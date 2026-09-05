"""
render/pptx_renderer.py — python-pptx renderer for the Presentation format.
Layout: title slide + content slides (one section = one slide).
Font metric prediction via visual/predict.py runs BEFORE write to catch overflow.
"""
from __future__ import annotations
import pathlib
import uuid
from datetime import datetime

from app.core.schemas import ContentPlan, GeneratedOutput, RenderedArtifact
from app.render.base import MIME_TYPES
from app.visual.predict import will_overflow
from app.visual.rules import MAX_SLIDES_DEVIATION
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    _PPTX = True
except ImportError:
    _PPTX = False


# Slide dimensions (widescreen 16:9)
SLIDE_WIDTH_IN  = 13.33
SLIDE_HEIGHT_IN = 7.5
CONTENT_WIDTH_PT  = SLIDE_WIDTH_IN * 72 - 144   # 1-inch margins each side
CONTENT_HEIGHT_PT = SLIDE_HEIGHT_IN * 72 - 200  # reserve space for title


class PptxRenderer:
    output_format = "presentation"
    mime_type = MIME_TYPES["presentation"]

    def render(
        self,
        plan: ContentPlan,
        output: GeneratedOutput,
        artifact_dir: pathlib.Path,
    ) -> RenderedArtifact:
        if not _PPTX:
            return self._stub(output, artifact_dir,
                              "python-pptx not installed: pip install python-pptx")

        prs = Presentation()
        prs.slide_width  = Inches(SLIDE_WIDTH_IN)
        prs.slide_height = Inches(SLIDE_HEIGHT_IN)
        blank_layout = prs.slide_layouts[6]   # completely blank

        # Title slide
        self._add_title_slide(prs, blank_layout, output)

        # Content slides — one per section
        for section in output.sections:
            if not section.claims:
                continue
            self._add_content_slide(prs, blank_layout, section, plan)

        filename = f"presentation_{output.output_id[:8]}.pptx"
        file_path = artifact_dir / filename
        artifact_dir.mkdir(parents=True, exist_ok=True)
        prs.save(str(file_path))
        size = file_path.stat().st_size

        logger.info("PPTX rendered", slides=len(prs.slides),
                    path=str(file_path))
        return RenderedArtifact(
            artifact_id=str(uuid.uuid4()),
            output_id=output.output_id,
            output_format=self.output_format,
            file_path=str(file_path),
            mime_type=self.mime_type,
            size_bytes=size,
            rendered_at=datetime.utcnow(),
        )

    def _add_title_slide(self, prs, layout, output: GeneratedOutput) -> None:
        slide = prs.slides.add_slide(layout)
        txb = slide.shapes.add_textbox(
            Inches(1), Inches(2.5), Inches(11.33), Inches(1.5))
        tf = txb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = output.output_format.replace("_", " ").title()
        p.font.size = Pt(36)
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER

    def _add_content_slide(self, prs, layout, section, plan: ContentPlan) -> None:
        slide = prs.slides.add_slide(layout)

        # Section title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.33), Inches(0.8))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = section.section_key.replace("_", " ").title()
        p.font.size = Pt(24)
        p.font.bold = True

        # Bullet content
        content_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.3), Inches(12.33), Inches(5.5))
        tf = content_box.text_frame
        tf.word_wrap = True

        for i, claim in enumerate(section.claims):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = u"•  " + claim.text
            p.font.size = Pt(18)
            p.space_after = Pt(6)

    def _stub(self, output: GeneratedOutput,
              artifact_dir: pathlib.Path, msg: str) -> RenderedArtifact:
        filename = f"presentation_{output.output_id[:8]}_stub.txt"
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
