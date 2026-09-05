"""
sot/confidence.py — Confidence scoring formula (§1.4 of the plan).
confidence = w1*extraction_agreement + w2*source_quality
           + w3*support_count_bonus  - w4*contradiction_penalty
All weights come from config; every number is explainable on stage.
"""
from __future__ import annotations
from dataclasses import dataclass
from app.config import get_settings


@dataclass
class ConfidenceBand:
    score: float
    band: str          # "exclude" | "caveat" | "plain"
    label: str         # human-readable adverb for auto-caveat


def compute(
    extraction_agreement: float,
    source_quality: float,
    support_count: int,
    has_contradiction: bool,
    max_support: int = 5,
) -> float:
    cfg = get_settings()
    w1 = cfg.confidence_w1_extraction_agreement
    w2 = cfg.confidence_w2_source_quality
    w3 = cfg.confidence_w3_support_count
    w4 = cfg.confidence_w4_contradiction_penalty

    support_bonus = min(1.0, support_count / max_support)
    penalty = w4 if has_contradiction else 0.0

    score = (w1 * extraction_agreement
             + w2 * source_quality
             + w3 * support_bonus
             - penalty)
    return round(max(0.0, min(1.0, score)), 4)


def band(score: float) -> ConfidenceBand:
    cfg = get_settings()
    if score < cfg.confidence_exclude_below:
        return ConfidenceBand(score, "exclude",
                              "insufficient evidence")
    if score < cfg.confidence_caveat_below:
        return ConfidenceBand(score, "caveat",
                              "reportedly")
    return ConfidenceBand(score, "plain", "")
