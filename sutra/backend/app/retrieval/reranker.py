"""
retrieval/reranker.py — bge-reranker-v2-m3 cross-encoder (stub).
Takes top-50 fused candidates, returns top-8 by rerank score.
Stub: identity pass-through. Replace with real cross-encoder in Phase 2.
"""
from __future__ import annotations
from app.retrieval.hybrid import FusedResult


def rerank(
    query: str,
    candidates: list[FusedResult],
    chunk_texts: dict[str, str],
    top_k: int = 8,
) -> list[FusedResult]:
    """
    Rerank candidates by cross-encoder score.
    Stub: returns candidates in fusion order (no actual reranking).
    Replace with: scores = cross_encoder.predict([(query, chunk_texts[c.chunk_id]) for c in candidates])
    """
    return candidates[:top_k]
