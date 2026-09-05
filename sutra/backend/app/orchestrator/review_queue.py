"""
orchestrator/review_queue.py — Holds outputs that exhausted repair attempts.
Human-in-the-loop: accept / regenerate / edit actions.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ReviewItem
from app.core.schemas import ValidationReport


async def enqueue(
    db: AsyncSession,
    session_id: str,
    output_id: str,
    failure_type: str,
    report: ValidationReport,
) -> ReviewItem:
    item = ReviewItem(
        id=str(uuid.uuid4()),
        session_id=session_id,
        output_id=output_id,
        failure_type=failure_type,
        evidence_json=report.model_dump_json(),
        status="pending",
    )
    db.add(item)
    await db.flush()
    return item


async def resolve(
    db: AsyncSession,
    item_id: str,
    resolution: str,   # "accepted" | "regenerated" | "edited"
) -> ReviewItem | None:
    item = await db.get(ReviewItem, item_id)
    if item:
        item.status = "resolved"
        item.resolution = resolution
        item.resolved_at = datetime.now(timezone.utc)
    return item
