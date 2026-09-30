from app.graph.workflow import run_request

def test_missing_role_prompts():
    r = run_request("u1", None, "Show P1001 diagnoses")
    assert r["status"] == "NEEDS_ROLE"

def test_invalid_role_prompts():
    r = run_request("u1", "ADMIN", "Show P1001 diagnoses")
    assert r["status"] == "NEEDS_ROLE"

def test_clinician_clinical_allowed():
    r = run_request("u1", "CLINICIAN", "Show P1001 diagnoses and lab results")
    assert r["status"] == "ALLOWED"
    assert "clinical" in r["executed_agents"]

def test_clinician_pharmacy_denied():
    r = run_request("u1", "CLINICIAN", "Show P1001 medications and prescriptions")
    assert "pharmacy" not in r["executed_agents"]
    assert "pharmacy" in r.get("denied_agents", [])

def test_pharmacist_pharmacy_allowed():
    r = run_request("u2", "PHARMACIST", "Show P1001 medications and prescriptions")
    assert r["status"] == "ALLOWED"
    assert "pharmacy" in r["executed_agents"]

def test_pharmacist_clinical_denied():
    r = run_request("u2", "PHARMACIST", "Show P1001 diagnoses")
    assert "clinical" not in r["executed_agents"]

def test_operations_staff_allowed():
    r = run_request("u3", "OPERATIONS_STAFF", "Show P1001 appointments and admission")
    assert r["status"] == "ALLOWED"
    assert "operations" in r["executed_agents"]

def test_operations_staff_clinical_denied():
    r = run_request("u3", "OPERATIONS_STAFF", "Show P1001 diagnoses")
    assert "clinical" not in r["executed_agents"]

def test_partial_authorization():
    r = run_request("u1", "CLINICIAN", "Show P1001 diagnoses and medications")
    assert "clinical" in r["executed_agents"]
    assert "pharmacy" not in r["executed_agents"]
    assert r["status"] == "PARTIAL"

def test_unknown_intent_denied():
    r = run_request("u1", "CLINICIAN", "What is the weather today?")
    assert r["executed_agents"] == []

def test_audit_record_created():
    from app.audit.logger import get_audit_service
    r = run_request("u1", "CLINICIAN", "Show P1001 diagnoses")
    audit = get_audit_service().get(r["request_id"])
    assert audit is not None
    assert audit.role == "CLINICIAN"