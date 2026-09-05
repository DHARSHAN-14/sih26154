"""
render/base.py — Renderer protocol and shared helpers.
A common interface means the pipeline treats all 7 formats identically;
adding an 8th format needs no pipeline change.
"""
from __future__ import annotations
import pathlib
from typing import Protocol, runtime_checkable
from app.core.schemas import ContentPlan, GeneratedOutput, RenderedArtifact


@runtime_checkable
class Renderer(Protocol):
    output_format: str
    mime_type: str

    def render(
        self,
        plan: ContentPlan,
        output: GeneratedOutput,
        artifact_dir: pathlib.Path,
    ) -> RenderedArtifact:
        ...


MIME_TYPES: dict[str, str] = {
    "advisory":          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "executive_summary": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "presentation":      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "linkedin":          "text/plain",
    "twitter_x":         "text/plain",
    "infographic":       "text/html",
    "video_package":     "application/json",
}
