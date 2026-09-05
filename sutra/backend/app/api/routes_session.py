"""
api/routes_session.py — Session lifecycle.
POST /api/sessions creates an isolated operator workspace.
Everything downstream is scoped by session_id.
"""
from __future__ import annotations
import pathlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import DbDep, SettingsDep
from app.db.models import Session
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions", tags=["Sessions"])


class SessionOut(BaseModel):
    id: str
    artifact_dir: str
    qdrant_collection: str
    created_at: datetime


@router.post("", summary="Create a new operator session", status_code=201)
async def create_session(settings: SettingsDep, db: DbDep) -> SessionOut:
    session_id = str(uuid.uuid4())
    artifact_dir = str(
        pathlib.Path(settings.artifact_dir) / session_id
    )
    pathlib.Path(artifact_dir).mkdir(parents=True, exist_ok=True)

    qdrant_col = f"{settings.qdrant_collection_prefix}_{session_id.replace('-', '_')[:16]}"

    session = Session(
        id=session_id,
        artifact_dir=artifact_dir,
        qdrant_collection=qdrant_col,
        is_active=True,
    )
    db.add(session)
    await db.flush()

    logger.info("Session created", session_id=session_id)
    return SessionOut(
        id=session_id,
        artifact_dir=artifact_dir,
        qdrant_collection=qdrant_col,
        created_at=datetime.now(timezone.utc),
    )


@router.get("/{session_id}", summary="Get session info")
async def get_session(session_id: str, db: DbDep) -> SessionOut:
    from sqlalchemy import select
    from app.core.errors import SessionNotFoundError
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise SessionNotFoundError(session_id)
    return SessionOut(
        id=session.id,
        artifact_dir=session.artifact_dir,
        qdrant_collection=session.qdrant_collection,
        created_at=session.created_at,
    )
