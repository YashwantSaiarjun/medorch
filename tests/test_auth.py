from app.auth.models import AgentId, AuthDecision, Role
from app.auth.policy_engine import authorize, is_role_allowed

def test_clinician_clinical_allowed():
    assert is_role_allowed(Role.CLINICIAN, AgentId.CLINICAL) is True

def test_clinician_pharmacy_denied():
    assert is_role_allowed(Role.CLINICIAN, AgentId.PHARMACY) is False

def test_clinician_operations_denied():
    assert is_role_allowed(Role.CLINICIAN, AgentId.OPERATIONS) is False

def test_pharmacist_pharmacy_allowed():
    assert is_role_allowed(Role.PHARMACIST, AgentId.PHARMACY) is True

def test_pharmacist_clinical_denied():
    assert is_role_allowed(Role.PHARMACIST, AgentId.CLINICAL) is False

def test_pharmacist_operations_denied():
    assert is_role_allowed(Role.PHARMACIST, AgentId.OPERATIONS) is False

def test_operations_staff_operations_allowed():
    assert is_role_allowed(Role.OPERATIONS_STAFF, AgentId.OPERATIONS) is True

def test_operations_staff_clinical_denied():
    assert is_role_allowed(Role.OPERATIONS_STAFF, AgentId.CLINICAL) is False

def test_operations_staff_pharmacy_denied():
    assert is_role_allowed(Role.OPERATIONS_STAFF, AgentId.PHARMACY) is False

def test_partial_authorization_split():
    result = authorize(Role.CLINICIAN, [AgentId.CLINICAL, AgentId.PHARMACY])
    assert set(result.authorized_agents) == {AgentId.CLINICAL}
    assert set(result.denied_agents)     == {AgentId.PHARMACY}

def test_policy_is_deterministic():
    r1 = authorize(Role.CLINICIAN, [AgentId.CLINICAL, AgentId.PHARMACY])
    r2 = authorize(Role.CLINICIAN, [AgentId.CLINICAL, AgentId.PHARMACY])
    assert r1 == r2