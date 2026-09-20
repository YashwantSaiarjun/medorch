"""
One-off script to load the synthetic knowledge base documents into the
configured vector store (Postgres+pgvector when DATABASE_URL is set).

Usage:
    DATABASE_URL=postgresql+psycopg2://medorch:medorch@localhost:5432/medorch \
        python scripts/load_kb.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.kb_loader import load_all_kbs  # noqa: E402


def main() -> None:
    load_clinical, load_ops = load_all_kbs()
    print("Loaded synthetic clinical_kb and operations_kb documents.")


if __name__ == "__main__":
    main()
