"""
retrieval/embedder.py — bge-m3 dense+sparse embedding stub.
In production: BAAI/bge-m3 gives dense + sparse in one forward pass.
Stub returns random vectors so the rest of the pipeline can be tested.
"""
from __future__ import annotations
import hashlib
import struct
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    chunk_id: str
    dense: list[float]
    sparse: dict[int, float]   # token_id -> weight


def _pseudo_dense(text: str, dim: int = 128) -> list[float]:
    """Deterministic pseudo-random dense vector from text hash (stub)."""
    h = hashlib.sha256(text.encode()).digest()
    floats = [struct.unpack("f", h[i:i+4])[0] for i in range(0, min(dim*4, len(h)), 4)]
    while len(floats) < dim:
        floats.append(0.0)
    return floats[:dim]


def embed_chunks(chunks: list[tuple[str, str]]) -> list[EmbeddingResult]:
    """
    Embed a list of (chunk_id, text) pairs.
    Stub: replace with real bge-m3 inference in Phase 2.
    """
    results = []
    for cid, text in chunks:
        results.append(EmbeddingResult(
            chunk_id=cid,
            dense=_pseudo_dense(text),
            sparse={hash(w) % 30000: 1.0 for w in text.split()[:20]},
        ))
    return results
