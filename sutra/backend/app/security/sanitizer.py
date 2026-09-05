"""
security/sanitizer.py — Indirect prompt-injection defence.
Every ingested text span runs through here before it can reach any prompt.
Returns (clean_text, detections) where detections carry span + pattern class.
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field


_IMPERATIVE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"ignore (previous|all|the above|prior) instructions?",
        r"you are now",
        r"disregard (previous|all|prior)",
        r"new (instruction|directive|order)s?[:\s]",
        r"system[:\s]*(prompt|override|directive|instruction)",
        r"override (all |your )?(safety|guidelines|constraints|rules)",
        r"</?(system|user|assistant|human)>",
        r"\[INST\]",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
    ]
]

_INVISIBLE_CHARS = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]"
)


@dataclass
class Detection:
    span: str
    pattern_class: str
    char_start: int
    char_end: int
    page: int | None = None
    locator: str = ""
    risk_score: float = 0.9


@dataclass
class SanitizeResult:
    clean_text: str
    detections: list[Detection] = field(default_factory=list)
    was_modified: bool = False


def sanitize(text: str, page: int | None = None,
             locator: str = "") -> SanitizeResult:
    detections: list[Detection] = []
    clean = text

    # 1. Strip invisible / bidirectional control chars
    stripped = _INVISIBLE_CHARS.sub("", clean)
    if stripped != clean:
        detections.append(Detection(
            span=clean[:200],
            pattern_class="invisible_chars",
            char_start=0,
            char_end=len(clean),
            page=page,
            locator=locator,
            risk_score=0.85,
        ))
        clean = stripped

    # 2. Detect imperative override patterns
    for pat in _IMPERATIVE_PATTERNS:
        for m in pat.finditer(clean):
            detections.append(Detection(
                span=m.group(),
                pattern_class="imperative_override",
                char_start=m.start(),
                char_end=m.end(),
                page=page,
                locator=locator,
                risk_score=0.95,
            ))
            # Neutralize: wrap in square brackets to signal inert content
            clean = clean[:m.start()] + "[NEUTRALIZED:" + m.group() + "]" + clean[m.end():]

    return SanitizeResult(
        clean_text=clean,
        detections=detections,
        was_modified=bool(detections),
    )
