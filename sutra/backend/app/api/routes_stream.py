"""
api/routes_stream.py — Server-Sent Events for live pipeline stage view.
GET /api/sessions/{id}/stream
Heartbeat every 15s; replays last N events on reconnect.
"""
from __future__ import annotations
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core import events as event_bus
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions/{session_id}/stream", tags=["Stream"])

HEARTBEAT_INTERVAL = 15   # seconds


@router.get("", summary="SSE stream for pipeline stages")
async def stream_events(session_id: str) -> StreamingResponse:
    return StreamingResponse(
        _generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _generator(session_id: str) -> AsyncGenerator[str, None]:
    q = event_bus.subscribe(session_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL)
                data = event.model_dump_json()
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat comment to keep the connection alive through proxies
                yield f": heartbeat {datetime.utcnow().isoformat()}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        event_bus.unsubscribe(session_id, q)
