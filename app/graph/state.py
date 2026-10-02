from __future__ import annotations
from typing import Any, TypedDict


class MedOrchState(TypedDict, total=False):
    request_id: str
    user_id: str
    role: str | None
    patient_id: str | None        # ← NEW
    message: str

    detected_agents: list[str]
    intent_reasoning: str
    intent_source: str

    authorized_agents: list[str]
    denied_agents: list[str]

    executed_agents: list[str]
    tools_called: list[str]       # ← NEW
    agent_results: dict[str, Any]

    final_answer: str
    citations: list[dict]

    status: str
    denial_message: str | None