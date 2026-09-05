"""
planner/gapfill.py — Handles required sections with no supporting evidence.
Policy: NEVER invent content. Options:
  1. flag_gap  — include the section header but mark [EVIDENCE GAP]
  2. skip      — omit the section silently (set in template on_missing)
  3. generate_anyway — allowed only for boilerplate sections (references, dates)
The operator sees gaps before generation; they can cancel or proceed.
"""
from __future__ import annotations
from app.core.schemas import GapReport, SectionPlan
from app.templates.contract import SectionSpec


def apply_gap_policy(
    spec: SectionSpec,
    section: SectionPlan,
) -> SectionPlan:
    """
    Mutate the section plan according to the template's on_missing policy.
    Returns the (possibly-modified) section plan.
    """
    policy = spec.on_missing

    if policy == "skip":
        # Mark as skipped — generator will omit
        section.gap = True
        section.skip = True
    elif policy == "flag_gap":
        # Keep section, mark as gap — generator emits [EVIDENCE GAP] marker
        section.gap = True
        section.skip = False
    elif policy == "generate_anyway":
        # Only valid for boilerplate (references, footer, metadata)
        # Do not set gap — generator proceeds with zero facts
        section.gap = False
        section.skip = False
    else:
        # Default: flag_gap
        section.gap = True
        section.skip = False

    return section


def gap_summary(gaps: list[GapReport]) -> str:
    """Human-readable gap summary for operator confirmation UI."""
    if not gaps:
        return "No evidence gaps detected."
    lines = [f"Evidence gaps found in {len(gaps)} required section(s):"]
    for g in gaps:
        req = "(required)" if g.required else "(optional)"
        lines.append(f"  - {g.output_format} / {g.section_key} {req}")
    lines.append("Proceed? The system will mark gaps clearly in the output.")
    return "\n".join(lines)
