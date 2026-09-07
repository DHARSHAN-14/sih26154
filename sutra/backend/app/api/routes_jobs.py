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

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.deps import DbDep, SettingsDep
from app.core.errors import SoTNotLockedError, SessionNotFoundError
from app.core.logging import get_logger
from app.orchestrator.pipeline import run
from app.orchestrator.stages import StageContext
from app.orchestrator.job_store import create_job, start_job
from app.core import events as event_bus

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions/{session_id}/jobs", tags=["Jobs"])
flat_router = APIRouter(prefix="/jobs", tags=["Jobs"])


class GenerateRequest(BaseModel):
    formats: list[str] = Field(default_factory=list)
    outputConfigIds: list[str] = Field(default_factory=list)
    sessionId: str | None = None
    session_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    configs: list[dict[str, Any]] = Field(default_factory=list)


class JobOut(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    # Frontend aliases
    id: str = ""
    sessionId: str = ""
    createdAt: str = ""
    outputCount: int = 0
    outputConfigIds: list[str] = Field(default_factory=list)
    progress: int = 0
    stages: list = Field(default_factory=list)

    @classmethod
    def create(cls, job_id: str, session_id: str, status: str, created_at: datetime, formats: list[str]) -> "JobOut":
        return cls(
            job_id=job_id,
            status=status,
            created_at=created_at,
            id=job_id,
            sessionId=session_id,
            createdAt=created_at.isoformat(),
            outputCount=len(formats),
            outputConfigIds=formats,
            progress=0,
            stages=[],
        )


async def _run_pipeline(ctx: StageContext) -> None:
    try:
        await run(ctx)
    except Exception as exc:
        logger.exception("Pipeline failed", job_id=ctx.job_id, error=str(exc))
        from app.db.session import AsyncSessionLocal
        from app.db.models import Job
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            j_res = await db.execute(select(Job).where(Job.id == ctx.job_id).limit(1))
            j = j_res.scalars().first()
            if j:
                j.status = "failed"
                j.error_message = str(exc)
            await db.commit()


def _normalize_formats(body: GenerateRequest) -> list[str]:
    fmts = []
    if body.configs:
        for c in body.configs:
            f = c.get("templateId") or c.get("type") or c.get("output_format")
            if f:
                fmts.append(f)
    if not fmts and body.formats:
        fmts = list(body.formats)
    if not fmts and body.outputConfigIds:
        for oc in body.outputConfigIds:
            if not oc.startswith("cfg-"):
                fmts.append(oc)

    _MAP = {
        "press_release": "advisory",
        "executive_brief": "executive_summary",
        "social_post": "linkedin",
        "technical_report": "advisory",
        "intelligence_summary": "executive_summary",
        "operational_bulletin": "advisory",
    }
    canonical = []
    for f in fmts:
        norm = _MAP.get(f, f)
        if norm in ["advisory", "executive_summary", "presentation", "linkedin", "twitter_x", "infographic", "video_package"]:
            if norm not in canonical:
                canonical.append(norm)
        elif norm not in canonical and not norm.startswith("cfg-"):
            canonical.append(norm)

    return canonical or ["advisory", "executive_summary", "presentation"]


async def _dispatch_job(session_id: str, formats: list[str], params: dict, background_tasks: BackgroundTasks, db, settings) -> JobOut:
    from sqlalchemy import select
    from app.db.models import SotVersion, Session, FactRecord
    import hashlib

    # Verify session exists
    sess_res = await db.execute(select(Session).where(Session.id == session_id).limit(1))
    sess = sess_res.scalars().first()
    if not sess:
        raise SessionNotFoundError(session_id)

    # Fetch SoT
    sot_res = await db.execute(
        select(SotVersion)
        .where(SotVersion.session_id == session_id)
        .order_by(SotVersion.version.desc())
        .limit(1)
    )
    sot = sot_res.scalars().first()

    # If SoT exists but not locked, lock it
    if sot and not sot.is_locked:
        facts_res = await db.execute(select(FactRecord).where(FactRecord.sot_id == sot.id))
        facts = facts_res.scalars().all()
        entries = sorted(f.id + "|" + f.canonical_text for f in facts)
        sot.lock_hash = hashlib.sha256(json.dumps(entries).encode()).hexdigest()
        sot.is_locked = True
        sot.locked_at = datetime.now(timezone.utc)
        await db.flush()

    sot_id = sot.id if sot else "sot-default"

    # Default to advisory format if none passed
    if not formats:
        formats = ["advisory", "executive_summary", "presentation"]

    job = await create_job(db, session_id, sot_id, formats, params)
    await db.commit()

    ctx = StageContext(
        session_id=session_id,
        job_id=job.id,
        sot_id=sot_id,
        artifact_dir=sess.artifact_dir,
        params=params,
        source_paths=[],
        formats=formats,
    )

    background_tasks.add_task(_run_pipeline, ctx)
    logger.info("Generation job queued", job_id=job.id, formats=formats)

    return JobOut.create(
        job_id=job.id,
        session_id=session_id,
        status="running",
        created_at=datetime.now(timezone.utc),
        formats=formats,
    )


# ─── Scoped routes for /sessions/{session_id}/jobs ────────────────────────────

@router.post("", summary="Start a generation job", status_code=202)
async def start_generation(
    session_id: str,
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: DbDep,
    settings: SettingsDep,
) -> JobOut:
    formats = _normalize_formats(body)
    return await _dispatch_job(session_id, formats, body.params, background_tasks, db, settings)


@router.get("/{job_id}", summary="Poll job status")
async def get_job(session_id: str, job_id: str, db: DbDep):
    from sqlalchemy import select
    from app.db.models import Job
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.session_id == session_id).limit(1)
    )
    job = result.scalars().first()
    if not job:
        from app.core.errors import JobNotFoundError
        raise JobNotFoundError(job_id)
    fmts = json.loads(job.formats) if job.formats else []
    return {
        "id": job.id,
        "job_id": job.id,
        "sessionId": job.session_id,
        "status": job.status,
        "formats": fmts,
        "outputConfigIds": fmts,
        "outputCount": len(fmts),
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error": job.error_message,
        "progress": 100 if job.status == "completed" else 50,
        "stages": [],
    }


