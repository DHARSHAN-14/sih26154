from __future__ import annotations
import pytest
from app.core.schemas import Fact, Provenance, NormalizedValues, SourceOfTruth
from app.core.ids import generate_fact_id


def make_fact(index: int = 1) -> Fact:
    return Fact(
        fact_id=generate_fact_id(index),
        fact_type="metric",
        subject="test subject",
        predicate="has_value",
        object="42",
        canonical_text="Test fact canonical text.",
        normalized=NormalizedValues(),
        provenance=[Provenance(
            doc_id="DOC-001",
            locator="p1",
            chunk_id="CHK-001",
            snippet="Test snippet.",
        )],
        confidence=0.85,
    )


class TestFactId:
    def test_format(self):
        assert generate_fact_id(1) == "F-001"
        assert generate_fact_id(14) == "F-014"
        assert generate_fact_id(100) == "F-100"


class TestFact:
    def test_create(self):
        f = make_fact()
        assert f.fact_id == "F-001"
        assert f.confidence == 0.85
        assert len(f.provenance) == 1

    def test_confidence_bounds(self):
        import pytest
        with pytest.raises(Exception):
            make_fact().__class__(
                fact_id="F-001", fact_type="metric",
                subject="s", predicate="p", object="o",
                canonical_text="t",
                normalized=NormalizedValues(),
                provenance=[], confidence=1.5,  # invalid
            )


class TestSoT:
    def test_create(self):
        sot = SourceOfTruth(sot_id="sot-1", session_id="sess-1")
        assert not sot.is_locked
        assert sot.lock_hash is None

    def test_fact_by_id(self):
        sot = SourceOfTruth(sot_id="sot-1", session_id="sess-1",
                            facts=[make_fact()])
        assert sot.fact_by_id("F-001") is not None
        assert sot.fact_by_id("F-999") is None
