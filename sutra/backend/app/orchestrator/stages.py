"""
orchestrator/stages.py — Each pipeline stage as a typed stub.
Stages are independently testable and replay-able from persisted artifacts.
Implementation is filled in as each phase completes.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class StageContext:
    session_id: str
    job_id: str
    sot_id: str
    artifact_dir: str
    params: dict[str, Any]
    source_paths: list[str]
    formats: list[str]
    # Filled as pipeline progresses:
    sot: Any = None
    content_plans: dict[str, Any] = None   # format -> ContentPlan
    generated: dict[str, Any] = None       # format -> GeneratedOutput
    artifacts: dict[str, Any] = None       # format -> RenderedArtifact
    validation_reports: dict[str, Any] = None


STAGE_NAMES = [
    "ingest",
    "sanitize",
    "route",
    "retrieve",
    "extract_facts",
    "build_kg",
    "build_sot",
    "lock_sot",
    "plan",           # fan-out starts here (per output format)
    "generate",
    "validate_facts",
    "render",
    "validate_visual",
    "cross_check",
    "finalize",
]
