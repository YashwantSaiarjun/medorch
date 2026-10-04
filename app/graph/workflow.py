from __future__ import annotations
import logging, uuid
from dataclasses import asdict
from langgraph.graph import END, StateGraph
from app.agents.clinical_agent import ClinicalAgent
from app.agents.pharmacy_agent import PharmacyAgent
from app.agents.operations_agent import OperationsAgent
from app.agents.intent import classify_intent
from app.audit.logger import get_audit_service
from app.audit.models import AuditRecord
from app.auth.models import AgentId, Role
from app.auth.policy_engine import authorize
from app.auth.patient_auth import is_patient_authorized, get_denial_message
from app.config import get_settings
from app.graph.state import MedOrchState

logger = logging.getLogger("medorch.graph")

VALID_ROLES = {r.value for r in Role}

_DISPLAY = {
    AgentId.CLINICAL.value:   "Clinical Agent",
    AgentId.PHARMACY.value:   "Pharmacy Agent",
    AgentId.OPERATIONS.value: "Operations Agent",
}

_AGENT_MAP = {
    AgentId.CLINICAL.value:   ClinicalAgent,
    AgentId.PHARMACY.value:   PharmacyAgent,
    AgentId.OPERATIONS.value: OperationsAgent,
}


# ── Nodes ──────────────────────────────────────────────────────────────────

def identify_role(state: MedOrchState) -> dict:
    role = state.get("role")
    if not role or role.upper() not in VALID_ROLES:
        msg = "Please specify your role: Clinician, Pharmacist, or Operations Staff."
        return {
            "status":            "NEEDS_ROLE",
            "final_answer":      msg,
            "detected_agents":   [],
            "authorized_agents": [],
            "denied_agents":     [],
            "executed_agents":   [],
            "citations":         [],
            "tools_called":      [],
        }
    return {"role": role.upper()}


def check_patient_auth(state: MedOrchState) -> dict:
    patient_id = state.get("patient_id")
    user_id    = state.get("user_id")
    role       = state.get("role")

    if not patient_id:
        return {}

    if not is_patient_authorized(user_id, patient_id, role=role):
        msg = get_denial_message(user_id, patient_id)
        return {
            "status":            "PATIENT_DENIED",
            "final_answer":      msg,
            "detected_agents":   [],
            "authorized_agents": [],
            "denied_agents":     [],
            "executed_agents":   [],
            "citations":         [],
            "tools_called":      [],
        }

    return {}


def analyze_intent(state: MedOrchState) -> dict:
    result = classify_intent(state["message"])
    return {
        "detected_agents":  [a.value for a in result.agents],
        "intent_reasoning": result.reasoning,
        "intent_source":    result.source,
    }


def authorize_node(state: MedOrchState) -> dict:
    role      = Role(state["role"])
    requested = [AgentId(a) for a in state.get("detected_agents", [])]

    if not requested:
        return {
            "authorized_agents": [],
            "denied_agents":     [],
            "status":            "DENIED",
            "denial_message":    "No relevant domain found for this request.",
        }

    result     = authorize(role, requested)
    authorized = [a.value for a in result.authorized_agents]
    denied     = [a.value for a in result.denied_agents]

    if not authorized:
        names = ", ".join(_DISPLAY.get(a, a) for a in denied)
        return {
            "authorized_agents": [],
            "denied_agents":     denied,
            "status":            "DENIED",
            "denial_message":    f"Access denied. Role {role.value} cannot access: {names}.",
        }

    return {
        "authorized_agents": authorized,
        "denied_agents":     denied,
        "status":            "ALLOWED" if not denied else "PARTIAL",
    }


def access_denied(state: MedOrchState) -> dict:
    return {
        "executed_agents": [],
        "agent_results":   {},
        "final_answer":    state.get("denial_message", "Access denied."),
        "citations":       [],
    }


