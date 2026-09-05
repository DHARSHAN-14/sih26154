from __future__ import annotations
import pytest
from app.visual.predict import estimate_lines, will_overflow, predict_overflow
from app.visual.rules import (
    MAX_LINES_PER_BULLET,
    MAX_BULLETS_PER_SLIDE,
    MAX_SLIDES_DEVIATION,
)
from app.visual.autofix import step_down_font, split_bullet


class TestVisualPptx:
    def test_line_estimation(self):
        short_text = "Short bullet point."
        lines = estimate_lines(short_text, 400.0, 18.0)
        assert lines == 1

        long_text = (
            "This is an exceptionally lengthy bullet point containing a comprehensive "
            "description of cyber security architecture and critical defense countermeasures "
            "designed to exceed standard line boundaries."
        )
        lines_long = estimate_lines(long_text, 400.0, 18.0)
        assert lines_long >= 2

    def test_will_overflow_detection(self):
        # 10 lines of 18pt font in a 100pt box -> overflow
        text = "Line entry. " * 40
        overflow = will_overflow(text, 300.0, 100.0, 18.0)
        assert overflow is True

    def test_font_step_down(self):
        long_text = "Detailed incident reporting. " * 15
        final_font, did_fit = step_down_font(
            long_text, box_width_pts=400.0, box_height_pts=150.0, start_pt=24.0, step=1.0
        )
        assert final_font <= 24.0
        assert final_font >= 8.0

    def test_split_bullet_point(self):
        long_bullet = (
            "Primary defensive capability was deployed on 2026-01-10. "
            "Secondary backup redundancy was activated on 2026-01-12."
        )
        parts = split_bullet(long_bullet, max_chars=60)
        assert len(parts) >= 2
