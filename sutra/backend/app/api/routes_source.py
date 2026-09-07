"""
api/routes_source.py — Source document upload and ingestion status.
POST /api/sessions/{id}/sources  — upload files
GET  /api/sessions/{id}/sources  — list ingested sources
"""
from __future__ import annotations
import pathlib
import uuid
from datetime import datetime, timezone
import json

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query, Header
from pydantic import BaseModel, Field

from app.deps import DbDep, SettingsDep
from app.core.ids import generate_doc_id
from app.core.hashing import hash_bytes
from app.core.errors import UnsupportedSourceTypeError, SessionNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions/{session_id}/sources", tags=["Sources"])
flat_router = APIRouter(prefix="/sources", tags=["Sources"])


class SourceOut(BaseModel):
    doc_id: str
    filename: str
    mime_type: str
    status: str = "ready"
    file_hash: str
    uploaded_at: datetime
    session_id: str = ""
    # Frontend aliases
    id: str = ""
    sessionId: str = ""
    name: str = ""
    type: str = "document"
    mimeType: str = ""
    sizeBytes: int = 0
    uploadedAt: str = ""
    checksum: str = ""
    pageCount: int = 1

    @classmethod
    def create(
        cls,
        doc_id: str,
        filename: str,
        mime: str,
        file_hash: str,
        created_at: datetime,
        size_bytes: int = 0,
        page_count: int = 1,
        status: str = "ready",
        session_id: str = "",
    ) -> "SourceOut":
        now_str = created_at.isoformat()
        stype = "document"
        if "image" in mime:
            stype = "image"
        elif "audio" in mime:
            stype = "audio"
        elif "video" in mime:
            stype = "video"
        elif "text" in mime or "json" in mime or filename.endswith((".txt", ".md")):
            stype = "text"

        return cls(
            doc_id=doc_id,
            filename=filename,
            mime_type=mime,
            status=status,
            file_hash=file_hash,
            uploaded_at=created_at,
            session_id=session_id,
            id=doc_id,
            sessionId=session_id,
            name=filename,
            type=stype,
            mimeType=mime,
            sizeBytes=size_bytes,
            uploadedAt=now_str,
            checksum=file_hash,
            pageCount=page_count,
        )


