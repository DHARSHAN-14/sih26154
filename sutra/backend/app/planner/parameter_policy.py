"""
planner/parameter_policy.py — Resolves operator parameters against template bindings.
Centralises all parameter-to-plan logic so the planner stays clean.
Key guarantee: parameters reshape the plan structure (which sections exist,
which facts are eligible), NOT just the wording — demonstrable live.
"""
from __future__ import annotations
from app.core.params import Audience, DetailLevel, Language, Tone
from app.templates.contract import (
    TemplateContract, DetailBinding, AudienceBinding
)

_SENSITIVITY_ORDER = ["public", "internal", "restricted"]


def resolve_detail(
    contract: TemplateContract, detail_level: str
) -> DetailBinding | None:
    """Return the detail binding for this level, or None for defaults."""
    return contract.parameter_bindings.detail_level.get(detail_level)


def resolve_audience(
    contract: TemplateContract, audience: str
) -> AudienceBinding | None:
    """Return the audience binding for this audience type."""
    return contract.parameter_bindings.audience.get(audience)


def sensitivity_max_for_audience(
    contract: TemplateContract, audience: str
) -> str:
    """Return the highest allowed sensitivity for this audience."""
    binding = resolve_audience(contract, audience)
    if binding:
        return binding.sensitivity_max
    # Default: public audiences get public facts only
    if audience == "public":
        return "public"
    return "internal"


def included_sections(
    contract: TemplateContract, detail_level: str
) -> list[str] | str:
    """Return the list of section keys to include, or '*' for all."""
    binding = resolve_detail(contract, detail_level)
    if binding:
        return binding.include
    return "*"


def max_claims_per_section(
    contract: TemplateContract, detail_level: str
) -> int:
    """Return the max claims per section for this detail level."""
    binding = resolve_detail(contract, detail_level)
    if binding:
        return binding.max_claims_per_section
    return 4   # sensible default


def tone_for_audience(contract: TemplateContract, audience: str) -> str:
    """Return the tone string for this audience binding."""
    binding = resolve_audience(contract, audience)
    if binding:
        return binding.tone
    return "neutral"
