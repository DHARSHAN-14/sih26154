"""
core/schemas.py  —  THE contract every module codes against.

Freeze this on day 1; change only by team agreement.
These Pydantic models double as JSON schemas for constrained decoding,
so a field rename silently changes what the LLM is allowed to emit.

ALL field names use snake_case.  ALL IDs follow core/ids.py conventions.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Provenance — every generated fact traces back to a source span
# ─────────────────────────────────────────────────────────────────────────────

class Provenance(BaseModel):
    """Pointer back to the exact location in the source document."""
    doc_id: str
    locator: str            # "p4" | "t00:14:22" | "slide3" | "sheet1!B7"
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None  # normalized 0-1
    char_start: int | None = None
    char_end: int | None = None
    chunk_id: str
    snippet: str            # ≤300 chars — exact source sentence for the panel


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Normalized values — canonical form for deterministic grounding
# ─────────────────────────────────────────────────────────────────────────────

class Quantity(BaseModel):
    """A normalized numeric quantity."""
    value: float
    unit: str
    raw: str                # original surface form, e.g. "₹4.2 crore"
    scale: float = 1.0      # multiplier applied (e.g. crore = 10_000_000)


class DateSpan(BaseModel):
    """An ISO-normalized date or date range."""
    iso_start: str          # ISO 8601
    iso_end: str | None = None
    granularity: Literal["year", "month", "day", "time"] = "day"
    raw: str                # original surface form


class EntityRef(BaseModel):
    """A reference to a named entity, resolved to a canonical ID."""
    surface: str            # as it appears in text
    canonical_id: str       # stable across the document
    entity_type: str        # PERSON | ORG | LOCATION | CVE | IP | ...


class NormalizedValues(BaseModel):
    numbers: list[Quantity] = Field(default_factory=list)
    dates: list[DateSpan] = Field(default_factory=list)
    entities: list[EntityRef] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Fact — the atomic unit of the Source of Truth
# ─────────────────────────────────────────────────────────────────────────────

class Fact(BaseModel):
    """
    One verifiable, provenance-linked statement from the source.

    fact_id is stable: the same fact in a re-run keeps its ID so version
    diffs and provenance links don't break.
    """
    fact_id: str                    # "F-014"
    fact_type: Literal[
        "metric", "event", "attribute", "relation",
        "claim", "quote", "definition"
    ]
    subject: str
    predicate: str
    object: str
    canonical_text: str             # one self-contained human-verifiable sentence
    normalized: NormalizedValues = Field(default_factory=NormalizedValues)
    provenance: list[Provenance] = Field(default_factory=list)  # ≥1
    confidence: float = Field(ge=0.0, le=1.0)
    contradicts: list[str] = Field(default_factory=list)        # other fact_ids
    depends_on: list[str] = Field(default_factory=list)         # caveat facts
    sensitivity: Literal["public", "internal", "restricted"] = "internal"
    extraction_pass: int = 1        # which self-consistency pass produced this


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Entity and Timeline — KG structures
# ─────────────────────────────────────────────────────────────────────────────

class Entity(BaseModel):
    canonical_id: str
    entity_type: str
    surface_forms: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    event_id: str
    timestamp: str          # ISO 8601
    description: str
    fact_ids: list[str] = Field(default_factory=list)
    before: list[str] = Field(default_factory=list)   # event_ids
    after: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Source of Truth — the locked, hashed, immutable fact set
# ─────────────────────────────────────────────────────────────────────────────

class SourceOfTruth(BaseModel):
    """
    The frozen fact set.  After lock(), this object is immutable.
    lock_hash is SHA-256 over sorted canonical_texts; show it in the UI.
    """
    model_config = ConfigDict(frozen=False)  # mutable until lock()

    sot_id: str
    session_id: str
    version: int = 1
    facts: list[Fact] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    graph_ref: str = ""             # path to serialized KG JSON
    locked_at: datetime | None = None
    lock_hash: str | None = None    # SHA-256; None until locked
    is_locked: bool = False

    def fact_by_id(self, fact_id: str) -> Fact | None:
        return next((f for f in self.facts if f.fact_id == fact_id), None)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Content plan — structured before any prose is generated
# ─────────────────────────────────────────────────────────────────────────────

class SectionPlan(BaseModel):
    section_key: str
    required: bool
    fact_ids: list[str] = Field(default_factory=list)
    max_chars: int | None = None
    max_claims: int | None = None
    gap: bool = False               # True = required but no supporting evidence


class ContentPlan(BaseModel):
    plan_id: str
    session_id: str
    job_id: str
    output_format: str
    sot_id: str
    lock_hash: str
    sections: list[SectionPlan] = Field(default_factory=list)
    token_budget: int = 4096
    language: str = "en"
    audience: str = "executive"
    tone: str = "neutral"
    detail_level: str = "medium"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Claims — structured generator output; never free prose
# ─────────────────────────────────────────────────────────────────────────────

class Claim(BaseModel):
    """
    One generated claim.  fact_ids MUST cite the locked SoT.
    Validation is mechanical against these IDs.
    """
    claim_id: str
    section_key: str
    text: str
    fact_ids: list[str] = Field(default_factory=list)


class GeneratedSection(BaseModel):
    section_key: str
    claims: list[Claim] = Field(default_factory=list)
    raw_text: str = ""


class GeneratedOutput(BaseModel):
    output_id: str
    job_id: str
    session_id: str
    output_format: str
    plan_id: str
    lock_hash: str
    sections: list[GeneratedSection] = Field(default_factory=list)
    language: str = "en"
    generation_model: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Validation
# ─────────────────────────────────────────────────────────────────────────────

class UnsupportedToken(BaseModel):
    """A token in a claim that has no grounding in the cited facts."""
    claim_id: str
    token: str
    char_start: int
    char_end: int
    token_type: str         # "number" | "date" | "entity" | "other"
    normalized_form: str


class RepairInstruction(BaseModel):
    claim_id: str
    failure_type: str       # "citation" | "grounding" | "entailment" | "dependency"
    offending_span: str
    char_start: int
    char_end: int
    permitted_fact_ids: list[str] = Field(default_factory=list)
    attempt: int = 1


class GapReport(BaseModel):
    section_key: str
    output_format: str
    required: bool = True
    reason: str = "No supporting evidence found in the source"


class ValidationReport(BaseModel):
    output_id: str
    verdict: Literal["pass", "repaired", "review"]
    citation_ok: bool = True
    grounding_ok: bool = True
    entailment_ok: bool = True
    dependency_ok: bool = True
    unsupported_tokens: list[UnsupportedToken] = Field(default_factory=list)
    repair_history: list[RepairInstruction] = Field(default_factory=list)
    gaps: list[GapReport] = Field(default_factory=list)
    cross_output_flags: list[str] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# 9.  Rendered artifact
# ─────────────────────────────────────────────────────────────────────────────

class RenderedArtifact(BaseModel):
    artifact_id: str
    output_id: str
    output_format: str
    file_path: str
    mime_type: str
    size_bytes: int = 0
    screenshot_path: str | None = None
    visual_ok: bool | None = None   # None = not yet checked
    visual_failures: list[str] = Field(default_factory=list)
    rendered_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Pipeline events — emitted over SSE
# ─────────────────────────────────────────────────────────────────────────────

class StageEvent(BaseModel):
    event_id: str
    session_id: str
    job_id: str
    stage: str
    status: str
    type: str = ""
    stageId: str = ""
    progress: int = 0
    message: str = ""
    elapsed_ms: int = 0
    counters: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
