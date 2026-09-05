from __future__ import annotations
import pytest
from app.core.schemas import Claim, Fact, NormalizedValues, Quantity, DateSpan, Provenance
from app.validation.grounding import check_claim


def _make_fact(fact_id: str, numbers: list[float] = [], dates: list[str] = []) -> Fact:
    q_list = [Quantity(value=n, unit="count", raw=str(n)) for n in numbers]
    d_list = [DateSpan(iso_start=d, raw=d) for d in dates]
    return Fact(
        fact_id=fact_id,
        fact_type="metric",
        subject="Entity",
        predicate="has",
        object="value",
        canonical_text="Canonical fact text.",
        normalized=NormalizedValues(numbers=q_list, dates=d_list),
        provenance=[
            Provenance(doc_id="DOC-1", locator="p1", chunk_id="CHK-1", snippet="source snippet")
        ],
        confidence=0.9,
    )


class TestGrounding:
    def test_claim_grounded_numbers(self):
        f = _make_fact("F-001", numbers=[42000000.0])  # 4.2 crore
        claim = Claim(
            claim_id="CLM-01",
            section_key="findings",
            text="The project budget is 4.2 crore.",
            fact_ids=["F-001"],
        )
        unsupported = check_claim(claim, [f])
        assert len(unsupported) == 0, f"Expected 0 unsupported tokens, got: {unsupported}"

    def test_claim_unsupported_number(self):
        f = _make_fact("F-001", numbers=[42000000.0])
        claim = Claim(
            claim_id="CLM-02",
            section_key="findings",
            text="The project budget is 9.5 crore and affects 100 systems.",
            fact_ids=["F-001"],
        )
        unsupported = check_claim(claim, [f])
        assert len(unsupported) > 0
        tokens = [u.token.strip() for u in unsupported]
        assert any("9.5" in t or "100" in t for t in tokens)

    def test_claim_grounded_dates(self):
        f = _make_fact("F-002", dates=["2026-03-15"])
        claim = Claim(
            claim_id="CLM-03",
            section_key="findings",
            text="The vulnerability was disclosed on 2026-03-15.",
            fact_ids=["F-002"],
        )
        unsupported = check_claim(claim, [f])
        assert len(unsupported) == 0

    def test_claim_unsupported_date(self):
        f = _make_fact("F-002", dates=["2026-03-15"])
        claim = Claim(
            claim_id="CLM-04",
            section_key="findings",
            text="A patch will be available on 2028-12-01.",
            fact_ids=["F-002"],
        )
        unsupported = check_claim(claim, [f])
        assert any(u.token_type == "date" for u in unsupported)

    def test_union_of_multiple_facts(self):
        f1 = _make_fact("F-001", numbers=[10.0])
        f2 = _make_fact("F-002", numbers=[25.0])
        claim = Claim(
            claim_id="CLM-05",
            section_key="findings",
            text="Between 10 and 25 servers were patched.",
            fact_ids=["F-001", "F-002"],
        )
        unsupported = check_claim(claim, [f1, f2])
        assert len(unsupported) == 0
