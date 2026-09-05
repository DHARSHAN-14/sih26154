"""
planner/coverage.py — Gap detection for required sections.
If a required section has no supporting evidence, emit a GapReport.
The system shows the gap to the operator; it does NOT invent content.
"""
from __future__ import annotations
from app.core.schemas import ContentPlan, GapReport


def check_coverage(plan: ContentPlan) -> list[GapReport]:
    """Return GapReports for required sections with no supporting facts."""
    gaps = []
    for section in plan.sections:
        if section.required and not section.fact_ids:
            gaps.append(GapReport(
                section_key=section.section_key,
                output_format=plan.output_format,
                required=True,
                reason="No supporting evidence found in the locked Source of Truth",
            ))
        elif section.gap:
            gaps.append(GapReport(
                section_key=section.section_key,
                output_format=plan.output_format,
                required=section.required,
                reason="Insufficient evidence (below min_facts threshold)",
            ))
    return gaps
