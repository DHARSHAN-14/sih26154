"""
api/routes_sot.py — Operator control surface over the Source of Truth.
GET  /api/sessions/{id}/sot         — full fact table
POST /api/sessions/{id}/sot/lock    — freeze and return hash
POST /api/sessions/{id}/sot/facts/{fid}/exclude  — exclude a fact
"""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import DbDep, SettingsDep
from app.core.errors import SessionNotFoundError, SoTAlreadyLockedError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions/{session_id}/sot", tags=["Source of Truth"])


class SotSummary(BaseModel):
    sot_id: str | None
    version: int
    fact_count: int
    is_locked: bool
    lock_hash: str | None


@router.get("", summary="Get current Source of Truth summary")
async def get_sot(session_id: str, db: DbDep) -> SotSummary:
    from sqlalchemy import select
    from app.db.models import SotVersion
    result = await db.execute(
        select(SotVersion)
        .where(SotVersion.session_id == session_id)
        .order_by(SotVersion.version.desc())
    )
    sot = result.scalar_one_or_none()
    if not sot:
        return SotSummary(sot_id=None, version=0, fact_count=0,
                          is_locked=False, lock_hash=None)
    return SotSummary(
        sot_id=sot.id,
        version=sot.version,
        fact_count=sot.fact_count,
        is_locked=sot.is_locked,
        lock_hash=sot.lock_hash,
    )


class LockResponse(BaseModel):
    sot_id: str
    lock_hash: str
    fact_count: int


@router.post("/lock", summary="Lock the Source of Truth")
async def lock_sot(session_id: str, db: DbDep) -> LockResponse:
    from sqlalchemy import select
    from datetime import datetime, timezone
    from app.db.models import SotVersion
    from app.core.hashing import hash_bytes
    import hashlib, json

    result = await db.execute(
        select(SotVersion)
        .where(SotVersion.session_id == session_id)
        .order_by(SotVersion.version.desc())
    )
    sot = result.scalar_one_or_none()
    if not sot:
        raise SessionNotFoundError(session_id)
    if sot.is_locked:
        raise SoTAlreadyLockedError()

    # Compute hash over fact canonical texts
    from app.db.models import FactRecord
    facts_res = await db.execute(
        select(FactRecord).where(FactRecord.sot_id == sot.id)
    )
    facts = facts_res.scalars().all()
    entries = sorted(f.id + "|" + f.canonical_text for f in facts)
    lock_hash = hashlib.sha256(json.dumps(entries).encode()).hexdigest()

    sot.lock_hash = lock_hash
    sot.is_locked = True
    sot.locked_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info("SoT locked", session_id=session_id,
                lock_hash=lock_hash[:16] + "...")
    return LockResponse(sot_id=sot.id, lock_hash=lock_hash,
                        fact_count=sot.fact_count)
