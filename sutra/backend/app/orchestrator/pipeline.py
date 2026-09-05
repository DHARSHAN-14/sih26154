"""
orchestrator/pipeline.py — The stage graph.
Runs ingest -> sanitize -> route -> retrieve -> extract -> KG -> SoT -> lock,
then fans out per selected output through plan -> generate -> validate -> render
-> visual validate -> repair, then cross-output pass, then finalize.
Emits a StageEvent at every transition.
"""
from __future__ import annotations
import asyncio
import time
import uuid
from typing import Any

from app.core import events as event_bus
from app.core.logging import get_logger
from app.orchestrator.stages import StageContext, STAGE_NAMES

logger = get_logger(__name__)


async def _stage(
    ctx: StageContext, name: str, fn, *args, **kwargs
) -> Any:
    t0 = time.monotonic()
    await event_bus.emit(ctx.session_id, ctx.job_id, name, "started")
    try:
        result = await fn(ctx, *args, **kwargs) if asyncio.iscoroutinefunction(fn)                  else fn(ctx, *args, **kwargs)
        elapsed = int((time.monotonic() - t0) * 1000)
        await event_bus.emit(ctx.session_id, ctx.job_id, name, "done",
                             elapsed_ms=elapsed)
        return result
    except Exception as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        await event_bus.emit(ctx.session_id, ctx.job_id, name, "failed",
                             message=str(exc), elapsed_ms=elapsed)
        raise


# ─── Stub stage functions (filled in per phase) ───────────────────────────────

async def _ingest(ctx: StageContext) -> None:
    """Phase 1: Docling ingestion, OCR, ASR."""
    logger.info("[stub] ingest", session=ctx.session_id)


async def _sanitize(ctx: StageContext) -> None:
    """Phase 1: Prompt-injection sanitization."""
    logger.info("[stub] sanitize")


async def _route(ctx: StageContext) -> None:
    """Phase 2: Route A / Route B decision."""
    logger.info("[stub] route")


async def _retrieve(ctx: StageContext) -> None:
    """Phase 2: Hybrid retrieval (Route B only)."""
    logger.info("[stub] retrieve")


async def _extract_facts(ctx: StageContext) -> None:
    """Phase 2: N-pass constrained fact extraction."""
    logger.info("[stub] extract_facts")


async def _build_kg(ctx: StageContext) -> None:
    """Phase 2: Triple extraction + KG build."""
    logger.info("[stub] build_kg")


async def _build_sot(ctx: StageContext) -> None:
    """Phase 2: Assemble Source of Truth."""
    logger.info("[stub] build_sot")


async def _lock_sot(ctx: StageContext) -> None:
    """Phase 2: Freeze + hash the SoT."""
    logger.info("[stub] lock_sot")


async def _plan(ctx: StageContext, output_format: str) -> None:
    """Phase 3: Content planning per format."""
    logger.info("[stub] plan", format=output_format)


async def _generate(ctx: StageContext, output_format: str) -> None:
    """Phase 3: LLM generation with structured output."""
    logger.info("[stub] generate", format=output_format)


async def _validate_facts(ctx: StageContext, output_format: str) -> None:
    """Phase 5: Citation + grounding + entailment + dependency checks."""
    logger.info("[stub] validate_facts", format=output_format)


async def _render(ctx: StageContext, output_format: str) -> None:
    """Phase 4: Template renderer."""
    logger.info("[stub] render", format=output_format)


async def _validate_visual(ctx: StageContext, output_format: str) -> None:
    """Phase 4: Visual / layout validation."""
    logger.info("[stub] validate_visual", format=output_format)


async def _cross_check(ctx: StageContext) -> None:
    """Phase 5: Cross-output contradiction check."""
    logger.info("[stub] cross_check")


async def _finalize(ctx: StageContext) -> None:
    """Phase 6: Provenance panel + audit trail."""
    logger.info("[stub] finalize")


# ─── Main pipeline entry point ────────────────────────────────────────────────

async def run(ctx: StageContext) -> None:
    """
    Run the full pipeline for a job.
    Phases 1-6 are stubbed; each will be replaced as phases complete.
    """
    logger.info("Pipeline starting",
                job=ctx.job_id, formats=ctx.formats,
                session=ctx.session_id)

    # Sequential pre-generation stages
    for stage_fn, name in [
        (_ingest,        "ingest"),
        (_sanitize,      "sanitize"),
        (_route,         "route"),
        (_retrieve,      "retrieve"),
        (_extract_facts, "extract_facts"),
        (_build_kg,      "build_kg"),
        (_build_sot,     "build_sot"),
        (_lock_sot,      "lock_sot"),
    ]:
        await _stage(ctx, name, stage_fn)

    # Fan-out: one set of stages per output format
    for fmt in ctx.formats:
        for stage_fn, name in [
            (_plan,           f"plan:{fmt}"),
            (_generate,       f"generate:{fmt}"),
            (_validate_facts, f"validate_facts:{fmt}"),
            (_render,         f"render:{fmt}"),
            (_validate_visual, f"validate_visual:{fmt}"),
        ]:
            try:
                await _stage(ctx, name, stage_fn, fmt)
            except Exception as exc:
                logger.warning("Format stage failed, continuing",
                               format=fmt, error=str(exc))

    # Post-generation stages
    await _stage(ctx, "cross_check", _cross_check)
    await _stage(ctx, "finalize",    _finalize)

    logger.info("Pipeline complete", job=ctx.job_id)
