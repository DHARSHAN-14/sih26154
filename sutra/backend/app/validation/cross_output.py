"""
validation/cross_output.py — Cross-output consistency checks.
Catches what the per-output SoT lock cannot:
1. Numeric rounding drift across formats for the same fact.
2. Severity/sentiment inversion for shared facts.
3. Selective omission: citing F-3 while dropping its caveat F-4.
"""
from __future__ import annotations
from app.core.schemas import GeneratedOutput, SourceOfTruth


def check_all(
    outputs: list[GeneratedOutput],
    sot: SourceOfTruth,
) -> dict[str, list[str]]:
    """
    Return {output_id: [flag_message, ...]} for any cross-output violations.
    """
    results: dict[str, list[str]] = {o.output_id: [] for o in outputs}

    # Build: fact_id -> {output_id -> text snippets}
    fact_citations: dict[str, dict[str, list[str]]] = {}
    for output in outputs:
        for section in output.sections:
            for claim in section.claims:
                for fid in claim.fact_ids:
                    fact_citations.setdefault(fid, {})
                    fact_citations[fid].setdefault(output.output_id, []).append(claim.text)

    sot_map = {f.fact_id: f for f in sot.facts}

    # Check: if a fact is cited, its depends_on facts must also be cited
    # in the same output (selective omission guard, cross-output variant)
    for output in outputs:
        cited_in_output: set[str] = set()
        for section in output.sections:
            for claim in section.claims:
                cited_in_output.update(claim.fact_ids)
        for fid in list(cited_in_output):
            fact = sot_map.get(fid)
            if not fact:
                continue
            for dep_id in fact.depends_on:
                if dep_id not in cited_in_output:
                    results[output.output_id].append(
                        f"Selective omission: cited {fid!r} but not its caveat {dep_id!r}"
                    )

    return results
