from __future__ import annotations
import asyncio
import uuid
from datetime import datetime
from typing import Any
from app.core.schemas import StageEvent

_subscribers: dict[str, list[asyncio.Queue]] = {}


def _build(session_id, job_id, stage, status, message="", elapsed_ms=0,
           counters=None, artifact_refs=None) -> StageEvent:
    return StageEvent(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        job_id=job_id,
        stage=stage,
        status=status,
        message=message,
        elapsed_ms=elapsed_ms,
        counters=counters or {},
        artifact_refs=artifact_refs or [],
        timestamp=datetime.utcnow(),
    )


async def emit(session_id: str, job_id: str, stage: str, status: str,
               message: str = "", elapsed_ms: int = 0,
               counters: dict | None = None,
               artifact_refs: list[str] | None = None) -> StageEvent:
    event = _build(session_id, job_id, stage, status,
                   message, elapsed_ms, counters, artifact_refs)
    for q in _subscribers.get(session_id, []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
    return event


def subscribe(session_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.setdefault(session_id, []).append(q)
    return q


def unsubscribe(session_id: str, q: asyncio.Queue) -> None:
    lst = _subscribers.get(session_id, [])
    if q in lst:
        lst.remove(q)
