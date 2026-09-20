"""
TEST 1-6: RBAC policy engine tests (deterministic, no LLM/network involved).
"""
from app.auth.models import AgentId, AuthDecision, Role
from app.auth.policy_engine import authorize, is_role_allowed


def test_clinician_agent_a_allowed():
    assert is_role_allowed(Role.CLINICIAN, AgentId.CLINICAL) is True
    result = authorize(Role.CLINICIAN, [AgentId.CLINICAL])
    assert result.overall_status == AuthDecision.ALLOWED
    assert AgentId.CLINICAL in result.authorized_agents
    assert result.denied_agents == ()


def test_clinician_agent_b_denied():
    assert is_role_allowed(Role.CLINICIAN, AgentId.OPERATIONS) is False
    result = authorize(Role.CLINICIAN, [AgentId.OPERATIONS])
    assert result.overall_status == AuthDecision.DENIED
    assert result.authorized_agents == ()
    assert AgentId.OPERATIONS in result.denied_agents


def test_operations_agent_a_denied():
    assert is_role_allowed(Role.OPERATIONS, AgentId.CLINICAL) is False
    result = authorize(Role.OPERATIONS, [AgentId.CLINICAL])
    assert result.overall_status == AuthDecision.DENIED
    assert result.authorized_agents == ()


def test_operations_agent_b_allowed():
    assert is_role_allowed(Role.OPERATIONS, AgentId.OPERATIONS) is True
    result = authorize(Role.OPERATIONS, [AgentId.OPERATIONS])
    assert result.overall_status == AuthDecision.ALLOWED
    assert AgentId.OPERATIONS in result.authorized_agents


def test_admin_both_agents_allowed():
    result = authorize(Role.ADMIN, [AgentId.CLINICAL, AgentId.OPERATIONS])
    assert result.overall_status == AuthDecision.ALLOWED
    assert set(result.authorized_agents) == {AgentId.CLINICAL, AgentId.OPERATIONS}
    assert result.denied_agents == ()


def test_restricted_both_agents_denied():
    result = authorize(Role.RESTRICTED, [AgentId.CLINICAL, AgentId.OPERATIONS])
    assert result.overall_status == AuthDecision.DENIED
    assert result.authorized_agents == ()
    assert set(result.denied_agents) == {AgentId.CLINICAL, AgentId.OPERATIONS}


def test_policy_engine_is_pure_and_deterministic():
    """Same inputs must always produce the same output -- no hidden state."""
    r1 = authorize(Role.CLINICIAN, [AgentId.CLINICAL, AgentId.OPERATIONS])
    r2 = authorize(Role.CLINICIAN, [AgentId.CLINICAL, AgentId.OPERATIONS])
    assert r1 == r2
