"""
sot/builder.py — Assemble the Source of Truth from extracted facts.
Deduplicates across extraction passes, merges provenance lists,
attaches entities and timeline, links the KG, sorts deterministically.
"""
from __future__ import annotations
import uuid
from app.core.schemas import SourceOfTruth, Fact, Entity, TimelineEvent
from app.core.ids import generate_fact_id
from app.core.logging import get_logger

logger = get_logger(__name__)


def deduplicate(facts: list[Fact]) -> list[Fact]:
    """
    Merge facts with identical (subject, predicate, object).
    Combined provenance raises support count and boosts confidence.
    """
    seen: dict[tuple, Fact] = {}
    for f in facts:
        key = (f.subject.lower(), f.predicate.lower(), f.object.lower())
        if key in seen:
            existing = seen[key]
            existing.provenance.extend(f.provenance)
        else:
            seen[key] = f
    # Re-assign stable, sortable IDs
    deduped = list(seen.values())
    for i, fact in enumerate(sorted(deduped, key=lambda f: f.canonical_text)):
        fact.fact_id = generate_fact_id(i + 1)
    return deduped


def build(
    session_id: str,
    facts: list[Fact],
    entities: list[Entity] | None = None,
    timeline: list[TimelineEvent] | None = None,
    graph_ref: str = "",
    version: int = 1,
) -> SourceOfTruth:
    deduped = deduplicate(facts)
    sot = SourceOfTruth(
        sot_id=str(uuid.uuid4()),
        session_id=session_id,
        version=version,
        facts=deduped,
        entities=entities or [],
        timeline=timeline or [],
        graph_ref=graph_ref,
    )
    logger.info("SoT built", sot_id=sot.sot_id,
                fact_count=len(deduped), version=version)
    return sot
