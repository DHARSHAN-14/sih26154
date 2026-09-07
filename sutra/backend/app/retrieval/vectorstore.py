"""
retrieval/vectorstore.py — In-memory hybrid vector store & inverted index.
Provides:
- Dense vector index with cosine similarity.
- Sparse inverted index with BM25 / token-frequency scoring.
- Hybrid fusion search (Dense + Sparse + RRF) with cross-encoder reranking.
- Session-scoped collections with persistence across the workflow.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any

from app.retrieval.embedder import EmbeddingResult, embed_query
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0


class InMemoryVectorStore:
    """
    Production-grade in-memory hybrid store supporting dense semantic search,
    sparse BM25 scoring, reciprocal rank fusion, and cross-matching rerank.
    """
    def __init__(self) -> None:
        # chunk_id -> (EmbeddingResult, payload)
        self._store: dict[str, tuple[EmbeddingResult, dict[str, Any]]] = {}
        # token_hash -> dict[chunk_id, weight]
        self._inverted_index: dict[int, dict[str, float]] = {}
        self._doc_lengths: dict[str, int] = {}

    def upsert(
        self,
        results: list[EmbeddingResult],
        payloads: list[dict[str, Any]] | None = None,
    ) -> None:
        payloads = payloads or [{} for _ in results]
        for emb, payload in zip(results, payloads):
            self._store[emb.chunk_id] = (emb, payload)
            # Record doc length
            doc_len = len(emb.tokens) if emb.tokens else len(emb.sparse)
            self._doc_lengths[emb.chunk_id] = max(doc_len, 1)

            # Update inverted index
            for thash, weight in emb.sparse.items():
                if thash not in self._inverted_index:
                    self._inverted_index[thash] = {}
                self._inverted_index[thash][emb.chunk_id] = weight

    def size(self) -> int:
        return len(self._store)

    def all_chunk_texts(self) -> dict[str, str]:
        return {
            cid: payload.get("text", "")
            for cid, (_, payload) in self._store.items()
        }

    def search_dense(
        self,
        query_dense: list[float],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Cosine similarity over dense vectors."""
        scored: list[SearchResult] = []
        q_norm = math.sqrt(sum(x * x for x in query_dense))
        if q_norm == 0:
            return scored

        for cid, (emb, payload) in self._store.items():
            if filters and not self._matches_filter(payload, filters):
                continue
            dot = sum(a * b for a, b in zip(query_dense, emb.dense))
            # emb.dense is already normalized, but guard against div0
            sim = max(0.0, dot / q_norm)
            scored.append(SearchResult(
                chunk_id=cid,
                score=round(sim, 4),
                dense_score=round(sim, 4),
                payload=payload,
            ))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def search_sparse(
        self,
        query_sparse: dict[int, float],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """BM25-style inverted index search."""
        if not self._store or not query_sparse:
            return []

        N = len(self._store)
        avgdl = sum(self._doc_lengths.values()) / max(N, 1)
        k1 = 1.2
        b = 0.75

        scores: dict[str, float] = {}

        for thash, q_weight in query_sparse.items():
            postings = self._inverted_index.get(thash, {})
            df = len(postings)
            if df == 0:
                continue
            # Standard Lucene/BM25 IDF
            idf = math.log(1.0 + (N - df + 0.5) / (df + 0.5))
            for cid, tf in postings.items():
                payload = self._store[cid][1]
                if filters and not self._matches_filter(payload, filters):
                    continue
                doc_len = self._doc_lengths.get(cid, avgdl)
                tf_norm = (tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (doc_len / avgdl)))
                score = idf * tf_norm * q_weight
                scores[cid] = scores.get(cid, 0.0) + score

        scored = [
            SearchResult(
                chunk_id=cid,
                score=round(score, 4),
                sparse_score=round(score, 4),
                payload=self._store[cid][1],
            )
            for cid, score in scores.items()
        ]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def search(
        self,
        query_dense: list[float],
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Backward-compatible search calling search_dense."""
        return self.search_dense(query_dense, top_k=top_k, filters=filters)

    def search_hybrid(
        self,
        query_text: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        k_rrf: int = 60,
    ) -> list[SearchResult]:
        """
        Execute full hybrid retrieval:
        1. Embed query into dense and sparse representations.
        2. Retrieve dense candidates via cosine similarity.
        3. Retrieve sparse candidates via BM25 inverted index.
        4. Fuse candidates via Reciprocal Rank Fusion (RRF).
        5. Rerank via cross-encoder token matching.
        """
        from app.retrieval.hybrid import reciprocal_rank_fusion
        from app.retrieval.reranker import rerank

        q_emb = embed_query(query_text)
        dense_results = self.search_dense(q_emb.dense, top_k=max(top_k * 3, 20), filters=filters)
        sparse_results = self.search_sparse(q_emb.sparse, top_k=max(top_k * 3, 20), filters=filters)

        # Fallback if both empty
        if not dense_results and not sparse_results:
            return []

        # Reciprocal Rank Fusion
        fused = reciprocal_rank_fusion(dense_results, sparse_results, k=k_rrf)

        # Build chunk texts for reranking
        chunk_texts = self.all_chunk_texts()
        reranked_fused = rerank(query_text, fused, chunk_texts, top_k=top_k)

        # Map to SearchResult with complete metadata
        results: list[SearchResult] = []
        dense_map = {r.chunk_id: r.dense_score for r in dense_results}
        sparse_map = {r.chunk_id: r.sparse_score for r in sparse_results}

        for f in reranked_fused:
            cid = f.chunk_id
            payload = self._store[cid][1] if cid in self._store else {}
            results.append(SearchResult(
                chunk_id=cid,
                score=round(f.rrf_score, 4),
                payload=payload,
                dense_score=dense_map.get(cid, 0.0),
                sparse_score=sparse_map.get(cid, 0.0),
                rrf_score=round(f.rrf_score, 4),
                rerank_score=round(getattr(f, "rerank_score", f.rrf_score), 4),
            ))

        return results

    @staticmethod
    def _matches_filter(payload: dict[str, Any], filters: dict[str, Any]) -> bool:
        for k, v in filters.items():
            if payload.get(k) != v:
                return False
        return True


# Session-scoped vector stores
_stores: dict[str, InMemoryVectorStore] = {}

def get_store(collection: str) -> InMemoryVectorStore:
    """Get or create session-specific hybrid vector store."""
    if collection not in _stores:
        _stores[collection] = InMemoryVectorStore()
    return _stores[collection]

def drop_store(collection: str) -> None:
    """Drop store for session."""
    _stores.pop(collection, None)
