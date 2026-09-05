"""
retrieval/decompose.py — Query decomposition for multi-hop retrieval (Route B).
Splits a complex generation request into sub-queries, one per content section.
Each sub-query is independently embedded and retrieved.
This ensures the advisory "affected_systems" section retrieves different
chunks than the "recommended_actions" section.
"""
from __future__ import annotations
from dataclasses import dataclass
from app.core.schemas import SectionPlan


@dataclass
class SubQuery:
    section_key: str
    query_text: str
    preferred_fact_types: list[str]
    top_k: int = 20


def decompose(
    sections: list[SectionPlan],
    sot_context: str = "",
    target_format: str = "",
) -> list[SubQuery]:
    """
    Decompose a content plan into per-section retrieval queries.
    Stub: generates a trivial query per section.
    Replace with constrained LLM decomposition in Phase 2.
    """
    queries = []
    for section in sections:
        # Minimal query: use section_key as the query
        query_text = f"information about {section.section_key.replace('_', ' ')}"
        if target_format:
            query_text += f" for {target_format}"
        queries.append(SubQuery(
            section_key=section.section_key,
            query_text=query_text,
            preferred_fact_types=[],
            top_k=20,
        ))
    return queries
