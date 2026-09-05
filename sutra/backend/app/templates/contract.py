"""
templates/contract.py — Pydantic models for template contracts.
ContentContract: what info an output type structurally requires.
LayoutContract: rendering limits and visual checks.
ParameterBindings: how operator params reshape the plan.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class SectionSpec(BaseModel):
    key: str
    required: bool = True
    max_chars: int | None = None
    min_facts: int = 0
    max_claims: int | None = None
    prefers_fact_types: list[str] = Field(default_factory=list)
    on_missing: Literal["flag_gap", "skip", "generate_anyway"] = "flag_gap"
    enum_values: list[str] = Field(default_factory=list, alias="enum")

    model_config = {"populate_by_name": True}


class ContentContract(BaseModel):
    sections: list[SectionSpec] = Field(default_factory=list)


class LayoutContract(BaseModel):
    renderer: str                           # pptx | docx | html | social | video
    max_pages: int | None = None
    max_slides: int | None = None
    max_chars: int | None = None
    font_family: str = "Noto Sans"
    body_pt: float = 10.5
    heading_pt: float = 14.0
    checks: list[str] = Field(default_factory=list)


class DetailBinding(BaseModel):
    include: list[str] | str = Field(default_factory=list)  # list or "*"
    max_claims_per_section: int = 4


class AudienceBinding(BaseModel):
    tone: str = "neutral"
    jargon: str = "keep"
    prefers_fact_types: list[str] = Field(default_factory=list)
    sensitivity_max: str = "internal"


class ParameterBindings(BaseModel):
    detail_level: dict[str, DetailBinding] = Field(default_factory=dict)
    audience: dict[str, AudienceBinding] = Field(default_factory=dict)
    language: dict[str, Any] = Field(default_factory=dict)


class TemplateContract(BaseModel):
    id: str
    version: int = 1
    renderer: str
    content_contract: ContentContract = Field(default_factory=ContentContract)
    layout_contract: LayoutContract
    parameter_bindings: ParameterBindings = Field(default_factory=ParameterBindings)
