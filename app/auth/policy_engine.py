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

# The central, centralized authorization matrix described in the spec.
# CLINICIAN   -> Agent A (clinical)   ALLOWED, Agent B (operations) DENIED
# OPERATIONS  -> Agent A (clinical)   DENIED,  Agent B (operations) ALLOWED
# ADMIN       -> both ALLOWED
# RESTRICTED  -> both DENIED
_PERMISSION_MATRIX: dict[Role, set[AgentId]] = {
    Role.CLINICIAN: {AgentId.CLINICAL},
    Role.OPERATIONS: {AgentId.OPERATIONS},
    Role.ADMIN: {AgentId.CLINICAL, AgentId.OPERATIONS},
    Role.RESTRICTED: set(),
}


@dataclass(frozen=True)
class AuthorizationResult:
    role: Role
    requested_agents: tuple[AgentId, ...]
    authorized_agents: tuple[AgentId, ...] = field(default_factory=tuple)
    denied_agents: tuple[AgentId, ...] = field(default_factory=tuple)

    @property
    def any_authorized(self) -> bool:
        return len(self.authorized_agents) > 0

    @property
    def overall_status(self) -> AuthDecision:
        return AuthDecision.ALLOWED if self.any_authorized else AuthDecision.DENIED


def is_role_allowed(role: Role, agent: AgentId) -> bool:
    """Pure, deterministic single-agent check."""
    return agent in _PERMISSION_MATRIX.get(role, set())


def authorize(role: Role, requested_agents: list[AgentId] | set[AgentId]) -> AuthorizationResult:
    """
    Deterministically split the requested agents into authorized / denied
    sets for the given role. This function must be called, and its result
    honored, BEFORE any agent is invoked or any knowledge base is queried.
    """
    requested = tuple(dict.fromkeys(requested_agents))  # de-dupe, preserve order
    allowed_set = _PERMISSION_MATRIX.get(role, set())

    authorized = tuple(a for a in requested if a in allowed_set)
    denied = tuple(a for a in requested if a not in allowed_set)

    return AuthorizationResult(
        role=role,
        requested_agents=requested,
        authorized_agents=authorized,
        denied_agents=denied,
    )


def permission_matrix_snapshot() -> dict[str, list[str]]:
    """Read-only, human-readable view of the policy matrix (for docs/UI)."""
    return {role.value: sorted(a.value for a in agents) for role, agents in _PERMISSION_MATRIX.items()}
