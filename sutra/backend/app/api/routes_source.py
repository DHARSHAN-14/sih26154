"""
api/routes_source.py — Source document upload and ingestion status.
POST /api/sessions/{id}/sources  — upload files
GET  /api/sessions/{id}/sources  — list ingested sources
"""
from __future__ import annotations
import pathlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.deps import DbDep, SettingsDep
from app.core.ids import generate_doc_id
from app.core.hashing import hash_bytes
from app.core.errors import UnsupportedSourceTypeError, SessionNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions/{session_id}/sources", tags=["Sources"])


class SourceOut(BaseModel):
    doc_id: str
    filename: str
    mime_type: str
    status: str
    file_hash: str
    uploaded_at: datetime


@router.post("", summary="Upload source documents", status_code=202)
async def upload_sources(
    session_id: str,
    db: DbDep,
    settings: SettingsDep,
    files: list[UploadFile] = File(...),
) -> list[SourceOut]:
    from sqlalchemy import select
    from app.db.models import Session, SourceDocument

    sess_res = await db.execute(select(Session).where(Session.id == session_id))
    sess = sess_res.scalar_one_or_none()
    if not sess:
        raise SessionNotFoundError(session_id)

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    results: list[SourceOut] = []

    for file in files:
        content = await file.read()
        if len(content) > max_bytes:
            raise HTTPException(413, f"File {file.filename!r} exceeds size limit")

        doc_id = generate_doc_id()
        file_hash = hash_bytes(content)
        mime = file.content_type or "application/octet-stream"

        # Save to session artifact dir
        dest_dir = pathlib.Path(sess.artifact_dir) / "uploads"
        dest_dir.mkdir(parents=True, exist_ok=True)
        suffix = pathlib.Path(file.filename or "upload").suffix
        dest_path = dest_dir / (doc_id + suffix)
        dest_path.write_bytes(content)

        doc = SourceDocument(
            id=doc_id,
            session_id=session_id,
            original_filename=file.filename or "unknown",
            mime_type=mime,
            file_hash=file_hash,
            file_path=str(dest_path),
            status="uploaded",
        )
        db.add(doc)
        await db.flush()

        results.append(SourceOut(
            doc_id=doc_id,
            filename=file.filename or "unknown",
            mime_type=mime,
            status="uploaded",
            file_hash=file_hash,
            uploaded_at=datetime.now(timezone.utc),
        ))
        logger.info("Source uploaded", doc_id=doc_id, session=session_id)

    return results


@router.get("", summary="List sources for a session")
async def list_sources(session_id: str, db: DbDep) -> list[SourceOut]:
    from sqlalchemy import select
    from app.db.models import SourceDocument
    result = await db.execute(
        select(SourceDocument).where(SourceDocument.session_id == session_id)
    )
    docs = result.scalars().all()
    return [
        SourceOut(
            doc_id=d.id,
            filename=d.original_filename,
            mime_type=d.mime_type,
            status=d.status,
            file_hash=d.file_hash,
            uploaded_at=d.created_at,
        )
        for d in docs
    ]
