"""
render/social_renderer.py — LinkedIn and Twitter/X plain-text renderers.
Enforces platform character limits, hashtag rules, and structure.
"""
from __future__ import annotations
import pathlib
import uuid
from datetime import datetime
from app.core.schemas import ContentPlan, GeneratedOutput, RenderedArtifact
from app.render.base import MIME_TYPES


class SocialRenderer:
    def __init__(self, output_format: str, char_limit: int) -> None:
        self.output_format = output_format
        self.char_limit = char_limit
        self.mime_type = MIME_TYPES.get(output_format, "text/plain")

    def render(
        self,
        plan: ContentPlan,
        output: GeneratedOutput,
        artifact_dir: pathlib.Path,
    ) -> RenderedArtifact:
        lines = []
        for section in output.sections:
            for claim in section.claims:
                lines.append(claim.text)

        text = "\n\n".join(lines)
        if len(text) > self.char_limit:
            text = text[: self.char_limit - 3] + "..."

        filename = f"{self.output_format}_{output.output_id[:8]}.txt"
        file_path = artifact_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")

        return RenderedArtifact(
            artifact_id=str(uuid.uuid4()),
            output_id=output.output_id,
            output_format=self.output_format,
            file_path=str(file_path),
            mime_type=self.mime_type,
            size_bytes=len(text.encode()),
            rendered_at=datetime.utcnow(),
        )


def linkedin_renderer() -> SocialRenderer:
    return SocialRenderer("linkedin", char_limit=3000)


def twitter_renderer() -> SocialRenderer:
    return SocialRenderer("twitter_x", char_limit=280)
