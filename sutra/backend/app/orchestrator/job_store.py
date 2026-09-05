"""
orchestrator/job_store.py — In-process job registry backed by the DB.
Provides create / update / get for jobs and per-output status.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Job, OutputArtifact, StageEventRecord
from app.core.schemas import StageEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_job(
    db: AsyncSession,
    session_id: str,
    sot_id: str,
    formats: list[str],
    params: dict,
) -> Job:
    job = Job(
        id=str(uuid.uuid4()),
        session_id=session_id,
        sot_id=sot_id,
        status="queued",
        formats=json.dumps(formats),
        params_json=json.dumps(params),
    )
    db.add(job)
    await db.flush()
    logger.info("Job created", job_id=job.id, formats=formats)
    return job


async def start_job(db: AsyncSession, job_id: str) -> Job | None:
    job = await db.get(Job, job_id)
    if job:
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
    return job


async def finish_job(
    db: AsyncSession, job_id: str, success: bool, error: str = ""
) -> Job | None:
    job = await db.get(Job, job_id)
    if job:
        job.status = "completed" if success else "failed"
        job.finished_at = datetime.now(timezone.utc)
        if error:
            job.error_message = error
    return job


async def record_event(db: AsyncSession, event: StageEvent) -> None:
    rec = StageEventRecord(
        id=event.event_id,
        job_id=event.job_id,
        session_id=event.session_id,
        stage=event.stage,
        status=event.status,
        message=event.message,
        elapsed_ms=event.elapsed_ms,
        counters_json=json.dumps(event.counters),
        occurred_at=event.timestamp,
    )
    db.add(rec)
