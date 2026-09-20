"""
TEST 7, 10, and end-to-end orchestration/demo-scenario tests via the
LangGraph workflow (app.graph.workflow.run_request).
"""
from app.graph.workflow import run_request


def test_unauthorized_agent_never_executes():
    """TEST 7: An unauthorized agent must not execute."""
    result = run_request("user-ops", "OPERATIONS", "What is the hypertension treatment protocol?")
    assert result["status"] == "DENIED"
    assert result["executed_agents"] == []
    assert "agent_results" not in result or result.get("agent_results", {}) == {}


def test_multiagent_request_correctly_decomposed_and_authorized():
    """TEST 10: multi-agent request is correctly decomposed and authorized."""
    result = run_request(
        "user-admin",
        "ADMIN",
        "Give me the synthetic clinical hypertension protocol and the corresponding hospital admission workflow.",
    )
    assert result["status"] == "ALLOWED"
    assert set(result["detected_agents"]) == {"clinical", "operations"}
    assert set(result["authorized_agents"]) == {"clinical", "operations"}
    assert set(result["executed_agents"]) == {"clinical", "operations"}
    agents_cited = {c["agent"] for c in result["citations"]}
    assert agents_cited == {"clinical", "operations"}


# --- README demo scenarios, exercised as automated regression tests --------

def test_scenario_1_clinician_clinical_question_allowed():
    result = run_request("user-001", "CLINICIAN", "What are the synthetic clinical guidelines for hypertension management?")
    assert result["status"] == "ALLOWED"
    assert result["executed_agents"] == ["clinical"]


def test_scenario_2_operations_question_allowed():
    result = run_request("user-002", "OPERATIONS", "What is the synthetic hospital admission workflow?")
    assert result["status"] == "ALLOWED"
    assert result["executed_agents"] == ["operations"]


def test_scenario_3_operations_role_clinical_question_denied():
    result = run_request("user-003", "OPERATIONS", "What is the synthetic clinical protocol for hypertension?")
    assert result["status"] == "DENIED"
    assert result["executed_agents"] == []
    assert "clinical" in result["denied_agents"]


def test_scenario_4_admin_multiagent_allowed():
    result = run_request(
        "user-004",
        "ADMIN",
        "Give me the synthetic clinical hypertension protocol and the corresponding hospital admission workflow.",
    )
    assert result["status"] == "ALLOWED"
    assert set(result["executed_agents"]) == {"clinical", "operations"}


def test_scenario_5_restricted_denied():
    result = run_request("user-005", "RESTRICTED", "Give me information about hypertension.")
    assert result["status"] == "DENIED"
    assert result["executed_agents"] == []


def test_missing_role_prompts_for_role():
    result = run_request("user-006", None, "What is the hypertension protocol?")
    assert result["status"] == "NEEDS_ROLE"
    assert "role" in result["final_answer"].lower()


def test_unknown_intent_handled_gracefully():
    result = run_request("user-007", "ADMIN", "What's the weather like today?")
    assert result["status"] == "DENIED"
    assert result["executed_agents"] == []


def test_audit_record_created_for_every_request():
    from app.audit.logger import get_audit_service

    result = run_request("user-008", "CLINICIAN", "What are the synthetic clinical guidelines for hypertension?")
    audit = get_audit_service().get(result["request_id"])
    assert audit is not None
    assert audit.role == "CLINICIAN"
    assert audit.status == "ALLOWED"
    assert audit.executed_agents == ["clinical"]


def test_audit_record_created_for_denied_request():
    from app.audit.logger import get_audit_service

    result = run_request("user-009", "OPERATIONS", "What is the hypertension treatment protocol?")
    audit = get_audit_service().get(result["request_id"])
    assert audit is not None
    assert audit.status == "DENIED"
    assert audit.executed_agents == []
    assert "clinical" in audit.denied_agents
