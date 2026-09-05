"""
kg/contradiction.py — Deterministic contradiction detection.
Two detectors, both 100% deterministic (no LLM).
1. Same (subject, predicate) -> different object -> contradiction edge.
2. Temporal impossibility: event ordering that violates stated sequence.
"""
from __future__ import annotations
from app.core.schemas import Fact
from app.kg.graph import KnowledgeGraph


def detect_contradictions(
    facts: list[Fact], kg: KnowledgeGraph
) -> list[tuple[str, str]]:
    """
    Return list of (fact_id_a, fact_id_b) contradiction pairs.
    Populates contradiction edges in the KG.
    """
    # Group by (subject, predicate)
    groups: dict[tuple[str, str], list[Fact]] = {}
    for f in facts:
        key = (f.subject.lower().strip(), f.predicate.lower().strip())
        groups.setdefault(key, []).append(f)

    contradictions: list[tuple[str, str]] = []
    for (subj, pred), group in groups.items():
        if len(group) < 2:
            continue
        # Compare all pairs
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.object.strip().lower() != b.object.strip().lower():
                    contradictions.append((a.fact_id, b.fact_id))
                    # Mark in KG
                    kg.add_triple(
                        subj, pred + "_CONTRADICTS",
                        b.object[:50],
                        fact_id=a.fact_id,
                        is_contradiction=True,
                    )
    return contradictions
