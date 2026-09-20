"""
VectorStore abstraction.

Both implementations below expose the exact same narrow interface:
`upsert_documents` and `similarity_search`, scoped to a single
`namespace` (one per agent's knowledge base: "clinical_kb" or
"operations_kb"). A retriever is constructed against exactly one
namespace and never accepts a namespace parameter at query time --
this makes cross-namespace access a compile-time impossibility rather
than a runtime check (see clinical_retriever.py / operations_retriever.py).

- InMemoryVectorStore: numpy cosine-similarity store, zero external
  infra required. Used by default and by the test suite.
- PgVectorStore: PostgreSQL + pgvector backed store, used when
  DATABASE_URL is configured (docker-compose deployment). Each
  namespace maps to its own table (clinical_kb / operations_kb) as
  required by the spec's knowledge-isolation model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from app.rag.embeddings import embed_text


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    content: str
    metadata: dict


@dataclass(frozen=True)
class ScoredDocument:
    document: Document
    score: float


class VectorStore(Protocol):
    def upsert_documents(self, namespace: str, documents: list[Document]) -> None: ...

    def similarity_search(self, namespace: str, query: str, top_k: int = 3) -> list[ScoredDocument]: ...


class InMemoryVectorStore:
    """Simple, dependency-light cosine-similarity vector store."""

    def __init__(self) -> None:
        self._docs: dict[str, list[Document]] = {}
        self._vecs: dict[str, np.ndarray] = {}

    def upsert_documents(self, namespace: str, documents: list[Document]) -> None:
        self._docs.setdefault(namespace, [])
        self._vecs.setdefault(namespace, np.zeros((0, 1)))

        existing_ids = {d.doc_id for d in self._docs[namespace]}
        new_docs = [d for d in documents if d.doc_id not in existing_ids]
        if not new_docs:
            return

        new_vecs = np.array([embed_text(f"{d.title}\n{d.content}") for d in new_docs])
        self._docs[namespace].extend(new_docs)
        if self._vecs[namespace].shape[0] == 0:
            self._vecs[namespace] = new_vecs
        else:
            self._vecs[namespace] = np.vstack([self._vecs[namespace], new_vecs])

    def similarity_search(self, namespace: str, query: str, top_k: int = 3) -> list[ScoredDocument]:
        docs = self._docs.get(namespace, [])
        vecs = self._vecs.get(namespace)
        if not docs or vecs is None or vecs.shape[0] == 0:
            return []

        q = np.array(embed_text(query))
        # vectors are already unit-norm, so dot product == cosine similarity
        scores = vecs @ q
        top_idx = np.argsort(-scores)[:top_k]
        return [ScoredDocument(document=docs[i], score=float(scores[i])) for i in top_idx]


class PgVectorStore:
    """
    PostgreSQL + pgvector backed implementation.

    Each namespace is stored in its own physical table (created by
    scripts/init_db.sql: `clinical_kb`, `operations_kb`), giving a real
    (not merely logical) storage-level isolation boundary in addition to
    the application-level isolation enforced by the retrievers/agents.
    """

    _ALLOWED_NAMESPACES = {"clinical_kb", "operations_kb"}

    def __init__(self, database_url: str) -> None:
        import sqlalchemy as sa

        self._engine = sa.create_engine(database_url, future=True)

    def _validate_namespace(self, namespace: str) -> str:
        if namespace not in self._ALLOWED_NAMESPACES:
            raise ValueError(f"Unknown/disallowed namespace: {namespace}")
        return namespace

    def upsert_documents(self, namespace: str, documents: list[Document]) -> None:
        import json

        import sqlalchemy as sa

        table = self._validate_namespace(namespace)
        with self._engine.begin() as conn:
            for d in documents:
                vec = embed_text(f"{d.title}\n{d.content}")
                conn.execute(
                    sa.text(
                        f"""
                        INSERT INTO {table} (doc_id, title, content, metadata, embedding)
                        VALUES (:doc_id, :title, :content, CAST(:metadata AS JSONB), CAST(:embedding AS vector))
                        ON CONFLICT (doc_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                        """
                    ),
                    {
                        "doc_id": d.doc_id,
                        "title": d.title,
                        "content": d.content,
                        "metadata": json.dumps(d.metadata),
                        "embedding": str(vec),
                    },
                )

    def similarity_search(self, namespace: str, query: str, top_k: int = 3) -> list[ScoredDocument]:
        import sqlalchemy as sa

        table = self._validate_namespace(namespace)
        q_vec = embed_text(query)
        with self._engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    f"""
                    SELECT doc_id, title, content, metadata,
                           1 - (embedding <=> CAST(:qvec AS vector)) AS score
                    FROM {table}
                    ORDER BY embedding <=> CAST(:qvec AS vector)
                    LIMIT :top_k
                    """
                ),
                {"qvec": str(q_vec), "top_k": top_k},
            ).fetchall()

        results = []
        for r in rows:
            doc = Document(doc_id=r.doc_id, title=r.title, content=r.content, metadata=r.metadata or {})
            results.append(ScoredDocument(document=doc, score=float(r.score)))
        return results


_singleton_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """
    Factory returning the process-wide vector store instance. Uses Postgres
    + pgvector when DATABASE_URL is configured, otherwise an in-memory
    store. This is the ONLY place storage-backend selection happens.
    """
    global _singleton_store
    if _singleton_store is not None:
        return _singleton_store

    from app.config import get_settings

    settings = get_settings()
    if settings.database_url:
        _singleton_store = PgVectorStore(settings.database_url)
    else:
        _singleton_store = InMemoryVectorStore()
    return _singleton_store


def reset_vector_store_for_tests(store: VectorStore | None = None) -> None:
    """Test-only helper to reset/replace the singleton store."""
    global _singleton_store
    _singleton_store = store if store is not None else InMemoryVectorStore()
