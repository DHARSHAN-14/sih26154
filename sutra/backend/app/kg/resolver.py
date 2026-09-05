"""
kg/resolver.py — Entity resolution: clusters surface forms into canonical IDs.
Prevents one real-world entity from producing two contradictory facts.
Stub: exact-match resolution. Replace with embedding similarity clustering.
"""
from __future__ import annotations
from app.core.schemas import Entity


def resolve_entities(
    surface_forms: list[str],
) -> dict[str, str]:
    """
    Map surface forms to canonical IDs.
    Returns {surface_form: canonical_id}.
    Stub: canonical_id = normalized lower-case form.
    """
    resolved: dict[str, str] = {}
    for sf in surface_forms:
        canonical = sf.strip().lower().replace(" ", "_")
        resolved[sf] = canonical
    return resolved


def build_entities(
    surface_to_canonical: dict[str, str],
    fact_ids_by_surface: dict[str, list[str]],
    entity_types: dict[str, str] | None = None,
) -> list[Entity]:
    entity_types = entity_types or {}
    canonical_to_surfaces: dict[str, list[str]] = {}
    canonical_to_facts: dict[str, list[str]] = {}

    for surf, cid in surface_to_canonical.items():
        canonical_to_surfaces.setdefault(cid, []).append(surf)
        for fid in fact_ids_by_surface.get(surf, []):
            canonical_to_facts.setdefault(cid, []).append(fid)

    return [
        Entity(
            canonical_id=cid,
            entity_type=entity_types.get(cid, "UNKNOWN"),
            surface_forms=surfs,
            fact_ids=canonical_to_facts.get(cid, []),
        )
        for cid, surfs in canonical_to_surfaces.items()
    ]
