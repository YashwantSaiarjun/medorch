"""
Lightweight, dependency-free embedding function.

For a two-day POC we avoid requiring a network call (or a large downloaded
model) just to embed synthetic demo documents. We use scikit-learn's
HashingVectorizer, which:
  - needs no training/fit step (stateless, deterministic),
  - produces a fixed-dimensionality dense vector,
  - is good enough to give meaningfully different vectors for the two
    distinct synthetic corpora (clinical vs operations) used in this demo.

In a production system this would be swapped for a real embedding model
(e.g. an API-based embedding endpoint or a local sentence-transformer);
because retrieval is hidden entirely behind the VectorStore interface
(see vector_store.py), that swap would not require any change to the
agents, the orchestrator, or the security boundary.
"""
from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

EMBEDDING_DIM = 256

_vectorizer = HashingVectorizer(
    n_features=EMBEDDING_DIM,
    alternate_sign=False,
    norm="l2",
)


def embed_text(text: str) -> list[float]:
    """Deterministically embed a single string into a unit-norm vector."""
    vec = _vectorizer.transform([text]).toarray()[0]
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.astype(float).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    return [embed_text(t) for t in texts]
