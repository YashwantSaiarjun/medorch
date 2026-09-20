import os
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_LLM", "true")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.audit.logger import reset_audit_service_for_tests
from app.rag.clinical_retriever import ClinicalRetriever
from app.rag.kb_loader import load_clinical_kb, load_operations_kb
from app.rag.operations_retriever import OperationsRetriever
from app.rag.vector_store import InMemoryVectorStore, reset_vector_store_for_tests


@pytest.fixture(autouse=True)
def _isolated_environment():
    """
    Give every test a fresh in-memory vector store (pre-loaded with the
    synthetic KBs) and a fresh audit service, so tests never leak state
    into one another.
    """
    store = InMemoryVectorStore()
    reset_vector_store_for_tests(store)
    load_clinical_kb(ClinicalRetriever(store))
    load_operations_kb(OperationsRetriever(store))
    reset_audit_service_for_tests()
    yield
