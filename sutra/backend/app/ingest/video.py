"""
ingest/video.py — Video ingestion: audio track extraction + keyframe OCR.
Pipeline: ffmpeg -> audio track + keyframes at scene cuts -> asr + docling_ocr.
Stub: returns dummy result; replace ffmpeg calls with real subprocess.
"""
from __future__ import annotations
import pathlib
from dataclasses import dataclass, field
from app.core.logging import get_logger
from app.ingest.chunker import Chunk

logger = get_logger(__name__)


@dataclass
class VideoResult:
    doc_id: str
    video_path: pathlib.Path
    audio_path: pathlib.Path | None = None
    keyframe_paths: list[pathlib.Path] = field(default_factory=list)
    duration_sec: float = 0.0
    fps: float = 25.0
    chunks: list[Chunk] = field(default_factory=list)


def extract(
    doc_id: str,
    video_path: pathlib.Path,
    artifact_dir: pathlib.Path,
    scene_threshold: float = 0.4,
) -> VideoResult:
    """
    Extract audio track and keyframes from a video file.
    Stub: returns empty result.
    Replace with:
        import subprocess
        audio_path = artifact_dir / f"{doc_id}.wav"
        subprocess.run(["ffmpeg", "-i", str(video_path),
                        "-vn", "-ar", "16000", "-ac", "1", str(audio_path)])
        # Then extract keyframes with ffmpeg scene filter
    """
    logger.info("Video extraction (stub)", doc_id=doc_id, path=str(video_path))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return VideoResult(
        doc_id=doc_id,
        video_path=video_path,
        audio_path=None,
        keyframe_paths=[],
        duration_sec=0.0,
    )
