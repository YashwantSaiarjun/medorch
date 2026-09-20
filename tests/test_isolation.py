"""
TEST 8-9: knowledge-base isolation tests.

Prove that Agent A's retriever can never surface Agent B's documents and
vice versa, even when a query is deliberately cross-domain.
"""
from app.rag.clinical_retriever import ClinicalRetriever
from app.rag.operations_retriever import OperationsRetriever
from app.rag.vector_store import Document, InMemoryVectorStore


def test_agent_a_cannot_retrieve_agent_b_documents():
    clinical = ClinicalRetriever()
    # deliberately ask an operations-flavored query through the clinical retriever
    results = clinical.retrieve("hospital billing insurance appointment scheduling", top_k=10)
    ids = {r.document.doc_id for r in results}
    assert all(i.startswith("clin-") for i in ids)
    assert not any(i.startswith("ops-") for i in ids)


def test_agent_b_cannot_retrieve_agent_a_documents():
    operations = OperationsRetriever()
    results = operations.retrieve("hypertension medication dosage clinical protocol", top_k=10)
    ids = {r.document.doc_id for r in results}
    assert all(i.startswith("ops-") for i in ids)
    assert not any(i.startswith("clin-") for i in ids)


def test_namespaces_are_physically_separate_in_the_store():
    """
    Directly exercise the vector store: documents upserted into clinical_kb
    must never appear in a similarity_search against operations_kb.
    """
    store = InMemoryVectorStore()
    store.upsert_documents("clinical_kb", [Document("c1", "Clinical doc", "hypertension protocol content", {})])
    store.upsert_documents("operations_kb", [Document("o1", "Ops doc", "billing workflow content", {})])

    ops_results = store.similarity_search("operations_kb", "hypertension protocol", top_k=5)
    assert all(r.document.doc_id != "c1" for r in ops_results)

    clin_results = store.similarity_search("clinical_kb", "billing workflow", top_k=5)
    assert all(r.document.doc_id != "o1" for r in clin_results)


def test_retriever_classes_have_no_namespace_parameter():
    """
    Structural guarantee: retrieve() takes no namespace argument, so it is
    not possible at the call site to redirect a retriever at the other
    domain's knowledge base.
    """
    import inspect

    clinical_sig = inspect.signature(ClinicalRetriever.retrieve)
    operations_sig = inspect.signature(OperationsRetriever.retrieve)
    assert "namespace" not in clinical_sig.parameters
    assert "namespace" not in operations_sig.parameters
