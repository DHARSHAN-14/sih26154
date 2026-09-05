"""
retrieval/vectorstore.py — Qdrant client wrapper (stub).
Provides create collection, upsert chunks, payload-filtered search.
Stub stores in-memory dict so tests run without Qdrant running.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from app.retrieval.embedder import EmbeddingResult
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    score: float
    payload: dict = field(default_factory=dict)


class InMemoryVectorStore:
    """Stub vector store — replace with Qdrant client in Phase 2."""
    def __init__(self) -> None:
        self._store: dict[str, tuple[EmbeddingResult, dict]] = {}

    def upsert(self, results: list[EmbeddingResult],
               payloads: list[dict] | None = None) -> None:
        payloads = payloads or [{} for _ in results]
        for emb, payload in zip(results, payloads):
            self._store[emb.chunk_id] = (emb, payload)

    def search(self, query_dense: list[float], top_k: int = 20,
               filters: dict | None = None) -> list[SearchResult]:
        """Cosine similarity stub (dot product on pseudo-vectors)."""
        scored = []
        for cid, (emb, payload) in self._store.items():
            score = sum(a*b for a,b in zip(query_dense[:len(emb.dense)], emb.dense))
            scored.append(SearchResult(chunk_id=cid, score=score, payload=payload))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]


# Module-level singleton (replaced by per-session Qdrant collection in Phase 2)
_stores: dict[str, InMemoryVectorStore] = {}

def get_store(collection: str) -> InMemoryVectorStore:
    if collection not in _stores:
        _stores[collection] = InMemoryVectorStore()
    return _stores[collection]

def drop_store(collection: str) -> None:
    _stores.pop(collection, None)
