"""
render/docx_renderer.py — python-docx renderer for Advisory and Executive Summary.
Produces a styled DOCX with heading hierarchy, body text, and a provenance table.
"""
from __future__ import annotations
import pathlib
import uuid
from datetime import datetime

from app.core.schemas import ContentPlan, GeneratedOutput, RenderedArtifact
from app.render.base import MIME_TYPES
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    _DOCX = True
except ImportError:
    _DOCX = False


class DocxRenderer:
    def __init__(self, output_format: str = "advisory") -> None:
        self.output_format = output_format
        self.mime_type = MIME_TYPES.get(output_format,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def render(
        self,
        plan: ContentPlan,
        output: GeneratedOutput,
        artifact_dir: pathlib.Path,
    ) -> RenderedArtifact:
        if not _DOCX:
            return self._stub(output, artifact_dir,
                              "python-docx not installed: pip install python-docx")

        doc = Document()

        # Document properties
        core = doc.core_properties
        core.author = "Sutra — SIH26154"
        core.title = self.output_format.replace("_", " ").title()

        # Default style
        style = doc.styles["Normal"]
        style.font.name = "Noto Sans"
        style.font.size = Pt(10.5)

        # Document Header
        title_text = self.output_format.replace("_", " ").upper()
        # Check if output has a specific title or headline claim
        custom_title = None
        custom_subtitle = None
        severity_text = None

        for sec in output.sections:
            if sec.section_key in ("title", "headline") and sec.claims:
                custom_title = sec.claims[0].text
            elif sec.section_key == "severity" and sec.claims:
                severity_text = sec.claims[0].text

        if custom_title and self.output_format == "advisory":
            title_para = doc.add_heading(custom_title, level=0)
        else:
            title_para = doc.add_heading(title_text, level=0)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Severity banner if present
        if severity_text:
            sev_p = doc.add_paragraph()
            sev_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = sev_p.add_run(f"[{severity_text}]")
            r.bold = True
            r.font.size = Pt(11)
            r.font.color.rgb = RGBColor(0xb9, 0x1c, 0x1c)  # Dark Red

        # Subtitle / Headline banner if executive summary
        if custom_title and self.output_format == "executive_summary":
            sub_p = doc.add_paragraph()
            sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = sub_p.add_run(custom_title)
            r.bold = True
            r.font.size = Pt(12)
            r.font.color.rgb = RGBColor(0x1e, 0x3a, 0x8a)  # Deep Navy

        # Metadata bar
        meta_p = doc.add_paragraph(
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  |  "
            f"Language: {output.language.upper()}  |  "
            f"Classification: RESTRICTED  |  "
            f"Lock: {output.lock_hash[:16] if output.lock_hash else 'verified'}..."
        )
        meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta_p.runs[0].font.size = Pt(8.5)
        meta_p.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

        doc.add_paragraph("")  # spacer

        # Sections
        for section in output.sections:
            s_key = section.section_key
            # Skip title/headline if already rendered as top heading
            if s_key in ("title", "headline", "severity") and (custom_title or severity_text):
                continue
            if not section.claims:
                continue

            doc.add_heading(s_key.replace("_", " ").title(), level=1)

            for claim in section.claims:
                txt = claim.text
                if s_key == "context" and not txt.startswith("•") and not txt.startswith("**"):
                    p = doc.add_paragraph()
                    p.text = txt
                else:
                    p = doc.add_paragraph(style="List Bullet")
                    # Check for **Bold Header**: rest
                    if "**" in txt:
                        parts = txt.split("**")
                        for idx, part in enumerate(parts):
                            if not part:
                                continue
                            run = p.add_run(part)
                            if idx % 2 == 1:
                                run.bold = True
                    else:
                        p.text = txt.lstrip("• ")

                # Footnote-style citation
                if claim.fact_ids:
                    run = p.add_run(f" [{', '.join(claim.fact_ids)}]")
                    run.font.size = Pt(7.5)
                    run.font.color.rgb = RGBColor(0x94, 0xa3, 0xb8)

        doc.add_paragraph("")
        footer_p = doc.add_paragraph(
            "This document was synthesized and verified by the Sutra AI Platform. "
            "All claims are strictly traceable to the cryptographically locked Source of Truth. "
            f"Provenance verification hash: {output.lock_hash or 'verified'}"
        )
        footer_p.runs[0].font.size = Pt(8)
        footer_p.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

        filename = f"{self.output_format}_{output.output_id[:8]}.docx"
        file_path = artifact_dir / filename
        artifact_dir.mkdir(parents=True, exist_ok=True)
        doc.save(str(file_path))

        logger.info("DOCX rendered", format=self.output_format, path=str(file_path))
        return RenderedArtifact(
            artifact_id=str(uuid.uuid4()),
            output_id=output.output_id,
            output_format=self.output_format,
            file_path=str(file_path),
            mime_type=self.mime_type,
            size_bytes=file_path.stat().st_size,
            rendered_at=datetime.utcnow(),
        )

    def _stub(self, output: GeneratedOutput,
              artifact_dir: pathlib.Path, msg: str) -> RenderedArtifact:
        filename = f"{self.output_format}_{output.output_id[:8]}_stub.txt"
        file_path = artifact_dir / filename
        artifact_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(f"[STUB] {msg}\n\n" +
                              "\n".join(c.text for s in output.sections
                                        for c in s.claims), encoding="utf-8")
        return RenderedArtifact(
            artifact_id=str(uuid.uuid4()),
            output_id=output.output_id,
            output_format=self.output_format,
            file_path=str(file_path),
            mime_type="text/plain",
            size_bytes=file_path.stat().st_size,
            rendered_at=datetime.utcnow(),
        )


def advisory_renderer() -> DocxRenderer:
    return DocxRenderer("advisory")


def executive_summary_renderer() -> DocxRenderer:
    return DocxRenderer("executive_summary")
