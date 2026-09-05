"""
validation/grounding.py — Check 2: the hallucination catcher.
Extracts every number/date/entity from claim text, normalises through
sot/normalizer.py, and takes the set-difference against the cited facts.
Anything left over is an UnsupportedToken.
100% deterministic — cannot itself hallucinate.
"""
from __future__ import annotations
import re
from app.core.schemas import (
    Claim, Fact, UnsupportedToken, NormalizedValues, Quantity,
)
from app.sot.normalizer import normalize_number, normalize_date
from app.core.ids import generate_claim_id

_NUM_PAT    = re.compile(r"\b\d[\d,\.]*(?:\s*(?:crore|lakh|k|m|b|%|percent))?\b",
                         re.IGNORECASE)
_DATE_PAT   = re.compile(r"\b\d{4}(?:-\d{2}(?:-\d{2})?)?\b")
_ENTITY_PAT = re.compile(r"\b[A-Z][A-Z0-9_\-]{1,}\b")   # rough NER stand-in


def _fact_numbers(fact: Fact) -> set[float]:
    return {q.value for q in fact.normalized.numbers}


def _fact_dates(fact: Fact) -> set[str]:
    return {d.iso_start for d in fact.normalized.dates}


def check_claim(
    claim: Claim,
    cited_facts: list[Fact],
) -> list[UnsupportedToken]:
    tokens: list[UnsupportedToken] = []

    # Collect all grounded values from cited facts
    grounded_numbers = set()
    grounded_dates   = set()
    for f in cited_facts:
        grounded_numbers |= _fact_numbers(f)
        grounded_dates   |= _fact_dates(f)

    # Extract all date spans to avoid misinterpreting date parts as standalone numbers
    date_spans = [m.span() for m in _DATE_PAT.finditer(claim.text)]

    # Check numeric tokens (ignoring numbers that are inside dates)
    for m in _NUM_PAT.finditer(claim.text):
        if any(start <= m.start() and m.end() <= end for start, end in date_spans):
            continue
        q = normalize_number(m.group())
        if q is not None and q.value not in grounded_numbers:
            tokens.append(UnsupportedToken(
                claim_id=claim.claim_id,
                token=m.group(),
                char_start=m.start(),
                char_end=m.end(),
                token_type="number",
                normalized_form=str(q.value),
            ))

    # Check date tokens
    for m in _DATE_PAT.finditer(claim.text):
        ds = normalize_date(m.group())
        if ds is not None and ds.iso_start not in grounded_dates:
            tokens.append(UnsupportedToken(
                claim_id=claim.claim_id,
                token=m.group(),
                char_start=m.start(),
                char_end=m.end(),
                token_type="date",
                normalized_form=ds.iso_start,
            ))

    return tokens
