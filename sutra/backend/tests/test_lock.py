from __future__ import annotations
import pytest
from app.core.schemas import SourceOfTruth, Fact, NormalizedValues, Provenance
from app.sot.lock import lock, assert_locked, verify_hash, SoTAlreadyLockedError, SoTNotLockedError


def _dummy_sot() -> SourceOfTruth:
    f = Fact(
        fact_id="F-001",
        fact_type="claim",
        subject="System",
        predicate="status",
        object="secure",
        canonical_text="The system is fully secure.",
        normalized=NormalizedValues(),
        provenance=[
            Provenance(doc_id="DOC-1", locator="p1", chunk_id="CHK-1", snippet="system is secure")
        ],
        confidence=0.95,
    )
    return SourceOfTruth(
        sot_id="SOT-TEST",
        session_id="SESS-001",
        version=1,
        facts=[f],
    )


class TestLockLifecycle:
    def test_lock_and_verify(self):
        sot = _dummy_sot()
        assert sot.lock_hash is None
        locked_sot = lock(sot)
        assert locked_sot.lock_hash is not None
        assert verify_hash(locked_sot, locked_sot.lock_hash) is True

    def test_double_lock_rejection(self):
        sot = _dummy_sot()
        locked = lock(sot)
        with pytest.raises(SoTAlreadyLockedError):
            lock(locked)

    def test_assert_locked_guard(self):
        unlocked = _dummy_sot()
        with pytest.raises(SoTNotLockedError):
            assert_locked(unlocked)

        locked = lock(unlocked)
        assert_locked(locked)  # should not raise

    def test_tamper_detection(self):
        sot = _dummy_sot()
        locked = lock(sot)
        original_hash = locked.lock_hash
        # Modify canonical text after lock
        locked.facts[0].canonical_text = "The system was compromised."
        assert verify_hash(locked, original_hash) is False
