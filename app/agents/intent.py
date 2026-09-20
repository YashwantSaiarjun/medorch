"""
Intent classification.

IMPORTANT: this module only ever produces a *suggestion* of which
agent(s) appear relevant to a request. Its output is treated as
untrusted input by the policy engine and has zero authority over
authorization. See app/auth/policy_engine.py for the actual security
boundary.

Two implementations are provided:
  - `classify_intent_llm`: asks the LLM to pick relevant domains.
  - `classify_intent_heuristic`: deterministic keyword-based fallback,
    used automatically when no LLM is configured, and available for
    fully offline/CI demos.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.auth.models import AgentId
from app.llm.client import LLMUnavailableError, call_llm, llm_configured

_SYSTEM_PROMPT = """You are the intent-classification component of MedOrch, a healthcare \
orchestration platform. Your ONLY job is to decide which knowledge domain(s) a user's \
request appears to relate to. You do NOT decide access permissions -- that is handled by \
a separate, deterministic policy engine outside your control. Never claim to grant or deny \
access.

Valid domains:
- "clinical": clinical guidelines, treatment protocols, medications, diseases, procedures
- "operations": hospital workflows, admissions, scheduling, insurance, billing, administration

Respond ONLY with compact JSON of the form:
{"agents": ["clinical"], "reasoning": "short reason"}
or
{"agents": ["clinical", "operations"], "reasoning": "short reason"}
or
{"agents": [], "reasoning": "short reason"}

No prose outside the JSON object."""

_CLINICAL_KEYWORDS = [
    "clinical", "treatment", "protocol", "guideline", "medication", "drug", "dose", "dosage",
    "diagnosis", "disease", "symptom", "hypertension", "diabetes", "pneumonia", "asthma",
    "surgery", "surgical", "wound", "therapy", "prescri", "patient care", "blood pressure",
    "cardio", "clinician",
]
_OPERATIONS_KEYWORDS = [
    "admission", "admit", "workflow", "appointment", "schedule", "scheduling", "insurance",
    "billing", "bill", "invoice", "credential", "discharge", "front desk", "registration",
    "operations", "administrative", "administration", "claims", "hospital process",
]


@dataclass(frozen=True)
class IntentResult:
    agents: tuple[AgentId, ...]
    reasoning: str
    source: str  # "llm" or "heuristic"


def classify_intent_heuristic(message: str) -> IntentResult:
    text = message.lower()
    agents: list[AgentId] = []
    if any(kw in text for kw in _CLINICAL_KEYWORDS):
        agents.append(AgentId.CLINICAL)
    if any(kw in text for kw in _OPERATIONS_KEYWORDS):
        agents.append(AgentId.OPERATIONS)

    reasoning = "Matched keyword heuristics: " + ", ".join(a.value for a in agents) if agents else \
        "No clinical or operations keywords matched."
    return IntentResult(agents=tuple(agents), reasoning=reasoning, source="heuristic")


def classify_intent_llm(message: str) -> IntentResult:
    raw = call_llm(_SYSTEM_PROMPT, f"User request: {message}", max_tokens=200)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"LLM did not return parseable JSON: {raw!r}")
    parsed = json.loads(match.group(0))

    valid_values = {a.value for a in AgentId}
    agents = tuple(AgentId(a) for a in parsed.get("agents", []) if a in valid_values)
    reasoning = str(parsed.get("reasoning", ""))
    return IntentResult(agents=agents, reasoning=reasoning, source="llm")


def classify_intent(message: str) -> IntentResult:
    """
    Preferred entry point: try the LLM if configured, else fall back to the
    deterministic heuristic classifier. Either way, the result is only a
    suggestion consumed by the policy engine downstream.
    """
    if llm_configured():
        try:
            return classify_intent_llm(message)
        except (LLMUnavailableError, ValueError, Exception):
            # Never let intent classification take down the request -- fall
            # back to the deterministic heuristic path.
            return classify_intent_heuristic(message)
    return classify_intent_heuristic(message)
