"""
ingest/quality.py — Per-chunk quality scoring.
Aggregates OCR confidence, ASR log-probability, and structural signals
into a quality score that feeds sot/confidence.py.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ChunkQuality:
    chunk_id: str
    ocr_confidence: float | None = None   # 0-1; None for native text
    asr_log_prob: float | None = None     # log-prob; None for non-audio
    is_table: bool = False
    is_caption: bool = False
    is_header: bool = False
    structural_bonus: float = 0.0

    @property
    def source_quality(self) -> float:
        """Normalised 0-1 quality signal used by confidence.py."""
        if self.ocr_confidence is not None:
            base = self.ocr_confidence
        elif self.asr_log_prob is not None:
            # log-prob typically -3..0; map to 0..1
            base = max(0.0, min(1.0, 1.0 + self.asr_log_prob / 3.0))
        else:
            base = 1.0   # native digital text
        return min(1.0, base + self.structural_bonus)


def score_chunks(
    chunk_ids: list[str],
    ocr_confidences: dict[str, float] | None = None,
    asr_log_probs: dict[str, float] | None = None,
) -> dict[str, ChunkQuality]:
    ocr_confidences = ocr_confidences or {}
    asr_log_probs = asr_log_probs or {}
    return {
        cid: ChunkQuality(
            chunk_id=cid,
            ocr_confidence=ocr_confidences.get(cid),
            asr_log_prob=asr_log_probs.get(cid),
        )
        for cid in chunk_ids
    }
