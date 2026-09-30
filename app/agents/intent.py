from __future__ import annotations
import json, re
from dataclasses import dataclass
from app.auth.models import AgentId
from app.llm.client import LLMUnavailableError, call_llm, llm_configured

_SYSTEM_PROMPT = """You are the intent classifier for MedOrch hospital AI.
Classify the user request into one or more domains.

Domains:
- "clinical"   : diagnoses, lab results, clinical assessment, treatment
- "pharmacy"   : medications, prescriptions, drug safety, reconciliation
- "operations" : appointments, admissions, scheduling, hospital workflows

Respond ONLY with JSON:
{"agents": ["clinical"], "reasoning": "brief reason"}
No prose outside the JSON."""

_KEYWORDS = {
    AgentId.CLINICAL:   ["diagnos", "lab", "test result", "clinical",
                         "disease", "condition", "treatment", "hypertension"],
    AgentId.PHARMACY:   ["medic", "prescription", "drug", "pharmacy",
                         "pharmacist", "reconciliation", "dose"],
    AgentId.OPERATIONS: ["appointment", "admission", "admit",
                         "schedule", "ward", "discharge"],
}

@dataclass(frozen=True)
class IntentResult:
    agents: tuple[AgentId, ...]
    reasoning: str
    source: str

def classify_intent_heuristic(message: str) -> IntentResult:
    text   = message.lower()
    agents = [a for a, kws in _KEYWORDS.items() if any(k in text for k in kws)]
    return IntentResult(
        agents=tuple(agents),
        reasoning="Keyword match: " + ", ".join(a.value for a in agents) if agents else "No domain matched.",
        source="heuristic",
    )

def classify_intent_llm(message: str) -> IntentResult:
    raw   = call_llm(_SYSTEM_PROMPT, f"User request: {message}", max_tokens=150)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON in response: {raw!r}")
    parsed = json.loads(match.group(0))
    valid  = {a.value for a in AgentId}
    agents = tuple(AgentId(a) for a in parsed.get("agents", []) if a in valid)
    return IntentResult(agents=agents, reasoning=parsed.get("reasoning", ""), source="llm")

def classify_intent(message: str) -> IntentResult:
    if llm_configured():
        try:
            return classify_intent_llm(message)
        except Exception:
            pass
    return classify_intent_heuristic(message)