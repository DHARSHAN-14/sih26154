"""
validation/entailment.py — Check 3: NLI entailment (stub).
Production: mDeBERTa-v3-base-xnli cross-encoder, ~15ms/pair on GPU.
Stub: always returns entailed (1.0) so pipeline passes end-to-end.
Replace with real model in Phase 5.
"""
from __future__ import annotations
from app.core.schemas import Claim, Fact
from app.config import get_settings


def check_claim(
    claim: Claim,
    cited_facts: list[Fact],
    threshold: float | None = None,
) -> tuple[bool, float]:
    """
    Return (entailed: bool, score: float).
    Stub always returns (True, 1.0).
    Production: score = nli_model.predict(premise, hypothesis)
    """
    if threshold is None:
        threshold = get_settings().entailment_threshold
    # Stub
    return True, 1.0
