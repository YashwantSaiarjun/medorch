"""
MedOrch orchestration workflow, implemented as a LangGraph state machine.

    START
      |
    identify_role -------------------> [NEEDS_ROLE] --> END
      |
    analyze_intent   (LLM suggestion only, untrusted)
      |
    authorize        (deterministic policy engine -- THE security boundary)
      |
      +-- no agents authorized --------> access_denied --> audit_log --> END
      |
    execute_agents    (only ever invokes AUTHORIZED agents)
      |
    aggregate_results
      |
    audit_log
      |
     END

This module contains no authorization logic of its own -- it only calls
app.auth.policy_engine.authorize() and strictly honors the result. Agents
(and therefore their retrievers/knowledge bases) are constructed and
invoked exclusively inside `execute_agents`, and only for agent ids that
appear in `authorized_agents`.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict

from langgraph.graph import END, StateGraph

from app.agents.clinical_agent import ClinicalAgent
from app.agents.intent import classify_intent
from app.agents.operations_agent import OperationsAgent
from app.audit.logger import get_audit_service
from app.audit.models import AuditRecord
from app.auth.models import AgentId, Role
from app.auth.policy_engine import authorize
from app.config import get_settings
from app.graph.state import MedOrchState

logger = logging.getLogger("medorch.graph")

_AGENT_DISPLAY_NAMES = {
    AgentId.CLINICAL.value: "Clinical Knowledge Agent (Agent A)",
    AgentId.OPERATIONS.value: "Healthcare Operations Agent (Agent B)",
}

VALID_ROLES = {r.value for r in Role}


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def identify_role(state: MedOrchState) -> dict:
    role = state.get("role")
    if not role or role.upper() not in VALID_ROLES:
        msg = (
            "Before I process your request, please specify your role: "
            "Clinician, Operations, Admin, or Restricted."
        )
        return {
            "status": "NEEDS_ROLE",
            "denial_message": msg,
            "final_answer": msg,
            "detected_agents": [],
            "authorized_agents": [],
            "denied_agents": [],
            "executed_agents": [],
            "citations": [],
        }
    return {"role": role.upper()}


def analyze_intent(state: MedOrchState) -> dict:
    result = classify_intent(state["message"])
    return {
        "detected_agents": [a.value for a in result.agents],
        "intent_reasoning": result.reasoning,
        "intent_source": result.source,
    }


def authorize_node(state: MedOrchState) -> dict:
    role = Role(state["role"])
    requested = [AgentId(a) for a in state.get("detected_agents", [])]

    if not requested:
        return {
            "authorized_agents": [],
            "denied_agents": [],
            "status": "DENIED",
            "denial_message": (
                "I couldn't determine a relevant clinical or operations knowledge domain "
                "for this request, so no specialized agent was invoked."
            ),
        }

    result = authorize(role, requested)
    authorized = [a.value for a in result.authorized_agents]
    denied = [a.value for a in result.denied_agents]

    if not authorized:
        denied_names = ", ".join(_AGENT_DISPLAY_NAMES.get(a, a) for a in denied)
        return {
            "authorized_agents": [],
            "denied_agents": denied,
            "status": "DENIED",
            "denial_message": (
                f"Access denied. Your current role ({role.value}) is not authorized to "
                f"access the requested knowledge domain ({denied_names})."
            ),
        }

    return {
        "authorized_agents": authorized,
        "denied_agents": denied,
        "status": "ALLOWED" if not denied else "PARTIAL",
    }


def access_denied(state: MedOrchState) -> dict:
    # Terminal node for fully-denied requests. No agent has been invoked and
    # no knowledge base has been queried at this point.
    return {
        "executed_agents": [],
        "agent_results": {},
        "final_answer": state.get("denial_message", "Access denied."),
        "citations": [],
    }


def execute_agents(state: MedOrchState) -> dict:
    settings = get_settings()
    executed: list[str] = []
    results: dict = {}

    for agent_id in state.get("authorized_agents", []):
        try:
            if agent_id == AgentId.CLINICAL.value:
                response = ClinicalAgent().handle(state["message"], top_k=settings.retrieval_top_k)
            elif agent_id == AgentId.OPERATIONS.value:
                response = OperationsAgent().handle(state["message"], top_k=settings.retrieval_top_k)
            else:
                continue  # unreachable: authorized_agents only ever contains known ids
        except Exception as exc:  # agent failure path
            logger.exception("Agent %s failed", agent_id)
            results[agent_id] = {"agent_id": agent_id, "answer": "", "sources": [], "error": str(exc)}
            continue

        executed.append(agent_id)
        results[agent_id] = asdict(response)

    return {"executed_agents": executed, "agent_results": results}


def aggregate_results(state: MedOrchState) -> dict:
    results = state.get("agent_results", {})
    sections: list[str] = []
    citations: list[dict] = []

    for agent_id, res in results.items():
        label = _AGENT_DISPLAY_NAMES.get(agent_id, agent_id)
        if res.get("error"):
            sections.append(f"{label}:\n[Agent failure -- {res['error']}]")
            continue

        sections.append(f"{label}:\n{res.get('answer', '')}")
        for src in res.get("sources", []):
            citations.append({"agent": agent_id, **src})

    denied = state.get("denied_agents", [])
    if denied:
        denied_names = ", ".join(_AGENT_DISPLAY_NAMES.get(a, a) for a in denied)
        sections.append(
            f"(Note: the following domain was not included because your role does not have "
            f"access: {denied_names}.)"
        )

    final_answer = "\n\n".join(sections) if sections else "No information was returned."
    return {"final_answer": final_answer, "citations": citations}


def audit_log(state: MedOrchState) -> dict:
    audit = AuditRecord(
        request_id=state["request_id"],
        user_id=state["user_id"],
        role=state.get("role") or "UNKNOWN",
        timestamp=AuditRecord.now_iso(),
        request_text=state["message"],
        detected_intent=state.get("detected_agents", []),
        requested_agents=state.get("detected_agents", []),
        authorized_agents=state.get("authorized_agents", []),
        denied_agents=state.get("denied_agents", []),
        executed_agents=state.get("executed_agents", []),
        status=state.get("status", "ERROR"),
    )
    get_audit_service().record(audit)
    return {}


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

def _route_after_role(state: MedOrchState) -> str:
    return "end_needs_role" if state.get("status") == "NEEDS_ROLE" else "analyze_intent"


def _route_after_authorize(state: MedOrchState) -> str:
    return "access_denied" if state.get("status") == "DENIED" else "execute_agents"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(MedOrchState)

    graph.add_node("identify_role", identify_role)
    graph.add_node("analyze_intent", analyze_intent)
    graph.add_node("authorize", authorize_node)
    graph.add_node("access_denied", access_denied)
    graph.add_node("execute_agents", execute_agents)
    graph.add_node("aggregate_results", aggregate_results)
    graph.add_node("audit_log", audit_log)

    graph.set_entry_point("identify_role")

    graph.add_conditional_edges(
        "identify_role",
        _route_after_role,
        {"end_needs_role": "audit_log", "analyze_intent": "analyze_intent"},
    )
    graph.add_edge("analyze_intent", "authorize")
    graph.add_conditional_edges(
        "authorize",
        _route_after_authorize,
        {"access_denied": "access_denied", "execute_agents": "execute_agents"},
    )
    graph.add_edge("access_denied", "audit_log")
    graph.add_edge("execute_agents", "aggregate_results")
    graph.add_edge("aggregate_results", "audit_log")
    graph.add_edge("audit_log", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_request(user_id: str, role: str | None, message: str, request_id: str | None = None) -> MedOrchState:
    """Single public entry point used by both the FastAPI layer and tests."""
    graph = get_compiled_graph()
    initial_state: MedOrchState = {
        "request_id": request_id or f"req-{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "role": role,
        "message": message,
    }
    result: MedOrchState = graph.invoke(initial_state)
    return result
