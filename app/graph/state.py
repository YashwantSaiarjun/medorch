"""
Shared state object threaded through the LangGraph workflow.
"""
from __future__ import annotations

from typing import Any, TypedDict


class MedOrchState(TypedDict, total=False):
    request_id: str
    user_id: str
    role: str | None            # raw string from the request; may be missing
    message: str

    # Populated by Intent Analysis node (LLM suggestion, untrusted)
    detected_agents: list[str]
    intent_reasoning: str
    intent_source: str

    # Populated by Authorization node (deterministic policy engine, trusted)
    authorized_agents: list[str]
    denied_agents: list[str]

    # Populated by Agent Execution node
    executed_agents: list[str]
    agent_results: dict[str, Any]   # agent_id -> AgentResponse-like dict

    # Populated by Result Aggregation node
    final_answer: str
    citations: list[dict]

    # Control flow / terminal status
    status: str                     # NEEDS_ROLE | DENIED | ALLOWED | ERROR
    denial_message: str | None
