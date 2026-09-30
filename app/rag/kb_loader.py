from __future__ import annotations
import json
from pathlib import Path
from app.rag.clinical_retriever import ClinicalRetriever
from app.rag.operations_retriever import OperationsRetriever
from app.rag.pharmacy_retriever import PharmacyRetriever
from app.rag.vector_store import Document

_DATA = Path(__file__).resolve().parents[2] / "data"

def _load(path: Path) -> list[Document]:
    return [Document(doc_id=d["doc_id"], title=d["title"],
                     content=d["content"], metadata=d.get("metadata", {}))
            for d in json.loads(path.read_text())]

def load_clinical_kb(r=None):
    r = r or ClinicalRetriever()
    r.load_documents(_load(_DATA / "clinical" / "documents.json"))
    return r

def load_pharmacy_kb(r=None):
    r = r or PharmacyRetriever()
    r.load_documents(_load(_DATA / "pharmacy" / "documents.json"))
    return r

def load_operations_kb(r=None):
    r = r or OperationsRetriever()
    r.load_documents(_load(_DATA / "operations" / "documents.json"))
    return r

def load_all_kbs():
    return load_clinical_kb(), load_pharmacy_kb(), load_operations_kb()