"""
visual/rules.py — All visual thresholds in one place.
A judge asking 'why 18pt?' gets a pointer to this file, not a shrug.
Defaults; layout contracts may override per output type.
"""
from __future__ import annotations

MIN_FONT_SIZE_PT: float = 8.0
MAX_FONT_SIZE_PT: float = 48.0
MAX_BULLETS_PER_SLIDE: int = 7
MAX_LINES_PER_BULLET: int = 3
MARGIN_TOLERANCE_PTS: float = 5.0
MIN_CONTRAST_RATIO: float = 4.5    # WCAG AA
MAX_SLIDES_DEVIATION: int = 1      # allowed deviation from contract max
MAX_PAGES_DEVIATION: int = 0
CHAR_WIDTH_RATIO: float = 0.55
LINE_SPACING: float = 1.2
