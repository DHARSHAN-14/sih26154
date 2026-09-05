"""
kg/extractor.py — Schema-constrained triple extraction (stub).
Uses a controlled predicate vocabulary so contradiction detection works.
Full implementation: constrained LLM decoding with structured_outputs.
"""
from __future__ import annotations
from dataclasses import dataclass
from app.core.schemas import Provenance

CONTROLLED_PREDICATES = {
    "affects", "mitigates", "discloses", "patches", "exploits",
    "contains", "precedes", "follows", "is_type_of", "has_severity",
    "has_version", "has_cve", "operates_in", "reports_to",
}


@dataclass
class Triple:
    subject: str
    predicate: str
    object: str
    fact_id: str
    provenance: Provenance | None = None
    temporal_qualifier: str | None = None


def extract_triples(
    text: str,
    fact_id: str,
    provenance: Provenance | None = None,
) -> list[Triple]:
    """
    Extract subject-predicate-object triples from text.
    Stub returns empty list. Replace with constrained LLM call in Phase 2.
    """
    return []
