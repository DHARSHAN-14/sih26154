"""
planner/planner.py — Content plan per (output format × operator params).
The plan is produced BEFORE any prose is generated, so parameters
demonstrably change structure and fact selection, not just phrasing.
"""
from __future__ import annotations
import uuid
from app.core.schemas import SourceOfTruth, ContentPlan, SectionPlan, GapReport
from app.core.params import DetailLevel, Audience
from app.templates.registry import get as get_template
from app.planner.selection import select_facts_for_section
from app.core.logging import get_logger

logger = get_logger(__name__)


def plan(
    session_id: str,
    job_id: str,
    sot: SourceOfTruth,
    output_format: str,
    params: dict,
) -> tuple[ContentPlan, list[GapReport]]:
    """
    Build a ContentPlan for one output format.
    Returns (plan, gaps) where gaps are required sections with no evidence.
    """
    template = get_template(output_format)
    detail = params.get("detail_level", "medium")
    audience = params.get("audience", "executive")
    language = params.get("language", "en")

    detail_binding = template.parameter_bindings.detail_level.get(detail)
    audience_binding = template.parameter_bindings.audience.get(audience)

    # Determine which sections to include
    if detail_binding:
        include = detail_binding.include
        max_claims = detail_binding.max_claims_per_section
    else:
        include = "*"
        max_claims = 4

    # Sensitivity filter
    sensitivity_max = "internal"
    if audience_binding:
        sensitivity_max = audience_binding.sensitivity_max

    _SENSITIVITY_ORDER = ["public", "internal", "restricted"]
    allowed_sensitivity = _SENSITIVITY_ORDER[: _SENSITIVITY_ORDER.index(sensitivity_max) + 1]

    available_facts = [
        f for f in sot.facts
        if f.sensitivity in allowed_sensitivity and not getattr(f, "is_excluded", False)
        and f.confidence >= 0.5
    ]

    sections: list[SectionPlan] = []
    gaps: list[GapReport] = []

    # Extract RAG retrieval mappings if present
    section_retrieved = params.get("section_retrieved_facts", {})
    retrieved_chunk_ids = set(params.get("retrieved_chunk_ids", []))

    for spec in template.content_contract.sections:
        if include != "*" and spec.key not in include:
            continue

        # Determine preferred fact IDs from RAG
        pref_ids = set(section_retrieved.get(spec.key, []))
        if not pref_ids and retrieved_chunk_ids:
            for f in available_facts:
                if any(p.chunk_id in retrieved_chunk_ids for p in f.provenance):
                    pref_ids.add(f.fact_id)

        selected = select_facts_for_section(
            spec=spec,
            available_facts=available_facts,
            max_claims=max_claims,
            preferred_fact_ids=pref_ids,
        )

        gap = spec.required and len(selected) < spec.min_facts
        if gap:
            gaps.append(GapReport(
                section_key=spec.key,
                output_format=output_format,
                required=spec.required,
            ))

        sections.append(SectionPlan(
            section_key=spec.key,
            required=spec.required,
            fact_ids=[f.fact_id for f in selected],
            max_chars=spec.max_chars,
            max_claims=max_claims,
            gap=gap,
        ))

    content_plan = ContentPlan(
        plan_id=str(uuid.uuid4()),
        session_id=session_id,
        job_id=job_id,
        output_format=output_format,
        sot_id=sot.sot_id,
        lock_hash=sot.lock_hash or "",
        sections=sections,
        language=language,
        audience=audience,
        tone=params.get("tone", "neutral"),
        detail_level=detail,
    )

    logger.info("Plan built", format=output_format,
                sections=len(sections), gaps=len(gaps))
    return content_plan, gaps
