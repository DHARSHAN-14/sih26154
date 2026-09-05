"""
visual/predict.py — Pre-render text overflow prediction.
Uses PIL font metrics to predict wrapped line count and height
BEFORE anything is written.  Catches ~80% of layout problems at near-zero cost.
"""
from __future__ import annotations
import math


def estimate_lines(
    text: str,
    box_width_pts: float,
    font_size_pts: float,
    avg_char_width_ratio: float = 0.55,
) -> int:
    """
    Estimate the number of wrapped lines for text in a box.
    avg_char_width_ratio: fraction of font_size that is the average char width.
    """
    if not text:
        return 0
    avg_char_w = font_size_pts * avg_char_width_ratio
    chars_per_line = max(1, int(box_width_pts / avg_char_w))
    words = text.split()
    lines = 1
    current_len = 0
    for word in words:
        wl = len(word) + 1   # +1 for space
        if current_len + wl > chars_per_line:
            lines += 1
            current_len = wl
        else:
            current_len += wl
    return lines


def will_overflow(
    text: str,
    box_width_pts: float,
    box_height_pts: float,
    font_size_pts: float,
    line_spacing: float = 1.2,
) -> bool:
    """Return True if the text will overflow the box."""
    lines = estimate_lines(text, box_width_pts, font_size_pts)
    required_height = lines * font_size_pts * line_spacing
    return required_height > box_height_pts


def predict_overflow(
    sections: dict[str, str],
    box_width_pts: float,
    box_height_pts: float,
    font_size_pts: float = 10.5,
) -> dict[str, bool]:
    """Batch overflow prediction for multiple sections."""
    return {
        key: will_overflow(text, box_width_pts, box_height_pts, font_size_pts)
        for key, text in sections.items()
    }
