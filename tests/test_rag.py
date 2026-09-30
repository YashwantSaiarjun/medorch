from app.agents.clinical_agent import ClinicalAgent
from app.agents.pharmacy_agent import PharmacyAgent
from app.agents.operations_agent import OperationsAgent

def test_clinical_agent_sources():
    r = ClinicalAgent().handle("clinical assessment hypertension", top_k=2)
    assert r.ok and r.agent_id == "clinical"
    assert all(s.doc_id.startswith("clin-") for s in r.sources)

def test_pharmacy_agent_sources():
    r = PharmacyAgent().handle("medication reconciliation safety", top_k=2)
    assert r.ok and r.agent_id == "pharmacy"
    assert all(s.doc_id.startswith("pharm-") for s in r.sources)

def test_operations_agent_sources():
    r = OperationsAgent().handle("hospital admission discharge", top_k=2)
    assert r.ok and r.agent_id == "operations"
    assert all(s.doc_id.startswith("ops-") for s in r.sources)

def test_all_agents_handle_failure():
    class Broken:
        def retrieve(self, q, top_k=3): raise RuntimeError("outage")
    for Cls in [ClinicalAgent, PharmacyAgent, OperationsAgent]:
        r = Cls(retriever=Broken()).handle("test")
        assert not r.ok
        assert "Retrieval failure" in r.error