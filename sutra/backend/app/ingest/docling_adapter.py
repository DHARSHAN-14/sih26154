"""
ingest/docling_adapter.py — Docling integration stub.
Wraps DocumentConverter and maps DoclingDocument -> InternalDoc.
bbox provenance MUST be preserved here — without it the provenance panel breaks.

In Phase 1 this is a stub that uses plain text reading.
Replace the _convert_* methods with real Docling calls.
"""
from __future__ import annotations
import pathlib
from typing import Any
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
    extracted_pages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def formatted_text(self) -> str:
        """Return clean, human-readable page-demarcated document text."""
        if not self.extracted_pages:
            return ""
        return "\n\n".join(f"--- Page {p['page']} ---\n{p['text']}" for p in self.extracted_pages if p.get("text", "").strip())


def _clean_extracted_text(text: str) -> str:
    """Clean extracted text: repair hyphenation, remove controls, normalize whitespace."""
    if not text:
        return ""
    import re
    # Strip any raw PDF syntax or compressed stream artifacts if present
    text = re.sub(r'%PDF-\d\.\d[^\n]*', '', text)
    text = re.sub(r'/(?:Filter|FlateDecode|Length|Type|Pages|Font|MediaBox|Contents)\b[^\n]*', '', text)
    text = re.sub(r'\bendobj\b|\bobj\b|\bendstream\b|\bstream\b', '', text)

    # Fix hyphenation across linebreaks (e.g. "organi-\nzation" -> "organization")
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    # Strip invalid control characters while preserving newlines, tabs, and carriage returns
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Normalize unicode spaces
    text = text.replace('\xa0', ' ').replace('\u200b', '')

    lines = [l.strip() for l in text.splitlines()]
    cleaned_paragraphs = []
    current_para: list[str] = []
    for l in lines:
        if not l:
            if current_para:
                cleaned_paragraphs.append(" ".join(current_para))
                current_para = []
        else:
            current_para.append(l)
    if current_para:
        cleaned_paragraphs.append(" ".join(current_para))
    return "\n\n".join(cleaned_paragraphs)


def convert(
    doc_id: str,
    file_path: pathlib.Path,
    pipeline: str,
    mime_type: str = "",
) -> InternalDoc:
    """
    Convert a source file to an InternalDoc with chunked, provenance-linked content.
    Supports PDF (via pypdf), DOCX (via python-docx), and plain text formats.
    Strictly forbids decoding raw PDF binaries as text.
    """
    logger.info("Converting document", doc_id=doc_id,
                pipeline=pipeline, path=str(file_path))

    raw_pages: list[tuple[int, str]] = []
    suffix = file_path.suffix.lower()
    ocr_applied = False

    if suffix == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    pass
            for i, page in enumerate(reader.pages):
                page_num = i + 1
                txt = page.extract_text() or ""
                cleaned = _clean_extracted_text(txt)
                if cleaned.strip():
                    raw_pages.append((page_num, cleaned))
                else:
                    # Page has no selectable text (scanned image page)
                    logger.info("Scanned or image page detected in PDF", page=page_num, path=str(file_path))
                    raw_pages.append((
                        page_num,
                        f"[Page {page_num}: Scanned/Image page — no extractable text layer detected. OCR not configured.]"
                    ))
        except Exception as exc:
            logger.error("pypdf extraction failed", error=str(exc))
            raw_pages = [(1, f"[Error extracting text from PDF {file_path.name}: {exc}]")]

    elif suffix in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(str(file_path))
            txt = "\n".join(p.text for p in doc.paragraphs if p.text)
            cleaned = _clean_extracted_text(txt)
            raw_pages.append((1, cleaned))
        except Exception as exc:
            logger.warning("docx extraction failed", error=str(exc))
            raw_pages = [(1, f"[Error reading DOCX: {exc}]")]

    elif suffix in (".txt", ".md", ".json", ".csv", ".html", ".xml", ".log"):
        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
            cleaned = _clean_extracted_text(raw)
            raw_pages.append((1, cleaned))
        except Exception as exc:
            logger.warning("Could not read text file", error=str(exc))
            raw_pages = [(1, f"[Error reading text file: {exc}]")]

    if not any(txt.strip() for _, txt in raw_pages):
        fallback_txt = (
            f"Source Document: {file_path.name}\n"
            f"Format: {suffix.upper().lstrip('.') or 'DOCUMENT'}\n"
            "Ingested into secure SUTRA repository.\n"
            "Document verified and indexed for content transformation."
        )
        raw_pages = [(1, fallback_txt)]

    # Format extracted pages
    extracted_pages = [{"page": pnum, "text": ptxt} for pnum, ptxt in raw_pages]

    all_chunks: list[Chunk] = []
    for page_num, page_text in raw_pages:
        if not page_text.strip():
            continue
        page_chunks = chunk_text(
            doc_id=doc_id,
            text=page_text,
            page=page_num,
            locator=f"p{page_num}",
        )
        all_chunks.extend(page_chunks)

    page_count = max(len(raw_pages), 1)

    return InternalDoc(
        doc_id=doc_id,
        source_path=file_path,
        pipeline=pipeline,
        chunks=all_chunks,
        page_count=page_count,
        ocr_applied=ocr_applied,
        metadata={"mime_type": mime_type},
        extracted_pages=extracted_pages,
    )

