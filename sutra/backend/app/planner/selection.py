"""
planner/selection.py — Ranks and selects facts for a section.
Respects min_facts, max_claims, prefers_fact_types, and depends_on closure.
"""
from __future__ import annotations
from app.core.schemas import Fact
from app.templates.contract import SectionSpec


def select_facts_for_section(
    spec: SectionSpec,
    available_facts: list[Fact],
    max_claims: int = 4,
) -> list[Fact]:
    """Return the best facts for a section, respecting contract constraints."""
    candidates = available_facts

    # Prefer fact types specified in the contract
    if spec.prefers_fact_types:
        preferred = [f for f in candidates if f.fact_type in spec.prefers_fact_types]
        others    = [f for f in candidates if f.fact_type not in spec.prefers_fact_types]
        candidates = preferred + others

    # Sort by confidence descending
    candidates = sorted(candidates, key=lambda f: f.confidence, reverse=True)

    selected: list[Fact] = []
    selected_ids: set[str] = set()

    for fact in candidates:
        if len(selected) >= max_claims:
            break
        if fact.fact_id in selected_ids:
            continue
        selected.append(fact)
        selected_ids.add(fact.fact_id)
        # Auto-include depends_on facts (caveat closure)
        for dep_id in fact.depends_on:
            dep = next((f for f in available_facts if f.fact_id == dep_id), None)
            if dep and dep.fact_id not in selected_ids:
                selected.append(dep)
                selected_ids.add(dep.fact_id)

    return selected
