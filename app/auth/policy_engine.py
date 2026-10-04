"""
Deterministic policy engine.

THIS IS THE SECURITY BOUNDARY. It is pure application code -- no LLM call
of any kind occurs in this module. The LLM (see app/llm and
app/agents/orchestrator.py) is only ever permitted to suggest which agent
*appears* relevant to a request ("intent"); this module is the sole
authority on whether the requesting user's role is actually *allowed* to
reach that agent.

Design rules enforced here:
  1. The permission matrix is a static, hard-coded Python data structure.
     It is not sourced from the LLM, from user input, or from any request
     payload.
  2. `authorize()` is a pure function: given a role and a set of requested
     agents, it deterministically returns which are allowed and which are
     denied. Same inputs -> same outputs, every time.
  3. Callers (the orchestrator graph) MUST check authorization for every
     requested agent BEFORE invoking that agent or its retriever. This
     module has no side effects and does not know about retrievers,
     vector stores, or the LLM -- it cannot leak data, by construction.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from app.auth.models import AgentId, AuthDecision, Role

_PERMISSION_MATRIX: dict[Role, set[AgentId]] = {
    Role.CLINICIAN:        {AgentId.CLINICAL, AgentId.PHARMACY, AgentId.OPERATIONS},
    Role.PHARMACIST:       {AgentId.PHARMACY},
    Role.OPERATIONS_STAFF: {AgentId.OPERATIONS},
}

@dataclass(frozen=True)
class AuthorizationResult:
    role: Role
    requested_agents: tuple[AgentId, ...]
    authorized_agents: tuple[AgentId, ...] = field(default_factory=tuple)
    denied_agents: tuple[AgentId, ...]     = field(default_factory=tuple)

    @property
    def any_authorized(self) -> bool:
        return len(self.authorized_agents) > 0

    @property
    def overall_status(self) -> AuthDecision:
        return AuthDecision.ALLOWED if self.any_authorized else AuthDecision.DENIED

def is_role_allowed(role: Role, agent: AgentId) -> bool:
    return agent in _PERMISSION_MATRIX.get(role, set())

def authorize(role: Role, requested_agents: list[AgentId] | set[AgentId]) -> AuthorizationResult:
    requested = tuple(dict.fromkeys(requested_agents))
    allowed   = _PERMISSION_MATRIX.get(role, set())
    return AuthorizationResult(
        role=role,
        requested_agents=requested,
        authorized_agents=tuple(a for a in requested if a in allowed),
        denied_agents=tuple(a for a in requested if a not in allowed),
    )

def permission_matrix_snapshot() -> dict[str, list[str]]:
    return {r.value: sorted(a.value for a in agents)
            for r, agents in _PERMISSION_MATRIX.items()}