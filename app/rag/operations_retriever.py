"""
Operations retriever.

Hard-bound to the `operations_kb` namespace only, mirroring
clinical_retriever.py. Agent B (operations) can only ever reach this
retriever, and this retriever can only ever reach operations_kb.
"""
from __future__ import annotations

from app.rag.vector_store import Document, ScoredDocument, VectorStore, get_vector_store

NAMESPACE = "operations_kb"


class OperationsRetriever:
    def __init__(self, store: VectorStore | None = None) -> None:
        self._store = store or get_vector_store()

    def load_documents(self, documents: list[Document]) -> None:
        self._store.upsert_documents(NAMESPACE, documents)

    def retrieve(self, query: str, top_k: int = 3) -> list[ScoredDocument]:
        return self._store.similarity_search(NAMESPACE, query, top_k=top_k)