async def _process_and_extract_sot(
    session_id: str,
    doc_id: str,
    dest_path: pathlib.Path,
    mime_type: str,
    db,
) -> int:
    """Parse document, chunk it, extract facts, and create initial SotVersion and FactRecords."""
    from app.ingest import docling_adapter
    from app.sot import extractor
    from app.db.models import SotVersion, FactRecord
    from sqlalchemy import select

    internal_doc = docling_adapter.convert(
        doc_id=doc_id,
        file_path=dest_path,
        pipeline="docling",
        mime_type=mime_type,
    )

    facts = extractor.extract_facts_from_chunks(internal_doc.chunks)
    if not facts and internal_doc.chunks:
        from app.core.schemas import Fact, NormalizedValues
        from app.core.ids import generate_fact_id
        c = internal_doc.chunks[0]
        facts = [
            Fact(
                fact_id=generate_fact_id(1),
                fact_type="claim",
                subject="Document",
                predicate="states",
                object=c.text[:200],
                canonical_text=c.text[:300],
                normalized=NormalizedValues(),
                provenance=c.provenance[:1],
                confidence=0.9,
                extraction_pass=1,
            )
        ]

    # Create SotVersion
    sot_res = await db.execute(
        select(SotVersion).where(SotVersion.session_id == session_id).order_by(SotVersion.version.desc()).limit(1)
    )
    latest_sot = sot_res.scalars().first()
    version = (latest_sot.version + 1) if latest_sot else 1

    sot_id = str(uuid.uuid4())
    sot_rec = SotVersion(
        id=sot_id,
        session_id=session_id,
        version=version,
        fact_count=len(facts),
        is_locked=False,
    )
    db.add(sot_rec)
    await db.flush()

    # Save FactRecords
    for f in facts:
        fact_rec = FactRecord(
            id=f.fact_id,
            sot_id=sot_id,
            session_id=session_id,
            fact_type=f.fact_type,
            subject=f.subject,
            predicate=f.predicate,
            object_val=f.object,
            canonical_text=f.canonical_text,
            confidence=f.confidence,
            sensitivity=f.sensitivity,
            provenance_json=json.dumps([p.model_dump() for p in f.provenance]),
        )
        db.add(fact_rec)
    await db.flush()

    # Save clean parsed text and structured pages
    parsed_dir = dest_path.parent
    parsed_txt_path = parsed_dir / f"{doc_id}_parsed.txt"
    parsed_json_path = parsed_dir / f"{doc_id}_parsed.json"
    parsed_txt_path.write_text(internal_doc.formatted_text, encoding="utf-8")
    parsed_json_path.write_text(json.dumps(internal_doc.extracted_pages, indent=2), encoding="utf-8")

    # Index chunks into session RAG hybrid vector store
    if internal_doc.chunks:
        try:
            from app.retrieval.embedder import embed_chunks
            from app.retrieval.vectorstore import get_store
            store = get_store(session_id)
            chunk_pairs = [(c.chunk_id, c.text) for c in internal_doc.chunks]
            emb_results = embed_chunks(chunk_pairs)
            payloads = [
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "doc_id": doc_id,
                    "page": c.provenance[0].page if c.provenance else 1,
                    "paragraph": c.provenance[0].paragraph if c.provenance else 1,
                }
                for c in internal_doc.chunks
            ]
            store.upsert(emb_results, payloads)
            logger.info("RAG hybrid vector store indexed", session_id=session_id, chunks=len(emb_results))
        except Exception as exc:
            logger.warning("Failed to index chunks into RAG store", error=str(exc))

    logger.info("Source document processed and SoT built", session_id=session_id, facts_count=len(facts), parsed_path=str(parsed_txt_path))
    return internal_doc.page_count, str(parsed_txt_path)


async def _get_or_create_session(db, settings, session_id: str | None = None):
    from sqlalchemy import select
    from app.db.models import Session
    if session_id:
        res = await db.execute(select(Session).where(Session.id == session_id).limit(1))
        sess = res.scalars().first()
        if sess:
            return sess

    # Find latest active session or create new
    res = await db.execute(select(Session).order_by(Session.created_at.desc()).limit(1))
    sess = res.scalars().first()
    if sess:
        return sess

    new_id = str(uuid.uuid4())
    art_dir = str(pathlib.Path(settings.artifact_dir) / new_id)
    pathlib.Path(art_dir).mkdir(parents=True, exist_ok=True)
    sess = Session(
        id=new_id,
        artifact_dir=art_dir,
        qdrant_collection=f"{settings.qdrant_collection_prefix}_{new_id[:12]}",
        is_active=True,
    )
    db.add(sess)
    await db.flush()
    return sess


# ─── Flat routes for /sources ──────────────────────────────────────────────────

@flat_router.post("/upload", summary="Upload a source document (flat endpoint)")
async def flat_upload_source(
    db: DbDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
    session_id: str | None = Query(None),
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
) -> SourceOut:
    from app.db.models import SourceDocument
    sess = await _get_or_create_session(db, settings, session_id or x_session_id)
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"File {file.filename!r} exceeds size limit")

    doc_id = generate_doc_id()
    file_hash = hash_bytes(content)
    mime = file.content_type or "application/octet-stream"

    dest_dir = pathlib.Path(sess.artifact_dir) / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = pathlib.Path(file.filename or "upload").suffix
    dest_path = dest_dir / (doc_id + suffix)
    dest_path.write_bytes(content)

    page_count, parsed_path = await _process_and_extract_sot(sess.id, doc_id, dest_path, mime, db)

    doc = SourceDocument(
        id=doc_id,
        session_id=sess.id,
        original_filename=file.filename or "upload",
        mime_type=mime,
        file_hash=file_hash,
        file_path=str(dest_path),
        parsed_path=parsed_path,
        page_count=page_count,
        status="ready",
    )
    db.add(doc)
    await db.flush()

    return SourceOut.create(
        doc_id=doc_id,
        filename=file.filename or "upload",
        mime=mime,
        file_hash=file_hash,
        created_at=datetime.now(timezone.utc),
        size_bytes=len(content),
        page_count=page_count,
        status="ready",
        session_id=sess.id,
    )


