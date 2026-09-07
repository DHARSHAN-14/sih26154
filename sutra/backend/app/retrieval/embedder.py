"""
retrieval/embedder.py — Hybrid dense + sparse embedding engine.
Generates:
1. Dense semantic feature vectors with subword/character n-gram hashing and L2 normalization
   providing accurate cosine similarity without heavy ML dependencies.
2. Sparse BM25-compatible token dictionaries with sublinear term-frequency weighting.
"""
from __future__ import annotations
import math
import re
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class EmbeddingResult:
    chunk_id: str
    dense: list[float]
    sparse: dict[int, float] = field(default_factory=dict)   # token_hash -> weight
    tokens: list[str] = field(default_factory=list)


_STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "but", "if", "then", "else", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "can", "will",
    "just", "should", "now", "this", "that", "these", "those"
}


def tokenize(text: str) -> list[str]:
    """Tokenize text preserving technical identifiers (CVEs, IPs, ports, versions)."""
    raw_tokens = re.findall(r"[a-zA-Z0-9_\-\.:]+", text.lower())
    # Strip boundary punctuation while preserving internal hyphens/dots
    cleaned = []
    for t in raw_tokens:
        t = t.strip(".:,;()[]{}'\"")
        if len(t) >= 2:
            cleaned.append(t)
    return cleaned


def compute_dense_vector(text: str, dim: int = 256) -> list[float]:
    """
    Compute a normalized dense semantic representation using unigrams, bigrams,
    and character 3-grams with sublinear TF weighting and L2 normalization.
    """
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * dim

    vec = [0.0] * dim

    # 1. Unigrams
    for t in tokens:
        weight = 0.5 if t in _STOP_WORDS else 1.5
        # Extra weight for technical identifiers (CVEs, IPs, numbers)
        if re.search(r"\d", t) or "-" in t:
            weight += 1.0
        h = abs(hash(t)) % dim
        vec[h] += weight

        # Character 3-grams for subword matching & spelling resilience
        if len(t) >= 3 and t not in _STOP_WORDS:
            for i in range(len(t) - 2):
                sub = t[i:i+3]
                h_sub = abs(hash(f"c3_{sub}")) % dim
                vec[h_sub] += 0.4

    # 2. Bigrams (word pairs for phrase matching)
    for i in range(len(tokens) - 1):
        t1, t2 = tokens[i], tokens[i+1]
        if t1 not in _STOP_WORDS or t2 not in _STOP_WORDS:
            h_bi = abs(hash(f"bi_{t1}_{t2}")) % dim
            vec[h_bi] += 1.2

    # Sublinear scaling: sign(x) * (1 + log(|x|))
    for i in range(dim):
        if vec[i] > 0:
            vec[i] = 1.0 + math.log(vec[i])

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [round(x / norm, 6) for x in vec]

    return vec


def compute_sparse_vector(text: str) -> dict[int, float]:
    """
    Compute sparse token frequency dictionary for BM25 / inverted index search.
    """
    tokens = tokenize(text)
    tf: dict[str, int] = {}
    for t in tokens:
        if t not in _STOP_WORDS:
            tf[t] = tf.get(t, 0) + 1

    sparse: dict[int, float] = {}
    for t, count in tf.items():
        # Sublinear term frequency
        weight = 1.0 + math.log(count)
        if re.search(r"\d", t) or "-" in t:
            weight *= 1.5
        token_hash = abs(hash(t)) % 1000003
        sparse[token_hash] = round(weight, 4)

    return sparse


def embed_chunks(chunks: list[tuple[str, str]]) -> list[EmbeddingResult]:
    """
    Embed a list of (chunk_id, text) pairs into dense + sparse representations.
    """
    results = []
    for cid, text in chunks:
        tokens = [t for t in tokenize(text) if t not in _STOP_WORDS]
        dense = compute_dense_vector(text)
        sparse = compute_sparse_vector(text)
        results.append(EmbeddingResult(
            chunk_id=cid,
            dense=dense,
            sparse=sparse,
            tokens=tokens,
        ))
    return results


def embed_query(query_text: str, query_id: str = "query") -> EmbeddingResult:
    """
    Embed a single search query into dense and sparse representations.
    """
    tokens = [t for t in tokenize(query_text) if t not in _STOP_WORDS]
    return EmbeddingResult(
        chunk_id=query_id,
        dense=compute_dense_vector(query_text),
        sparse=compute_sparse_vector(query_text),
        tokens=tokens,
    )
