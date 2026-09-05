"""
ingest/router.py — Maps MIME type / extension to the right ingestion pipeline.
Handles multi-file uploads; keeps per-file doc_ids so provenance is attributable.
"""
from __future__ import annotations
import pathlib
from dataclasses import dataclass, field

SUPPORTED_MIME_TYPES: dict[str, str] = {
    "application/pdf":                    "docling",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docling",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "docling",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "docling",
    "text/html":                          "docling",
    "image/png":                          "docling_ocr",
    "image/jpeg":                         "docling_ocr",
    "image/tiff":                         "docling_ocr",
    "audio/mpeg":                         "asr",
    "audio/wav":                          "asr",
    "video/mp4":                          "video",
    "video/quicktime":                    "video",
    "text/plain":                         "text",
}

EXTENSION_FALLBACKS: dict[str, str] = {
    ".pdf": "docling", ".docx": "docling", ".pptx": "docling",
    ".xlsx": "docling", ".html": "docling", ".htm": "docling",
    ".png": "docling_ocr", ".jpg": "docling_ocr", ".jpeg": "docling_ocr",
    ".tiff": "docling_ocr", ".tif": "docling_ocr",
    ".mp3": "asr", ".wav": "asr", ".m4a": "asr",
    ".mp4": "video", ".mov": "video",
    ".txt": "text", ".md": "text",
}


@dataclass
class IngestRoute:
    doc_id: str
    file_path: pathlib.Path
    pipeline: str
    mime_type: str


def route(
    doc_id: str,
    file_path: pathlib.Path,
    mime_type: str | None = None,
) -> IngestRoute:
    """Determine which pipeline handles this file."""
    from app.core.errors import UnsupportedSourceTypeError

    detected = mime_type or ""
    pipeline = SUPPORTED_MIME_TYPES.get(detected)

    if not pipeline:
        ext = file_path.suffix.lower()
        pipeline = EXTENSION_FALLBACKS.get(ext)

    if not pipeline:
        raise UnsupportedSourceTypeError(
            f"Unsupported file type: mime={detected!r}, ext={file_path.suffix!r}"
        )

    return IngestRoute(
        doc_id=doc_id,
        file_path=file_path,
        pipeline=pipeline,
        mime_type=detected or "application/octet-stream",
    )
