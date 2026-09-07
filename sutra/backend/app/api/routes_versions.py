"""
api/routes_versions.py — SoT version history and stale output detection.
GET /api/sessions/{id}/versions           — list all SoT versions
GET /api/sessions/{id}/versions/{vid}     — get one version
POST /api/sessions/{id}/versions/compare  — diff two versions, show stale outputs
"""
from __future__ import annotations
import json
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from app.deps import DbDep
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(
    prefix="/sessions/{session_id}/versions",
    tags=["Versions"],
)
flat_router = APIRouter(
    prefix="/versions",
    tags=["Versions"],
)


class VersionOut(BaseModel):
    sot_id: str
    version: int
    fact_count: int
    is_locked: bool
    lock_hash: str | None
    locked_at: datetime | None
    created_at: datetime
    # Frontend aliases
    id: str = ""
    sessionId: str = ""
    createdAt: str = ""
    createdBy: str = "operator"
    sourceId: str = ""
    sourceName: str = ""
    artifactCount: int = 0
    status: str = "active"
    notes: str | None = None

    @classmethod
    def from_sot(cls, v, session_id: str = "") -> "VersionOut":
        c_str = v.created_at.isoformat() if v.created_at else datetime.now().isoformat()
        return cls(
            sot_id=v.id,
            version=v.version,
            fact_count=v.fact_count,
            is_locked=v.is_locked,
            lock_hash=v.lock_hash,
            locked_at=v.locked_at,
            created_at=v.created_at or datetime.now(),
            id=v.id,
            sessionId=session_id or v.session_id,
            createdAt=c_str,
            createdBy="operator",
            sourceId=v.session_id,
            sourceName=f"v{v.version} Source",
            artifactCount=0,
            status="active" if v.is_locked else "draft",
            notes=f"Source of Truth version {v.version} ({v.fact_count} verified facts)",
        )


@router.get("", summary="List all SoT versions for a session")
async def list_versions(session_id: str, db: DbDep) -> list[VersionOut]:
    from sqlalchemy import select
    from app.db.models import SotVersion
    result = await db.execute(
        select(SotVersion)
        .where(SotVersion.session_id == session_id)
        .order_by(SotVersion.version)
    )
    versions = result.scalars().all()
    return [VersionOut.from_sot(v, session_id) for v in versions]


@flat_router.get("/{session_id}", summary="List versions for a session (flat endpoint)")
async def flat_list_versions(session_id: str, db: DbDep) -> list[VersionOut]:
    from sqlalchemy import select
    from app.db.models import SotVersion
    result = await db.execute(
        select(SotVersion)
        .where(SotVersion.session_id == session_id)
        .order_by(SotVersion.version)
    )
    versions = result.scalars().all()
    return [VersionOut.from_sot(v, session_id) for v in versions]


@flat_router.get("/{session_id}/{version_id}", summary="Get specific version (flat endpoint)")
async def flat_get_version(session_id: str, version_id: str, db: DbDep) -> VersionOut:
    from app.db.models import SotVersion
    sot = await db.get(SotVersion, version_id)
    if not sot:
        from app.core.errors import SessionNotFoundError
        raise SessionNotFoundError(version_id)
    return VersionOut.from_sot(sot, session_id)


@flat_router.post("/{session_id}/{version_id}/restore", summary="Restore specific version")
async def flat_restore_version(session_id: str, version_id: str, db: DbDep) -> VersionOut:
    from app.db.models import SotVersion
    sot = await db.get(SotVersion, version_id)
    if not sot:
        from app.core.errors import SessionNotFoundError
        raise SessionNotFoundError(version_id)
    return VersionOut.from_sot(sot, session_id)


@router.get("/{sot_id}", summary="Get a specific SoT version")
async def get_version(session_id: str, sot_id: str, db: DbDep) -> VersionOut:
    from app.db.models import SotVersion
    from app.core.errors import SessionNotFoundError
    sot = await db.get(SotVersion, sot_id)
    if not sot:
        raise SessionNotFoundError(sot_id)
    return VersionOut.from_sot(sot, session_id)


class CompareRequest(BaseModel):
    v1_sot_id: str
    v2_sot_id: str
    output_citations: dict[str, list[str]] = {}   # output_id -> fact_ids


class CompareResult(BaseModel):
    added_count: int
    removed_count: int
    changed_count: int
    unchanged_count: int
    stale_output_ids: list[str]


@router.post("/compare", summary="Diff two SoT versions and detect stale outputs")
async def compare_versions(
    session_id: str,
    body: CompareRequest,
    db: DbDep,
) -> CompareResult:
    from sqlalchemy import select
    from app.db.models import SotVersion, FactRecord
    from app.core.schemas import SourceOfTruth, Fact, Provenance, NormalizedValues
    from app.sot.diff import diff, stale_outputs

    async def _load_sot(sot_id: str) -> SourceOfTruth:
        sot_rec = await db.get(SotVersion, sot_id)
        facts_res = await db.execute(
            select(FactRecord).where(FactRecord.sot_id == sot_id)
        )
        facts_raw = facts_res.scalars().all()
        facts = [
            Fact(
                fact_id=f.id,
                fact_type=f.fact_type,
                subject=f.subject,
                predicate=f.predicate,
                object=f.object_val,
                canonical_text=f.canonical_text,
                normalized=NormalizedValues(),
                provenance=[Provenance(
                    doc_id="unknown", locator="p1",
                    chunk_id="unknown", snippet=f.canonical_text[:100],
                )],
                confidence=f.confidence,
            )
            for f in facts_raw
        ]
        return SourceOfTruth(
            sot_id=sot_id,
            session_id=session_id,
            version=sot_rec.version if sot_rec else 1,
            facts=facts,
            lock_hash=sot_rec.lock_hash if sot_rec else None,
        )

    v1 = await _load_sot(body.v1_sot_id)
    v2 = await _load_sot(body.v2_sot_id)
    d = diff(v1, v2)

    citation_sets = {
        oid: set(fids)
        for oid, fids in body.output_citations.items()
    }
    stale = stale_outputs(d, citation_sets)

    return CompareResult(
        added_count=len(d.added),
        removed_count=len(d.removed),
        changed_count=len(d.changed),
        unchanged_count=len(d.unchanged),
        stale_output_ids=stale,
    )
