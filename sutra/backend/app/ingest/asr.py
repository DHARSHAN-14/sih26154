"""
ingest/asr.py — Whisper-based ASR adapter.
Uses faster-whisper (large-v3-turbo, int8) for timestamps.
Timestamps become provenance locators ("t00:14:22") for the SoT.
Stub: reads no audio; replace _transcribe with real faster-whisper call.
"""
from __future__ import annotations
import pathlib
from dataclasses import dataclass, field
from app.core.schemas import Provenance
from app.core.ids import generate_chunk_id
from app.ingest.chunker import Chunk
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ASRSegment:
    start: float        # seconds
    end: float          # seconds
    text: str
    avg_logprob: float = -0.5
    no_speech_prob: float = 0.05


@dataclass
class ASRResult:
    doc_id: str
    audio_path: pathlib.Path
    segments: list[ASRSegment] = field(default_factory=list)
    language: str = "en"
    duration_sec: float = 0.0

    @property
    def full_text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)


def _format_ts(sec: float) -> str:
    """Convert seconds to HH:MM:SS locator."""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"t{h:02d}:{m:02d}:{s:02d}"


def transcribe(
    doc_id: str,
    audio_path: pathlib.Path,
    language: str = "en",
) -> ASRResult:
    """
    Transcribe audio file to timestamped segments.
    Stub: returns one dummy segment.
    Replace with:
        from faster_whisper import WhisperModel
        model = WhisperModel("large-v3-turbo", device="cuda", compute_type="int8")
        segments, info = model.transcribe(str(audio_path), language=language)
    """
    logger.info("ASR transcription (stub)", doc_id=doc_id, path=str(audio_path))
    return ASRResult(
        doc_id=doc_id,
        audio_path=audio_path,
        segments=[
            ASRSegment(start=0.0, end=5.0,
                       text="[stub: ASR not configured — install faster-whisper]")
        ],
        language=language,
        duration_sec=5.0,
    )


def segments_to_chunks(result: ASRResult) -> list[Chunk]:
    """Convert ASR segments to provenance-linked Chunks."""
    chunks = []
    for seg in result.segments:
        cid = generate_chunk_id()
        locator = _format_ts(seg.start)
        prov = Provenance(
            doc_id=result.doc_id,
            locator=locator,
            chunk_id=cid,
            snippet=seg.text[:300],
        )
        chunks.append(Chunk(
            chunk_id=cid,
            doc_id=result.doc_id,
            text=seg.text,
            provenance=[prov],
        ))
    return chunks
