"""
ingest/docling_adapter.py — Docling integration stub.
Wraps DocumentConverter and maps DoclingDocument -> InternalDoc.
bbox provenance MUST be preserved here — without it the provenance panel breaks.

In Phase 1 this is a stub that uses plain text reading.
Replace the _convert_* methods with real Docling calls.
"""
from __future__ import annotations
import pathlib
from dataclasses import dataclass, field
from app.core.schemas import Provenance
from app.core.ids import generate_chunk_id
from app.ingest.chunker import Chunk, chunk_text
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class InternalDoc:
    doc_id: str
    source_path: pathlib.Path
    pipeline: str
    chunks: list[Chunk] = field(default_factory=list)
    page_count: int = 0
    ocr_applied: bool = False
    metadata: dict = field(default_factory=dict)


def convert(
    doc_id: str,
    file_path: pathlib.Path,
    pipeline: str,
    mime_type: str = "",
) -> InternalDoc:
    """
    Convert a source file to an InternalDoc with chunked, provenance-linked content.
    Stub: reads plain text and chunks it. Replace with Docling in Phase 1.
    """
    logger.info("Converting document (stub)", doc_id=doc_id,
                pipeline=pipeline, path=str(file_path))

    try:
        raw = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Could not read file as text", error=str(exc))
        raw = ""

    chunks = chunk_text(doc_id=doc_id, text=raw, page=1, locator="p1")

    return InternalDoc(
        doc_id=doc_id,
        source_path=file_path,
        pipeline=pipeline,
        chunks=chunks,
        page_count=1,
        ocr_applied=pipeline == "docling_ocr",
        metadata={"mime_type": mime_type, "stub": True},
    )