# ─── Flat routes for /jobs ─────────────────────────────────────────────────────

@flat_router.post("", summary="Start a generation job (flat endpoint)", status_code=202)
async def flat_start_generation(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: DbDep,
    settings: SettingsDep,
) -> JobOut:
    from sqlalchemy import select
    from app.db.models import Session, SourceDocument, SotVersion

    session_id = body.sessionId or body.session_id
    sess = None
    if session_id:
        sess_res = await db.execute(select(Session).where(Session.id == session_id).limit(1))
        sess = sess_res.scalars().first()
        if not sess:
            doc_res = await db.execute(select(SourceDocument).where(SourceDocument.id == session_id).limit(1))
            doc = doc_res.scalars().first()
            if doc:
                sess_res = await db.execute(select(Session).where(Session.id == doc.session_id).limit(1))
                sess = sess_res.scalars().first()
        if not sess:
            sot_res = await db.execute(select(SotVersion).where(SotVersion.id == session_id).limit(1))
            sot = sot_res.scalars().first()
            if sot:
                sess_res = await db.execute(select(Session).where(Session.id == sot.session_id).limit(1))
                sess = sess_res.scalars().first()

    if not sess:
        sess_res = await db.execute(select(Session).order_by(Session.created_at.desc()).limit(1))
        sess = sess_res.scalars().first()
        if not sess:
            raise HTTPException(400, "No active session found")

    session_id = sess.id
    formats = _normalize_formats(body)
    return await _dispatch_job(session_id, formats, body.params, background_tasks, db, settings)


@flat_router.get("/{job_id}", summary="Poll job status (flat endpoint)")
async def flat_get_job(job_id: str, db: DbDep):
    from sqlalchemy import select
    from app.db.models import Job
    result = await db.execute(select(Job).where(Job.id == job_id).limit(1))
    job = result.scalars().first()
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    fmts = json.loads(job.formats) if job.formats else []
    return {
        "id": job.id,
        "job_id": job.id,
        "sessionId": job.session_id,
        "status": job.status,
        "formats": fmts,
        "outputConfigIds": fmts,
        "outputCount": len(fmts),
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error": job.error_message,
        "progress": 100 if job.status == "completed" else 50,
        "stages": [],
    }


@flat_router.post("/{job_id}/cancel", summary="Cancel a running job")
async def cancel_job(job_id: str, db: DbDep):
    from sqlalchemy import select
    from app.db.models import Job
    result = await db.execute(select(Job).where(Job.id == job_id).limit(1))
    job = result.scalars().first()
    if job:
        job.status = "cancelled"
        await db.flush()
    return {"status": "cancelled", "job_id": job_id}


@flat_router.get("/{job_id}/stream", summary="SSE stream for job stages")
async def stream_job_events(job_id: str, db: DbDep) -> StreamingResponse:
    from sqlalchemy import select
    from app.db.models import Job
    result = await db.execute(select(Job).where(Job.id == job_id).limit(1))
    job = result.scalars().first()
    session_id = job.session_id if job else job_id

    async def _sse():
        q = event_bus.subscribe(session_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    data = event.model_dump_json()
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f": heartbeat {datetime.now(timezone.utc).isoformat()}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe(session_id, q)

    return StreamingResponse(
        _sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

