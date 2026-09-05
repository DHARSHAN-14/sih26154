"""
validation/dependency.py — Check 4: selective omission guard.
If a cited fact has depends_on edges, those facts must also be cited
somewhere in the same output — you cannot use a finding while silently
dropping the caveat that qualifies it.
"""
from __future__ import annotations
from app.core.schemas import GeneratedOutput, SourceOfTruth


def check(output: GeneratedOutput, sot: SourceOfTruth) -> list[str]:
    """Return list of violation messages.  Empty = pass."""
    # All fact_ids cited anywhere in the output
    cited: set[str] = set()
    for section in output.sections:
        for claim in section.claims:
            cited.update(claim.fact_ids)

    sot_map = {f.fact_id: f for f in sot.facts}
    errors: list[str] = []

    for fid in list(cited):
        fact = sot_map.get(fid)
        if not fact:
            continue
        for dep_id in fact.depends_on:
            if dep_id not in cited:
                errors.append(
                    f"Fact {fid!r} depends on {dep_id!r} but {dep_id!r} "                    f"is not cited in the output (selective omission)"
                )
    return errors
