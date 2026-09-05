"""
sot/extractor.py — N-pass constrained fact extraction (stub).
Each extracted fact must carry provenance; reject any without one.
Self-consistency: facts appearing in ≥2 passes get an agreement bonus.
Full impl: schema-constrained LLM decoding via structured_outputs.
"""
from __future__ import annotations
from app.core.schemas import Fact, Provenance, NormalizedValues
from app.core.ids import generate_fact_id
from app.ingest.chunker import Chunk
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_facts_from_chunks(
    chunks: list[Chunk],
    n_passes: int = 1,
) -> list[Fact]:
    """
    Extract facts from chunks using N self-consistency passes.
    Stub: returns one dummy fact per chunk for pipeline testing.
    Replace with constrained LLM call in Phase 2.
    """
    facts: list[Fact] = []
    for i, chunk in enumerate(chunks):
        if not chunk.provenance:
            logger.warning("Chunk has no provenance, skipping", chunk_id=chunk.chunk_id)
            continue
        fact = Fact(
            fact_id=generate_fact_id(i + 1),
            fact_type="claim",
            subject="[stub subject]",
            predicate="[stub predicate]",
            object="[stub object]",
            canonical_text=chunk.text[:300],
            normalized=NormalizedValues(),
            provenance=chunk.provenance[:1],
            confidence=0.8,
            extraction_pass=1,
        )
        facts.append(fact)
    return facts
