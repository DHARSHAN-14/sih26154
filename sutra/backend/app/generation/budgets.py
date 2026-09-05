"""
generation/budgets.py — Per-section token/character budgets.
Keeps 'how much text fits on a slide' in exactly one place so
the generator and visual validator can never disagree.
"""
from __future__ import annotations
from app.templates.contract import TemplateContract


def section_char_budget(contract: TemplateContract, section_key: str) -> int | None:
    """Return the max_chars for a section, or None if unconstrained."""
    for spec in contract.content_contract.sections:
        if spec.key == section_key:
            return spec.max_chars
    return None


def total_token_budget(contract: TemplateContract, detail_level: str = "medium") -> int:
    """Estimate total token budget for a format based on section limits."""
    binding = contract.parameter_bindings.detail_level.get(detail_level)
    max_per = binding.max_claims_per_section if binding else 4
    total_chars = sum(
        (spec.max_chars or 400) * max_per
        for spec in contract.content_contract.sections
    )
    return total_chars // 4  # rough chars-to-tokens
