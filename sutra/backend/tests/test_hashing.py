from __future__ import annotations
from app.core.schemas import SourceOfTruth, Fact, Provenance, NormalizedValues
from app.core.hashing import compute_lock_hash, verify
from app.core.ids import generate_fact_id


def _make_sot() -> SourceOfTruth:
    facts = [
        Fact(
            fact_id=generate_fact_id(i),
            fact_type="claim",
            subject=f"subject_{i}",
            predicate="predicate",
            object=f"object_{i}",
            canonical_text=f"Canonical text number {i}.",
            normalized=NormalizedValues(),
            provenance=[Provenance(
                doc_id="DOC-001", locator=f"p{i}",
                chunk_id=f"CHK-{i:03d}", snippet=f"snippet {i}",
            )],
            confidence=0.9,
        )
        for i in range(1, 4)
    ]
    return SourceOfTruth(sot_id="sot-test", session_id="sess-test", facts=facts)


class TestLockHash:
    def test_deterministic(self):
        sot = _make_sot()
        assert compute_lock_hash(sot) == compute_lock_hash(sot)

    def test_changes_on_fact_change(self):
        sot = _make_sot()
        h1 = compute_lock_hash(sot)
        sot.facts[0].canonical_text = "Modified text."
        h2 = compute_lock_hash(sot)
        assert h1 != h2

    def test_verify_true(self):
        sot = _make_sot()
        h = compute_lock_hash(sot)
        assert verify(sot, h)

    def test_verify_false_on_tamper(self):
        sot = _make_sot()
        h = compute_lock_hash(sot)
        sot.facts[0].canonical_text = "Tampered."
        assert not verify(sot, h)
