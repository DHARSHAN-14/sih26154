from __future__ import annotations
import pytest
from app.core.schemas import SourceOfTruth, Fact, Provenance, NormalizedValues
from app.core.ids import generate_fact_id
from app.sot.lock import lock, assert_locked
from app.core.errors import SoTAlreadyLockedError, SoTNotLockedError


def _sot() -> SourceOfTruth:
    return SourceOfTruth(
        sot_id="test-sot",
        session_id="test-session",
        facts=[
            Fact(
                fact_id=generate_fact_id(1),
                fact_type="claim",
                subject="s", predicate="p", object="o",
                canonical_text="Test canonical text.",
                normalized=NormalizedValues(),
                provenance=[Provenance(
                    doc_id="DOC-001", locator="p1",
                    chunk_id="CHK-001", snippet="snippet",
                )],
                confidence=0.9,
            )
        ]
    )


class TestLock:
    def test_lock_sets_hash(self):
        sot = lock(_sot())
        assert sot.is_locked
        assert sot.lock_hash is not None
        assert len(sot.lock_hash) == 64  # SHA-256 hex

    def test_double_lock_raises(self):
        sot = lock(_sot())
        with pytest.raises(SoTAlreadyLockedError):
            lock(sot)

    def test_assert_locked_raises_when_not_locked(self):
        with pytest.raises(SoTNotLockedError):
            assert_locked(_sot())

    def test_assert_locked_passes_when_locked(self):
        sot = lock(_sot())
        assert_locked(sot)  # should not raise
