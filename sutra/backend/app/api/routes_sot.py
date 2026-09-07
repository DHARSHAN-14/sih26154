from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.deps import DbDep, SettingsDep
from app.core.errors import SessionNotFoundError, SoTAlreadyLockedError
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions/{session_id}/sot", tags=["Source of Truth"])
flat_router = APIRouter(prefix="/sot", tags=["Source of Truth"])


def _classify_entity(text: str) -> str:
    """Classify an entity into one of the frontend EntityTypes."""
    lower = text.lower().strip()
    if lower.startswith("cve-") or "cve-" in lower:
        return "technical"
    if any(w in lower for w in ["cyclone", "apt", "lazarus", "actor", "threat", "ntro", "cert", "drdo", "isro", "ministry", "agency", "organization", "organisation", "department", "board"]):
        return "organization"
    if any(w in lower for w in ["gateway", "controller", "server", "system", "payload", "firmware", "vulnerability", "udp", "tcp", "ip", "hash", "ethernet", "port", "protocol", "malware", "patch"]):
        return "technical"
    if any(w in lower for w in ["grid", "substation", "region", "city", "state", "delhi", "mumbai", "india", "north", "west", "east", "south"]):
        return "location"
    if any(c.isdigit() for c in text):
        if any(w in lower for w in ["year", "month", "day", "202", "199", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]):
            return "date"
        return "numeric"
    if any(w in lower for w in ["dr.", "mr.", "mrs.", "shri", "officer", "director", "minister", "general"]):
        return "person"
    return "claim"