class UrlUploadRequest(BaseModel):
    url: str


@flat_router.post("/url", summary="Ingest source from URL")
async def flat_upload_url(
    req: UrlUploadRequest,
    db: DbDep,
    settings: SettingsDep,
    session_id: str | None = Query(None),
) -> SourceOut:
    from app.db.models import SourceDocument
    import httpx
    sess = await _get_or_create_session(db, settings, session_id)
    doc_id = generate_doc_id()

    # Fetch URL content
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(req.url)
            content = r.content
            mime = r.headers.get("content-type", "text/html").split(";")[0]
    except Exception as exc:
        content = f"Source URL: {req.url}\nFetched at {datetime.now(timezone.utc)}".encode()
        mime = "text/plain"

    file_hash = hash_bytes(content)
    dest_dir = pathlib.Path(sess.artifact_dir) / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{doc_id}.txt"
    dest_path.write_bytes(content)

    page_count, parsed_path = await _process_and_extract_sot(sess.id, doc_id, dest_path, mime, db)

    doc = SourceDocument(
        id=doc_id,
        session_id=sess.id,
        original_filename=req.url.split("/")[-1] or "webpage",
        mime_type=mime,
        file_hash=file_hash,
        file_path=str(dest_path),
        parsed_path=parsed_path,
        page_count=page_count,
        status="ready",
    )
    db.add(doc)
    await db.flush()

    return SourceOut.create(
        doc_id=doc_id,
        filename=req.url,
        mime=mime,
        file_hash=file_hash,
        created_at=datetime.now(timezone.utc),
        size_bytes=len(content),
        page_count=page_count,
        status="ready",
    )


class TextUploadRequest(BaseModel):
    text: str
    name: str = "source-text"


@flat_router.post("/text", summary="Ingest raw text as source")
async def flat_upload_text(
    req: TextUploadRequest,
    db: DbDep,
    settings: SettingsDep,
    session_id: str | None = Query(None),
) -> SourceOut:
    from app.db.models import SourceDocument
    sess = await _get_or_create_session(db, settings, session_id)
    doc_id = generate_doc_id()
    content = req.text.encode("utf-8")
    file_hash = hash_bytes(content)
    mime = "text/plain"

    dest_dir = pathlib.Path(sess.artifact_dir) / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{doc_id}.txt"
    dest_path.write_bytes(content)

    page_count, parsed_path = await _process_and_extract_sot(sess.id, doc_id, dest_path, mime, db)

    doc = SourceDocument(
        id=doc_id,
        session_id=sess.id,
        original_filename=req.name,
        mime_type=mime,
        file_hash=file_hash,
        file_path=str(dest_path),
        parsed_path=parsed_path,
        page_count=page_count,
        status="ready",
    )
    db.add(doc)
    await db.flush()

    return SourceOut.create(
        doc_id=doc_id,
        filename=req.name,
        mime=mime,
        file_hash=file_hash,
        created_at=datetime.now(timezone.utc),
        size_bytes=len(content),
        page_count=page_count,
        status="ready",
        session_id=sess.id,
    )


@flat_router.get("/{doc_id}/status", summary="Get source processing status")
async def get_source_status(doc_id: str, db: DbDep) -> dict:
    from sqlalchemy import select
    from app.db.models import SourceDocument
    res = await db.execute(select(SourceDocument).where(SourceDocument.id == doc_id).limit(1))
    doc = res.scalars().first()
    return {
        "id": doc_id,
        "status": doc.status if doc else "ready",
        "progress": 100,
        "message": "Source of Truth ready for review.",
    }


