from __future__ import annotations
import pytest
from app.sot.normalizer import normalize_number, normalize_date


class TestNumbers:
    def test_crore(self):
        q = normalize_number("4.2 crore")
        assert q is not None
        assert q.value == pytest.approx(42_000_000.0)

    def test_lakh(self):
        q = normalize_number("12 lakh")
        assert q is not None
        assert q.value == pytest.approx(1_200_000.0)

    def test_percentage(self):
        q = normalize_number("73.5%")
        assert q is not None
        assert q.unit == "percent"
        assert q.value == pytest.approx(73.5)

    def test_plain_integer(self):
        q = normalize_number("42")
        assert q is not None
        assert q.value == pytest.approx(42.0)

    def test_plain_with_commas(self):
        q = normalize_number("1,00,000")
        assert q is not None
        assert q.value == pytest.approx(100_000.0)


class TestDates:
    def test_full_date(self):
        ds = normalize_date("2026-03-14")
        assert ds is not None
        assert ds.iso_start == "2026-03-14"
        assert ds.granularity == "day"

    def test_year_only(self):
        ds = normalize_date("2024")
        assert ds is not None
        assert ds.iso_start == "2024"
        assert ds.granularity == "year"

    def test_year_month(self):
        ds = normalize_date("2025-07")
        assert ds is not None
        assert ds.iso_start == "2025-07"
        assert ds.granularity == "month"
