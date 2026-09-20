"""
Loads the synthetic JSON documents in data/clinical and data/operations
into the appropriate retriever/namespace. Used at app startup and by
scripts/load_kb.py for the Postgres/docker-compose deployment.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.rag.clinical_retriever import ClinicalRetriever
from app.rag.operations_retriever import OperationsRetriever
from app.rag.vector_store import Document

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _load_json_documents(path: Path) -> list[Document]:
    raw = json.loads(path.read_text())
    return [
        Document(doc_id=d["doc_id"], title=d["title"], content=d["content"], metadata=d.get("metadata", {}))
        for d in raw
    ]


def load_clinical_kb(retriever: ClinicalRetriever | None = None) -> ClinicalRetriever:
    retriever = retriever or ClinicalRetriever()
    docs = _load_json_documents(_DATA_DIR / "clinical" / "documents.json")
    retriever.load_documents(docs)
    return retriever


def load_operations_kb(retriever: OperationsRetriever | None = None) -> OperationsRetriever:
    retriever = retriever or OperationsRetriever()
    docs = _load_json_documents(_DATA_DIR / "operations" / "documents.json")
    retriever.load_documents(docs)
    return retriever


def load_all_kbs() -> tuple[ClinicalRetriever, OperationsRetriever]:
    return load_clinical_kb(), load_operations_kb()
