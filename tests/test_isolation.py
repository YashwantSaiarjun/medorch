from app.rag.clinical_retriever import ClinicalRetriever
from app.rag.pharmacy_retriever import PharmacyRetriever
from app.rag.operations_retriever import OperationsRetriever

def test_clinical_only_returns_clinical_docs():
    results = ClinicalRetriever().retrieve("medication admission billing", top_k=10)
    assert all(r.document.doc_id.startswith("clin-") for r in results)

def test_pharmacy_only_returns_pharmacy_docs():
    results = PharmacyRetriever().retrieve("diagnosis lab result admission", top_k=10)
    assert all(r.document.doc_id.startswith("pharm-") for r in results)

def test_operations_only_returns_operations_docs():
    results = OperationsRetriever().retrieve("medication diagnosis clinical", top_k=10)
    assert all(r.document.doc_id.startswith("ops-") for r in results)

def test_retrievers_have_no_namespace_parameter():
    import inspect
    for cls in [ClinicalRetriever, PharmacyRetriever, OperationsRetriever]:
        sig = inspect.signature(cls.retrieve)
        assert "namespace" not in sig.parameters