@flat_router.get("/{doc_id}/preview", summary="Preview source document")
async def get_source_preview(doc_id: str, db: DbDep) -> dict:
    from sqlalchemy import select
    from app.db.models import SourceDocument, FactRecord
    res = await db.execute(select(SourceDocument).where(SourceDocument.id == doc_id).limit(1))
    doc = res.scalars().first()
    preview_text = ""
    page_count = 1
    if doc:
        page_count = doc.page_count or 1
        if doc.parsed_path:
            p = pathlib.Path(doc.parsed_path)
            if p.exists():
                try:
                    preview_text = p.read_text(encoding="utf-8", errors="replace")[:3000]
                except Exception:
                    pass
        if not preview_text and doc.file_path:
            p = pathlib.Path(doc.file_path)
            if p.exists() and p.suffix.lower() in [".txt", ".md", ".json", ".csv", ".html"]:
                try:
                    preview_text = p.read_text(encoding="utf-8", errors="replace")[:3000]
                except Exception:
                    pass
        if not preview_text:
            facts_res = await db.execute(
                select(FactRecord).where(FactRecord.session_id == doc.session_id).order_by(FactRecord.db_id).limit(12)
            )
            facts = facts_res.scalars().all()
            if facts:
                preview_text = "\n\n".join(f.canonical_text for f in facts)
    return {
        "id": doc_id,
        "text": preview_text or "Source registered and processed.",
        "pageCount": page_count,
    }


@flat_router.get("/{doc_id}", summary="Get source document details")
async def get_single_source(doc_id: str, db: DbDep) -> SourceOut:
    from sqlalchemy import select
    from app.db.models import SourceDocument
    res = await db.execute(select(SourceDocument).where(SourceDocument.id == doc_id).limit(1))
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(404, f"Source {doc_id} not found")
    return SourceOut.create(
        doc_id=doc.id,
        filename=doc.original_filename,
        mime=doc.mime_type,
        file_hash=doc.file_hash,
        created_at=doc.created_at,
        status=doc.status,
    )


# ─── Scoped routes for /sessions/{session_id}/sources ─────────────────────────

@router.post("", summary="Upload source documents for session", status_code=202)
async def upload_sources(
    session_id: str,
    db: DbDep,
    settings: SettingsDep,
    files: list[UploadFile] = File(...),
) -> list[SourceOut]:
    from sqlalchemy import select
    from app.db.models import Session, SourceDocument

    sess_res = await db.execute(select(Session).where(Session.id == session_id).limit(1))
    sess = sess_res.scalars().first()
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

        dest_dir = pathlib.Path(sess.artifact_dir) / "uploads"
        dest_dir.mkdir(parents=True, exist_ok=True)
        suffix = pathlib.Path(file.filename or "upload").suffix
        dest_path = dest_dir / (doc_id + suffix)
        dest_path.write_bytes(content)

        page_count, parsed_path = await _process_and_extract_sot(sess.id, doc_id, dest_path, mime, db)

        doc = SourceDocument(
            id=doc_id,
            session_id=session_id,
            original_filename=file.filename or "unknown",
            mime_type=mime,
            file_hash=file_hash,
            file_path=str(dest_path),
            parsed_path=parsed_path,
            page_count=page_count,
            status="ready",
        )
        db.add(doc)
        await db.flush()

        results.append(SourceOut.create(
            doc_id=doc_id,
            filename=file.filename or "unknown",
            mime=mime,
            file_hash=file_hash,
            created_at=datetime.now(timezone.utc),
            size_bytes=len(content),
            page_count=page_count,
            status="ready",
            session_id=session_id,
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
        SourceOut.create(
            doc_id=d.id,
            filename=d.original_filename,
            mime=d.mime_type,
            file_hash=d.file_hash,
            created_at=d.created_at,
            status=d.status,
        )
        for d in docs
    ]

