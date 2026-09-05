"""
retrieval/hybrid.py — Reciprocal Rank Fusion over dense + sparse results.
RRF needs no per-corpus tuning, which matters when the corpus is whatever
the operator just uploaded.
"""
from __future__ import annotations
from dataclasses import dataclass
from app.retrieval.vectorstore import SearchResult


@dataclass
class FusedResult:
    chunk_id: str
    rrf_score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None


def reciprocal_rank_fusion(
    dense_results: list[SearchResult],
    sparse_results: list[SearchResult],
    k: int = 60,
) -> list[FusedResult]:
    """
    Fuse two ranked lists with RRF.
    RRF score = sum(1/(k + rank_i)) for each list where the item appears.
    """
    scores: dict[str, float] = {}
    dense_ranks: dict[str, int] = {}
    sparse_ranks: dict[str, int] = {}

    for rank, r in enumerate(dense_results, 1):
        scores[r.chunk_id] = scores.get(r.chunk_id, 0.0) + 1.0 / (k + rank)
        dense_ranks[r.chunk_id] = rank

    for rank, r in enumerate(sparse_results, 1):
        scores[r.chunk_id] = scores.get(r.chunk_id, 0.0) + 1.0 / (k + rank)
        sparse_ranks[r.chunk_id] = rank

    fused = [
        FusedResult(
            chunk_id=cid,
            rrf_score=score,
            dense_rank=dense_ranks.get(cid),
            sparse_rank=sparse_ranks.get(cid),
        )
        for cid, score in scores.items()
    ]
    fused.sort(key=lambda x: x.rrf_score, reverse=True)
    return fused
