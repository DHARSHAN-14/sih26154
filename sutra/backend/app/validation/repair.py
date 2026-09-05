"""
validation/repair.py — Targeted repair of validation failures.
Repairs one section at a time — not one document.
Caps at MAX_REPAIR_ATTEMPTS; escalates to review queue if exhausted.
"""
from __future__ import annotations
from app.core.schemas import (
    GeneratedOutput, SourceOfTruth, ValidationReport,
    RepairInstruction, UnsupportedToken,
)
from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_repair_instruction(
    token: UnsupportedToken,
    permitted_fact_ids: list[str],
    attempt: int,
) -> RepairInstruction:
    return RepairInstruction(
        claim_id=token.claim_id,
        failure_type="grounding",
        offending_span=token.token,
        char_start=token.char_start,
        char_end=token.char_end,
        permitted_fact_ids=permitted_fact_ids,
        attempt=attempt,
    )


async def attempt_repair(
    output: GeneratedOutput,
    report: ValidationReport,
    sot: SourceOfTruth,
    attempt: int = 1,
) -> tuple[GeneratedOutput, bool]:
    """
    Try to repair unsupported tokens deterministically first, then via LLM.
    Returns (repaired_output, success).
    Stub: no-op repair, always marks success=False so review queue gets it.
    """
    cfg = get_settings()
    if attempt > cfg.max_repair_attempts:
        logger.warning("Max repair attempts reached", output_id=output.output_id)
        return output, False

    # Stub: just log and return unchanged
    logger.info("Repair attempted (stub)", output_id=output.output_id, attempt=attempt)
    return output, False
