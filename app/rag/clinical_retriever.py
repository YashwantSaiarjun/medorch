"""
Clinical retriever.

Hard-bound to the `clinical_kb` namespace only. There is no method on this
class that accepts a namespace parameter, and no other module constructs a
ClinicalRetriever pointed at any other namespace. This is the concrete
mechanism behind "Agent A must not have direct access to Agent B's
knowledge base" -- it is structurally impossible for this class to read
operations_kb.
"""
from __future__ import annotations

from app.rag.vector_store import Document, ScoredDocument, VectorStore, get_vector_store

NAMESPACE = "clinical_kb"


class ClinicalRetriever:
    def __init__(self, store: VectorStore | None = None) -> None:
        self._store = store or get_vector_store()

    def load_documents(self, documents: list[Document]) -> None:
        self._store.upsert_documents(NAMESPACE, documents)

    def retrieve(self, query: str, top_k: int = 3) -> list[ScoredDocument]:
        return self._store.similarity_search(NAMESPACE, query, top_k=top_k)
