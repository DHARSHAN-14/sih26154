"""
visual/autofix.py — Deterministic layout repairs before any LLM call.
Step font down, split bullet, push to continuation slide, tighten spacing.
Each fix is re-validated. Only if deterministic fixes fail does content
go back to validation/repair.py for a text rewrite.
"""
from __future__ import annotations
from app.visual.rules import MIN_FONT_SIZE_PT
from app.visual.predict import will_overflow


def step_down_font(
    text: str,
    box_width_pts: float,
    box_height_pts: float,
    start_pt: float,
    step: float = 1.0,
) -> tuple[float, bool]:
    """
    Reduce font size by step until text fits or MIN_FONT_SIZE_PT is reached.
    Returns (final_font_size, did_fit).
    """
    font_pt = start_pt
    while font_pt >= MIN_FONT_SIZE_PT:
        if not will_overflow(text, box_width_pts, box_height_pts, font_pt):
            return font_pt, True
        font_pt -= step
    return MIN_FONT_SIZE_PT, False


def split_bullet(text: str, max_chars: int = 120) -> list[str]:
    """Split a long bullet into sub-bullets at sentence boundaries."""
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    bullets: list[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = (current + " " + sent).strip()
        else:
            if current:
                bullets.append(current)
            current = sent
    if current:
        bullets.append(current)
    return bullets or [text]
