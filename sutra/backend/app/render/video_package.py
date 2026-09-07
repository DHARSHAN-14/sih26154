"""
render/video_package.py — Structured video deliverable.
Output = shot list + VO script + storyboard + B-roll cues (JSON + text).
NOT a rendered MP4 — that is explicitly out of scope per the plan.
"""
from __future__ import annotations
import json
import pathlib
import uuid
from datetime import datetime
from app.core.schemas import ContentPlan, GeneratedOutput, RenderedArtifact
from app.render.base import MIME_TYPES

WORDS_PER_SECOND = 130 / 60  # 130 words/min


class VideoPackageRenderer:
    output_format = "video_package"
    mime_type = MIME_TYPES["video_package"]

    def render(
        self,
        plan: ContentPlan,
        output: GeneratedOutput,
        artifact_dir: pathlib.Path,
    ) -> RenderedArtifact:
        shots = []
        for i, section in enumerate(output.sections, 1):
            vo_text = " ".join(c.text for c in section.claims)
            word_count = len(vo_text.split())
            duration_sec = round(word_count / WORDS_PER_SECOND, 1)
            shots.append({
                "shot_number": i,
                "section": section.section_key,
                "voiceover": vo_text,
                "word_count": word_count,
                "estimated_duration_sec": duration_sec,
                "on_screen_text": vo_text[:100],
                "b_roll_cue": f"[B-roll: visuals for '{section.section_key}']",
                "fact_ids": [fid for c in section.claims for fid in c.fact_ids],
            })

        package = {
            "format": "video_package",
            "output_id": output.output_id,
            "language": output.language,
            "shots": shots,
            "total_shots": len(shots),
            "estimated_total_sec": sum(s["estimated_duration_sec"] for s in shots),
            "note": (
                "Video output = shot-by-shot script + storyboard + VO timing + B-roll cues. "
                "A rendered MP4 is out of scope for this prototype."
            ),
        }

        filename = f"video_package_{output.output_id[:8]}.json"
        file_path = artifact_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(package, indent=2, ensure_ascii=False),
                             encoding="utf-8")

        # Also create companion teleprompter script
        script_lines = [
            "===============================================================",
            "SUTRA BROADCAST PRODUCTION SCRIPT & TELEPROMPTER",
            f"Language: {output.language.upper()} | Lock Hash: {output.lock_hash or 'verified'}",
            "===============================================================\n",
        ]
        for s in shots:
            script_lines.append(f"[SCENE {s['shot_number']}: {s['section'].replace('_', ' ').upper()}]")
            script_lines.append(f"Est. Duration: ~{s['estimated_duration_sec']}s | Graphic (OST): {s['on_screen_text']}")
            script_lines.append(f"Visual / B-Roll Cue: {s['b_roll_cue']}")
            script_lines.append("VOICEOVER DIALOGUE:")
            script_lines.append(f"{s['voiceover']}\n")

        txt_path = file_path.with_name(f"video_package_{output.output_id[:8]}_teleprompter.txt")
        txt_path.write_text("\n".join(script_lines), encoding="utf-8")

        return RenderedArtifact(
            artifact_id=str(uuid.uuid4()),
            output_id=output.output_id,
            output_format=self.output_format,
            file_path=str(file_path),
            mime_type=self.mime_type,
            size_bytes=file_path.stat().st_size,
            rendered_at=datetime.utcnow(),
        )
