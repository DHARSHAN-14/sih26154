from __future__ import annotations
import pytest
from app.templates.registry import load_all, get, all_ids

EXPECTED_FORMATS = [
    "advisory", "executive_summary", "presentation",
    "linkedin", "twitter_x", "infographic", "video_package",
]


class TestTemplateContracts:
    @classmethod
    def setup_class(cls):
        load_all()

    def test_all_formats_loaded(self):
        loaded = all_ids()
        for fmt in EXPECTED_FORMATS:
            assert fmt in loaded, f"Missing template: {fmt}"

    def test_each_has_content_contract(self):
        for fmt in EXPECTED_FORMATS:
            t = get(fmt)
            assert t.content_contract.sections, f"{fmt} has no sections"

    def test_each_has_layout_contract(self):
        for fmt in EXPECTED_FORMATS:
            t = get(fmt)
            assert t.layout_contract.renderer

    def test_advisory_has_severity_section(self):
        t = get("advisory")
        keys = [s.key for s in t.content_contract.sections]
        assert "severity" in keys

    def test_twitter_has_char_limit(self):
        t = get("twitter_x")
        assert t.layout_contract.max_chars == 280

    def test_detail_bindings_exist(self):
        for fmt in EXPECTED_FORMATS:
            t = get(fmt)
            assert t.parameter_bindings.detail_level, f"{fmt} missing detail bindings"