def execute_agents(state: MedOrchState) -> dict:
    settings     = get_settings()
    executed     = []
    results      = {}
    patient_id   = state.get("patient_id")
    tools_called = []

    for agent_id in state.get("authorized_agents", []):
        cls = _AGENT_MAP.get(agent_id)
        if not cls:
            continue
        try:
            response = cls().handle(
                state["message"],
                top_k=settings.retrieval_top_k,
                patient_id=patient_id,
            )
            executed.append(agent_id)
            results[agent_id] = asdict(response)

            meta = response.retrieval_metadata or {}
            tools_called.extend(meta.get("tools_called", []))

        except Exception as exc:
            logger.exception("Agent %s failed", agent_id)
            results[agent_id] = {
                "agent_id": agent_id,
                "answer":   "",
                "sources":  [],
                "error":    str(exc),
            }

    return {
        "executed_agents": executed,
        "agent_results":   results,
        "tools_called":    tools_called,
    }


def aggregate_results(state: MedOrchState) -> dict:
    sections, citations = [], []

    for agent_id, res in state.get("agent_results", {}).items():
        label = _DISPLAY.get(agent_id, agent_id)
        if res.get("error"):
            sections.append(f"{label}:\n[Error: {res['error']}]")
        else:
            sections.append(f"{label}:\n{res.get('answer', '')}")
            for src in res.get("sources", []):
                citations.append({"agent": agent_id, **src})

    # Only show denial message if user explicitly asked for that domain
    # not just because generic keywords like "name" matched everything
    denied = state.get("denied_agents", [])
    authorized = state.get("authorized_agents", [])
    if denied and len(authorized) == 0:
        names = ", ".join(_DISPLAY.get(a, a) for a in denied)
        sections.append(f"(Access denied for: {names})")

    return {
        "final_answer": "\n\n".join(sections) or "No information returned.",
        "citations":    citations,
    }


def audit_log(state: MedOrchState) -> dict:
    get_audit_service().record(AuditRecord(
        request_id=state["request_id"],
        user_id=state["user_id"],
        role=state.get("role") or "UNKNOWN",
        timestamp=AuditRecord.now_iso(),
        request_text=state["message"],
        patient_id=state.get("patient_id"),
        detected_intent=state.get("detected_agents", []),
        requested_agents=state.get("detected_agents", []),
        authorized_agents=state.get("authorized_agents", []),
        denied_agents=state.get("denied_agents", []),
        executed_agents=state.get("executed_agents", []),
        tools_called=state.get("tools_called", []),
        status=state.get("status", "ERROR"),
    ))
    return {}


# ── Routing ────────────────────────────────────────────────────────────────

def _route_role(state: MedOrchState) -> str:
    return "audit_log" if state.get("status") == "NEEDS_ROLE" \
           else "check_patient_auth"


def _route_patient_auth(state: MedOrchState) -> str:
    return "audit_log" if state.get("status") == "PATIENT_DENIED" \
           else "analyze_intent"


def _route_auth(state: MedOrchState) -> str:
    return "access_denied" if state.get("status") == "DENIED" \
           else "execute_agents"


# ── Graph ──────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(MedOrchState)

    for name, fn in [
        ("identify_role",      identify_role),
        ("check_patient_auth", check_patient_auth),
        ("analyze_intent",     analyze_intent),
        ("authorize",          authorize_node),
        ("access_denied",      access_denied),
        ("execute_agents",     execute_agents),
        ("aggregate_results",  aggregate_results),
        ("audit_log",          audit_log),
    ]:
        g.add_node(name, fn)

    g.set_entry_point("identify_role")

    g.add_conditional_edges("identify_role", _route_role,
        {"audit_log": "audit_log", "check_patient_auth": "check_patient_auth"})

    g.add_conditional_edges("check_patient_auth", _route_patient_auth,
        {"audit_log": "audit_log", "analyze_intent": "analyze_intent"})

    g.add_edge("analyze_intent", "authorize")

    g.add_conditional_edges("authorize", _route_auth,
        {"access_denied": "access_denied", "execute_agents": "execute_agents"})

    g.add_edge("access_denied",      "audit_log")
    g.add_edge("execute_agents",     "aggregate_results")
    g.add_edge("aggregate_results",  "audit_log")
    g.add_edge("audit_log",          END)

    return g.compile()


_graph = None


def get_compiled_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_request(user_id: str, role: str | None, message: str,
                request_id: str | None = None,
                patient_id: str | None = None) -> MedOrchState:
    return get_compiled_graph().invoke({
        "request_id": request_id or f"req-{uuid.uuid4().hex[:12]}",
        "user_id":    user_id,
        "role":       role,
        "message":    message,
        "patient_id": patient_id,
    })