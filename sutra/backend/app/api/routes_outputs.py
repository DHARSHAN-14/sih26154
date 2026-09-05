"""
api/routes_outputs.py — Output artifact access.
GET /api/sessions/{id}/jobs/{job_id}/outputs
GET /api/sessions/{id}/jobs/{job_id}/outputs/{output_id}/download
GET /api/sessions/{id}/jobs/{job_id}/outputs/{output_id}/provenance
"""
from __future__ import annotations
import json
import pathlib
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.deps import DbDep
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(
    prefix="/sessions/{session_id}/jobs/{job_id}/outputs",
    tags=["Outputs"],
)


@router.get("", summary="List outputs for a job")
async def list_outputs(session_id: str, job_id: str, db: DbDep) -> list[dict]:
    from sqlalchemy import select
    from app.db.models import OutputArtifact
    result = await db.execute(
        select(OutputArtifact).where(
            OutputArtifact.job_id == job_id,
            OutputArtifact.session_id == session_id,
        )
    )
    arts = result.scalars().all()
    return [
        {
            "id": a.id,
            "format": a.output_format,
            "verdict": a.validation_verdict,
            "visual_ok": a.visual_ok,
            "size_bytes": a.size_bytes,
            "mime_type": a.mime_type,
        }
        for a in arts
    ]


@router.get("/{output_id}/download", summary="Download rendered artifact")
async def download_output(
    session_id: str, job_id: str, output_id: str, db: DbDep
) -> FileResponse:
    from sqlalchemy import select
    from app.db.models import OutputArtifact
    from app.core.errors import JobNotFoundError
    result = await db.execute(
        select(OutputArtifact).where(OutputArtifact.id == output_id)
    )
    art = result.scalar_one_or_none()
    if not art or not art.file_path:
        raise JobNotFoundError(output_id)
    return FileResponse(
        path=art.file_path,
        media_type=art.mime_type,
        filename=pathlib.Path(art.file_path).name,
    )


@router.get("/{output_id}/provenance", summary="Claim -> fact -> source provenance")
async def get_provenance(
    session_id: str, job_id: str, output_id: str, db: DbDep
) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import OutputArtifact
    result = await db.execute(
        select(OutputArtifact).where(OutputArtifact.id == output_id)
    )
    art = result.scalar_one_or_none()
    if not art:
        return {"claims": []}
    content = json.loads(art.generated_content_json or "{}")
    return {"output_id": output_id, "provenance": content.get("provenance", [])}
