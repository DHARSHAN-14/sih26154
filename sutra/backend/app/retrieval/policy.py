"""
retrieval/policy.py — Route A / Route B decision gate.
Small source -> Route A (whole-source, no retrieval, higher recall).
Large source -> Route B (chunk -> embed -> hybrid search -> rerank).
Log and surface in UI so the architectural decision is visible.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Route(str, Enum):
    A = "A"   # full-context
    B = "B"   # retrieval


@dataclass
class RetrievalDecision:
    route: Route
    token_count: int
    threshold: int
    reason: str
    file_count: int = 1
    media_duration_sec: float = 0.0


def decide(
    token_count: int,
    threshold: int,
    file_count: int = 1,
    media_duration_sec: float = 0.0,
) -> RetrievalDecision:
    """
    Return Route A when the source fits in context; Route B otherwise.
    Also triggers Route B for multi-file uploads or long audio/video.
    """
    if file_count > 1:
        return RetrievalDecision(
            route=Route.B,
            token_count=token_count,
            threshold=threshold,
            reason=f"Multi-file upload ({file_count} files) — Route B engaged",
            file_count=file_count,
            media_duration_sec=media_duration_sec,
        )
    if media_duration_sec > 1200:   # 20 min
        return RetrievalDecision(
            route=Route.B,
            token_count=token_count,
            threshold=threshold,
            reason=f"Audio/video > 20 min ({media_duration_sec:.0f}s) — Route B engaged",
            file_count=file_count,
            media_duration_sec=media_duration_sec,
        )
    if token_count > threshold:
        return RetrievalDecision(
            route=Route.B,
            token_count=token_count,
            threshold=threshold,
            reason=(f"Source too large for context "
                    f"({token_count} tokens > threshold {threshold}) — Route B engaged"),
            file_count=file_count,
        )
    return RetrievalDecision(
        route=Route.A,
        token_count=token_count,
        threshold=threshold,
        reason=(f"Route A — {token_count} tokens fits in context; "
                f"retrieval skipped (higher recall)"),
        file_count=file_count,
    )
