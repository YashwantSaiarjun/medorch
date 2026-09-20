"""
RAG-layer unit tests: agents return proper citations/metadata, and
retrieval-failure handling degrades gracefully rather than crashing the
request.
"""
from app.agents.clinical_agent import ClinicalAgent
from app.agents.operations_agent import OperationsAgent


def test_clinical_agent_returns_sources_and_agent_id():
    response = ClinicalAgent().handle("What is the synthetic hypertension protocol?", top_k=2)
    assert response.ok
    assert response.agent_id == "clinical"
    assert len(response.sources) > 0
    assert all(s.doc_id.startswith("clin-") for s in response.sources)
    assert "latency_ms" in response.retrieval_metadata


def test_operations_agent_returns_sources_and_agent_id():
    response = OperationsAgent().handle("What is the synthetic hospital admission workflow?", top_k=2)
    assert response.ok
    assert response.agent_id == "operations"
    assert len(response.sources) > 0
    assert all(s.doc_id.startswith("ops-") for s in response.sources)


def test_agent_handles_retrieval_failure_gracefully():
    class BrokenRetriever:
        def retrieve(self, query, top_k=3):
            raise RuntimeError("simulated retrieval outage")

    agent = ClinicalAgent(retriever=BrokenRetriever())
    response = agent.handle("anything")
    assert not response.ok
    assert "Retrieval failure" in response.error


def test_no_results_returns_graceful_empty_answer():
    from app.rag.clinical_retriever import ClinicalRetriever
    from app.rag.vector_store import InMemoryVectorStore

    empty_store = InMemoryVectorStore()  # nothing loaded
    agent = ClinicalAgent(retriever=ClinicalRetriever(empty_store))
    response = agent.handle("anything at all")
    assert response.ok
    assert response.sources == []
