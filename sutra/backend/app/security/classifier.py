"""
security/classifier.py — Sensitivity classification for ingested facts.
Classifies each fact as public / internal / restricted based on
keyword rules and regex patterns. Ensures sensitivity_max in audience
bindings is enforced structurally, not by hope.
Stub: keyword-based only; replace with a proper NER-based classifier.
"""
from __future__ import annotations
import re
from typing import Literal

SensitivityLevel = Literal["public", "internal", "restricted"]

_RESTRICTED_PATTERNS = re.compile(
    r"\b(classified|top secret|secret|restricted|confidential|"
    r"noforn|orcon|TS/SCI|compartmented|SIGINT|HUMINT|IMINT)\b",
    re.IGNORECASE,
)

_INTERNAL_PATTERNS = re.compile(
    r"\b(internal use|not for public|draft|pre-decisional|"
    r"deliberative|for official use only|FOUO|sensitive)\b",
    re.IGNORECASE,
)


def classify(text: str) -> SensitivityLevel:
    """
    Return sensitivity level for a text span.
    Restricted > Internal > Public.
    """
    if _RESTRICTED_PATTERNS.search(text):
        return "restricted"
    if _INTERNAL_PATTERNS.search(text):
        return "internal"
    return "public"


def classify_bulk(texts: list[str]) -> list[SensitivityLevel]:
    return [classify(t) for t in texts]


def max_sensitivity(levels: list[SensitivityLevel]) -> SensitivityLevel:
    """Return the highest sensitivity level from a list."""
    order = {"public": 0, "internal": 1, "restricted": 2}
    if not levels:
        return "internal"
    return max(levels, key=lambda x: order[x])
