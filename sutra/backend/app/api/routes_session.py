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
    operatorId: str = "operator"
    classification: str = "unclassified"


# In-memory store for session configs
_session_configs: dict[str, list[dict]] = {}


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
        operatorId="operator",
        classification="unclassified",
    )


@router.get("/{session_id}", summary="Get session info")
async def get_session(session_id: str, db: DbDep) -> SessionOut:
    from sqlalchemy import select
    from app.core.errors import SessionNotFoundError
    result = await db.execute(
        select(Session).where(Session.id == session_id).limit(1)
    )
    session = result.scalars().first()
    if not session:
        raise SessionNotFoundError(session_id)
    return SessionOut(
        id=session.id,
        artifact_dir=session.artifact_dir,
        qdrant_collection=session.qdrant_collection,
        created_at=session.created_at,
        operatorId="operator",
        classification="unclassified",
    )


@router.get("/{session_id}/configs", summary="List output configs for session")
async def list_configs(session_id: str) -> list[dict]:
    return _session_configs.get(session_id, [])


@router.post("/{session_id}/configs", summary="Save output config for session")
async def create_config(session_id: str, config: dict) -> dict:
    configs = _session_configs.setdefault(session_id, [])
    # Replace if id matches, else append
    existing_idx = next((i for i, c in enumerate(configs) if c.get("id") == config.get("id")), -1)
    if existing_idx >= 0:
        configs[existing_idx] = config
    else:
        configs.append(config)
    return config


@router.patch("/{session_id}/configs/{config_id}", summary="Update output config")
async def update_config(session_id: str, config_id: str, updates: dict) -> dict:
    configs = _session_configs.setdefault(session_id, [])
    for c in configs:
        if c.get("id") == config_id:
            c.update(updates)
            return c
    return updates


@router.delete("/{session_id}/configs/{config_id}", summary="Delete output config")
async def delete_config(session_id: str, config_id: str) -> dict:
    configs = _session_configs.get(session_id, [])
    _session_configs[session_id] = [c for c in configs if c.get("id") != config_id]
    return {"status": "deleted", "id": config_id}

