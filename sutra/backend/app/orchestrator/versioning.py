"""
orchestrator/versioning.py — Source v2 ingestion, diff, stale-output queueing.
Prior versions are never overwritten; auditability is structural.
"""
from __future__ import annotations
from app.core.schemas import SourceOfTruth
from app.sot.diff import diff, stale_outputs, SotDiff


def compute_stale(
    v1: SourceOfTruth,
    v2: SourceOfTruth,
    output_citations: dict[str, set[str]],
) -> tuple[SotDiff, list[str]]:
    """
    Compare v1 and v2 SoTs, return (diff, stale_output_ids).
    stale_output_ids are the outputs that need regeneration.
    """
    d = diff(v1, v2)
    stale = stale_outputs(d, output_citations)
    return d, stale
