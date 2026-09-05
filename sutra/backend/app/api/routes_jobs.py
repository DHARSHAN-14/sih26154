"""
api/routes_jobs.py — Generation job lifecycle.
POST /api/sessions/{id}/jobs  — start generation
GET  /api/sessions/{id}/jobs/{job_id}  — poll status
"""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.deps import DbDep, SettingsDep
from app.core.errors import SoTNotLockedError, SessionNotFoundError
from app.core.logging import get_logger
from app.orchestrator.pipeline import run
from app.orchestrator.stages import StageContext
from app.orchestrator.job_store import create_job, start_job

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions/{session_id}/jobs", tags=["Jobs"])


class GenerateRequest(BaseModel):
    formats: list[str]
    params: dict[str, Any] = {}


class JobOut(BaseModel):
    job_id: str
    status: str
    created_at: datetime


@router.post("", summary="Start a generation job", status_code=202)
async def start_generation(
    session_id: str,
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: DbDep,
    settings: SettingsDep,
) -> JobOut:
    from sqlalchemy import select
    from app.db.models import SotVersion, Session

    # Verify session exists
    sess_res = await db.execute(select(Session).where(Session.id == session_id))
    sess = sess_res.scalar_one_or_none()
    if not sess:
        raise SessionNotFoundError(session_id)

    # Verify SoT is locked
    sot_res = await db.execute(
        select(SotVersion)
        .where(SotVersion.session_id == session_id)
        .order_by(SotVersion.version.desc())
    )
    sot = sot_res.scalar_one_or_none()
    if not sot or not sot.is_locked:
        raise SoTNotLockedError()

    job = await create_job(db, session_id, sot.id, body.formats, body.params)
    await db.commit()

    ctx = StageContext(
        session_id=session_id,
        job_id=job.id,
        sot_id=sot.id,
        artifact_dir=sess.artifact_dir,
        params=body.params,
        source_paths=[],
        formats=body.formats,
    )

    background_tasks.add_task(_run_pipeline, ctx)
    logger.info("Generation job queued", job_id=job.id, formats=body.formats)

    return JobOut(
        job_id=job.id,
        status="queued",
        created_at=datetime.now(timezone.utc),
    )


async def _run_pipeline(ctx: StageContext) -> None:
    try:
        await run(ctx)
    except Exception as exc:
        logger.exception("Pipeline failed", job_id=ctx.job_id, error=str(exc))


@router.get("/{job_id}", summary="Poll job status")
async def get_job(session_id: str, job_id: str, db: DbDep):
    from sqlalchemy import select
    from app.db.models import Job
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.session_id == session_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        from app.core.errors import JobNotFoundError
        raise JobNotFoundError(job_id)
    return {
        "job_id": job.id,
        "status": job.status,
        "formats": json.loads(job.formats),
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error": job.error_message,
    }
