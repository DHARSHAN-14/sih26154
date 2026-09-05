"""
sot/dependencies.py — Detect when one fact qualifies another.
Writes depends_on edges that the dependency validator enforces.
"""
from __future__ import annotations
import re
from app.core.schemas import Fact

_CAVEAT_SIGNALS = re.compile(
    r"\b(only if|provided that|assuming|unless|except when|"
    r"in tested configurations|preliminary|reportedly|subject to)\b",
    re.IGNORECASE,
)


def infer_dependencies(facts: list[Fact]) -> list[Fact]:
    """
    For each fact whose canonical_text contains a caveat signal,
    look for a plausible qualifier fact and add depends_on edges.
    Stub: regex-only, no semantic matching.
    """
    # Mark facts that contain caveats
    caveat_ids = {
        f.fact_id for f in facts
        if _CAVEAT_SIGNALS.search(f.canonical_text)
    }
    # Any fact that mentions a caveat-bearing fact's subject depends on it
    # (simplified heuristic for stub)
    for fact in facts:
        for caveat_id in caveat_ids:
            if caveat_id != fact.fact_id and caveat_id not in fact.depends_on:
                caveat_fact = next((f for f in facts if f.fact_id == caveat_id), None)
                if caveat_fact and caveat_fact.subject.lower() in fact.canonical_text.lower():
                    fact.depends_on.append(caveat_id)
    return facts
