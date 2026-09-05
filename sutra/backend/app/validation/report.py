"""
validation/report.py — Assemble the ValidationReport for one output.
PASS   = all checks green.
REPAIRED = had failures, all fixed within MAX_REPAIR_ATTEMPTS.
REVIEW = exhausted repair attempts; route to human queue.
"""
from __future__ import annotations
from app.core.schemas import (
    GeneratedOutput, SourceOfTruth,
    ValidationReport, UnsupportedToken, RepairInstruction, GapReport,
)
from app.validation import citation, grounding, dependency


def build(
    output: GeneratedOutput,
    sot: SourceOfTruth,
    unsupported_tokens: list[UnsupportedToken] | None = None,
    repair_history: list[RepairInstruction] | None = None,
    gaps: list[GapReport] | None = None,
    cross_output_flags: list[str] | None = None,
) -> ValidationReport:
    cite_errs = citation.check(output, sot)
    dep_errs  = dependency.check(output, sot)

    ut = unsupported_tokens or []
    rh = repair_history or []
    gp = gaps or []
    cf = cross_output_flags or []

    citation_ok  = len(cite_errs) == 0
    grounding_ok = len(ut) == 0
    dependency_ok = len(dep_errs) == 0

    all_ok = citation_ok and grounding_ok and dependency_ok and not cf

    if all_ok and not rh:
        verdict = "pass"
    elif all_ok and rh:
        verdict = "repaired"
    else:
        verdict = "review"

    return ValidationReport(
        output_id=output.output_id,
        verdict=verdict,
        citation_ok=citation_ok,
        grounding_ok=grounding_ok,
        entailment_ok=True,   # set by entailment.py when implemented
        dependency_ok=dependency_ok,
        unsupported_tokens=ut,
        repair_history=rh,
        gaps=gp,
        cross_output_flags=cf,
    )