async def _build_full_sot_dict(sot, db) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import FactRecord, SourceDocument

    # Fetch facts
    facts_res = await db.execute(
        select(FactRecord).where(FactRecord.sot_id == sot.id)
    )
    facts = facts_res.scalars().all()

    # Fetch source document
    doc_res = await db.execute(
        select(SourceDocument).where(SourceDocument.session_id == sot.session_id).order_by(SourceDocument.created_at.desc()).limit(1)
    )
    doc = doc_res.scalars().first()

    from app.kg.resolver import build_resolved_kg_from_facts

    entities, relations = build_resolved_kg_from_facts(facts)

    # Summary
    if facts:
        top_sentences = [f.canonical_text for f in facts[:4]]
        summary = " ".join(top_sentences)
    else:
        summary = "Source document processed. Knowledge graph ready."

    # Raw text & page extraction (Strictly clean text, never raw PDF bytes)
    raw_text = ""
    pages_list: list[dict[str, Any]] = []

    if doc:
        import pathlib
        if doc.parsed_path and pathlib.Path(doc.parsed_path).exists():
            try:
                raw_text = pathlib.Path(doc.parsed_path).read_text(encoding="utf-8", errors="replace")
                json_p = pathlib.Path(doc.parsed_path).parent / f"{doc.id}_parsed.json"
                if json_p.exists():
                    pages_list = json.loads(json_p.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Could not read parsed text file", error=str(exc))

        if not raw_text and doc.file_path:
            p = pathlib.Path(doc.file_path)
            # Only read text files directly; NEVER decode binary PDFs or DOCXs as text
            if p.exists() and p.suffix.lower() in [".txt", ".md", ".json", ".csv", ".html", ".xml", ".log"]:
                try:
                    raw_text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

    # Fallback: Assemble clean readable text from facts grouped by source page
    if not raw_text and facts:
        page_groups: dict[int, list[str]] = {}
        for f in facts:
            p = 1
            if f.provenance_json:
                try:
                    provs = json.loads(f.provenance_json)
                    if provs and isinstance(provs, list):
                        p = provs[0].get("page", 1)
                except Exception:
                    p = 1
            page_groups.setdefault(p, []).append(f.canonical_text)

        parts = []
        for p_num in sorted(page_groups.keys()):
            p_text = "\n".join(page_groups[p_num])
            parts.append(f"--- Page {p_num} ---\n{p_text}")
            pages_list.append({"page": p_num, "text": p_text})
        raw_text = "\n\n".join(parts)

    if not pages_list and raw_text:
        pages_list = [{"page": 1, "text": raw_text}]

    words = len(raw_text.split()) if raw_text else len(summary.split())

    status = "locked" if sot.is_locked else "verified"
    created_str = sot.created_at.isoformat() if sot.created_at else datetime.now(timezone.utc).isoformat()
    locked_str = sot.locked_at.isoformat() if sot.locked_at else None

    return {
        "id": sot.id,
        "sot_id": sot.id,
        "sourceId": doc.id if doc else "src-001",
        "status": status,
        "version": sot.version,
        "fact_count": sot.fact_count,
        "is_locked": sot.is_locked,
        "lock_hash": sot.lock_hash,
        "lockHash": sot.lock_hash,
        "hash": sot.lock_hash,
        "createdAt": created_str,
        "lockedAt": locked_str,
        "lockedBy": "operator" if sot.is_locked else None,
        "entities": entities,
        "relations": relations,
        "rawText": raw_text,
        "extractedText": raw_text,
        "pages": pages_list,
        "summary": summary,
        "language": "en",
        "wordCount": max(words, 1),
    }


# ─── Scoped routes for /sessions/{session_id}/sot ─────────────────────────────

@router.get("", summary="Get current Source of Truth for session")
async def get_sot(session_id: str, db: DbDep) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import SotVersion
    result = await db.execute(
        select(SotVersion)
        .where(SotVersion.session_id == session_id)
        .order_by(SotVersion.version.desc())
        .limit(1)
    )
    sot = result.scalars().first()
    if not sot:
        return {
            "id": "sot-empty",
            "sot_id": None,
            "sourceId": "none",
            "status": "draft",
            "version": 0,
            "fact_count": 0,
            "is_locked": False,
            "lock_hash": None,
            "lockHash": None,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "entities": [],
            "relations": [],
            "rawText": "",
            "summary": "No Source of Truth built yet for this session.",
            "language": "en",
            "wordCount": 0,
        }
    return await _build_full_sot_dict(sot, db)


@router.post("/lock", summary="Lock the Source of Truth")
async def lock_sot(session_id: str, db: DbDep) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import SotVersion, FactRecord

    result = await db.execute(
        select(SotVersion)
        .where(SotVersion.session_id == session_id)
        .order_by(SotVersion.version.desc())
        .limit(1)
    )
    sot = result.scalars().first()
    if not sot:
        raise SessionNotFoundError(session_id)
    if sot.is_locked:
        return await _build_full_sot_dict(sot, db)

    # Compute hash over fact canonical texts
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

    logger.info("SoT locked", session_id=session_id, lock_hash=lock_hash[:16] + "...")
    return await _build_full_sot_dict(sot, db)


# ─── Flat routes for /sot ──────────────────────────────────────────────────────

@flat_router.get("/{target_id}", summary="Get Source of Truth by doc_id, sot_id or session_id")
async def flat_get_sot(target_id: str, db: DbDep) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import SotVersion, SourceDocument

    # Try matching SotVersion.id
    res = await db.execute(select(SotVersion).where(SotVersion.id == target_id).limit(1))
    sot = res.scalars().first()

    # Try matching by SourceDocument.id
    if not sot:
        doc_res = await db.execute(select(SourceDocument).where(SourceDocument.id == target_id).limit(1))
        doc = doc_res.scalars().first()
        if doc:
            res = await db.execute(
                select(SotVersion).where(SotVersion.session_id == doc.session_id).order_by(SotVersion.version.desc()).limit(1)
            )
            sot = res.scalars().first()

    # Try matching by session_id
    if not sot:
        res = await db.execute(
            select(SotVersion).where(SotVersion.session_id == target_id).order_by(SotVersion.version.desc()).limit(1)
        )
        sot = res.scalars().first()

    # Fallback to latest
    if not sot:
        res = await db.execute(select(SotVersion).order_by(SotVersion.version.desc()).limit(1))
        sot = res.scalars().first()

    if not sot:
        return {
            "id": target_id,
            "sourceId": target_id,
            "status": "draft",
            "version": 1,
            "fact_count": 0,
            "is_locked": False,
            "lock_hash": None,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "entities": [],
            "relations": [],
            "rawText": "",
            "summary": "Source of Truth ready.",
            "language": "en",
            "wordCount": 0,
        }

    return await _build_full_sot_dict(sot, db)


@flat_router.post("/{target_id}/lock", summary="Lock Source of Truth (flat endpoint)")
async def flat_lock_sot(target_id: str, db: DbDep) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import SotVersion, FactRecord, SourceDocument

    res = await db.execute(select(SotVersion).where(SotVersion.id == target_id).limit(1))
    sot = res.scalars().first()

    if not sot:
        doc_res = await db.execute(select(SourceDocument).where(SourceDocument.id == target_id).limit(1))
        doc = doc_res.scalars().first()
        if doc:
            res = await db.execute(
                select(SotVersion).where(SotVersion.session_id == doc.session_id).order_by(SotVersion.version.desc()).limit(1)
            )
            sot = res.scalars().first()

    if not sot:
        res = await db.execute(
            select(SotVersion).where(SotVersion.session_id == target_id).order_by(SotVersion.version.desc()).limit(1)
        )
        sot = res.scalars().first()

    if not sot:
        raise HTTPException(404, f"SoT not found for target {target_id}")

    if sot.is_locked:
        return await _build_full_sot_dict(sot, db)

    facts_res = await db.execute(select(FactRecord).where(FactRecord.sot_id == sot.id))
    facts = facts_res.scalars().all()
    entries = sorted(f.id + "|" + f.canonical_text for f in facts)
    lock_hash = hashlib.sha256(json.dumps(entries).encode()).hexdigest()

    sot.lock_hash = lock_hash
    sot.is_locked = True
    sot.locked_at = datetime.now(timezone.utc)
    await db.flush()

    return await _build_full_sot_dict(sot, db)


@flat_router.post("/{target_id}/unlock", summary="Unlock Source of Truth")
async def flat_unlock_sot(target_id: str, db: DbDep) -> dict[str, Any]:
    from sqlalchemy import select
    from app.db.models import SotVersion
    res = await db.execute(select(SotVersion).where(SotVersion.id == target_id).limit(1))
    sot = res.scalars().first()
    if sot:
        sot.is_locked = False
        sot.lock_hash = None
        sot.locked_at = None
        await db.flush()
        return await _build_full_sot_dict(sot, db)
    return {"status": "unlocked", "id": target_id}

