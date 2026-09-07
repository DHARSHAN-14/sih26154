"""
retrieval/reranker.py — Cross-matching reranker.
Takes top fused candidates from RRF and rescores them using:
1. Exact identifier and entity matching (CVEs, IPs, port numbers, threat actors).
2. Lexical term coverage (recall of query terms in the candidate passage).
3. Consecutive n-gram phrase alignment.
4. Calibrated combination with Reciprocal Rank Fusion (RRF) score.
"""
from __future__ import annotations
import re
from app.retrieval.hybrid import FusedResult
from app.retrieval.embedder import tokenize, _STOP_WORDS


def _extract_identifiers(text: str) -> set[str]:
    """Extract critical technical identifiers like CVEs, IPs, ports, and threat actor tokens."""
    tokens = set()
    # CVE patterns
    for m in re.finditer(r"cve-\d{4}-\d+", text.lower()):
        tokens.add(m.group(0))
    # IP patterns
    for m in re.finditer(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text):
        tokens.add(m.group(0))
    # Standalone numbers (ports, counts, CVSS)
    for m in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
        tokens.add(m.group(0))
    return tokens


def rerank(
    query: str,
    candidates: list[FusedResult],
    chunk_texts: dict[str, str],
    top_k: int = 8,
) -> list[FusedResult]:
    """
    Rerank candidate passages against the query using cross-matching scoring.
    """
    if not candidates:
        return []

    q_tokens = [t for t in tokenize(query) if t not in _STOP_WORDS]
    q_identifiers = _extract_identifiers(query)
    q_bigrams = [
        f"{q_tokens[i]} {q_tokens[i+1]}"
        for i in range(len(q_tokens) - 1)
    ]

    # Find max RRF score for normalization
    max_rrf = max((c.rrf_score for c in candidates), default=1.0) or 1.0

    rescored: list[tuple[float, FusedResult]] = []

    for c in candidates:
        text = chunk_texts.get(c.chunk_id, "").lower()
        if not text:
            c.rerank_score = c.rrf_score
            rescored.append((c.rerank_score, c))
            continue

        p_tokens = set(tokenize(text))
        p_identifiers = _extract_identifiers(text)

        # 1. Term coverage (fraction of query tokens present in passage)
        coverage = sum(1.0 for t in q_tokens if t in p_tokens) / max(len(q_tokens), 1)

        # 2. Technical identifier exact match bonus
        id_matches = sum(1.0 for ident in q_identifiers if ident in p_identifiers or ident in text)
        id_bonus = min(1.0, (id_matches / max(len(q_identifiers), 1)) * 1.5) if q_identifiers else 0.5

        # 3. Bigram phrase alignment bonus
        bigram_matches = sum(1.0 for bg in q_bigrams if bg in text)
        bigram_bonus = min(1.0, bigram_matches / max(len(q_bigrams), 1)) if q_bigrams else 0.0

        # 4. RRF normalized contribution
        rrf_norm = c.rrf_score / max_rrf

        # Combined cross-score (0.0 to 1.0)
        final_score = (
            0.35 * rrf_norm +
            0.35 * coverage +
            0.20 * id_bonus +
            0.10 * bigram_bonus
        )
        c.rerank_score = round(min(1.0, max(0.0, final_score)), 4)
        rescored.append((c.rerank_score, c))

    # Sort descending by rerank_score
    rescored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in rescored[:top_k]]
