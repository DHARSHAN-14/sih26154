"""
visual/office.py — LibreOffice headless orchestration for visual validation.
Converts office docs -> PDF -> PyMuPDF box extraction.
This is the real layout validation path (not pre-render prediction).
Prediction (visual/predict.py) catches ~80% of issues cheaply;
this catches the remaining 20% after actual rendering.
"""
from __future__ import annotations
import pathlib
from app.render.pdf import docx_to_pdf, pptx_to_pdf
from app.visual.pdf_probe import probe as pdf_probe
from app.visual.rules import MAX_PAGES_DEVIATION, MAX_SLIDES_DEVIATION
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_docx(
    docx_path: pathlib.Path,
    max_pages: int | None,
    artifact_dir: pathlib.Path,
) -> list[str]:
    """
    Convert DOCX -> PDF, probe layout, return list of violations.
    Empty list = pass.
    """
    violations: list[str] = []
    pdf_path = docx_to_pdf(docx_path, artifact_dir / "pdf_probes")
    if not pdf_path:
        logger.warning("LibreOffice unavailable — skipping docx visual check")
        return violations

    results = pdf_probe(pdf_path)

    if max_pages and results["page_count"] > max_pages + MAX_PAGES_DEVIATION:
        violations.append(
            f"Page count {results['page_count']} exceeds contract max {max_pages}"
        )

    for font_issue in results.get("font_violations", []):
        violations.append(f"Font: {font_issue}")

    return violations


def validate_pptx(
    pptx_path: pathlib.Path,
    max_slides: int | None,
    artifact_dir: pathlib.Path,
) -> list[str]:
    """Convert PPTX -> PDF, probe layout, return violations."""
    violations: list[str] = []
    pdf_path = pptx_to_pdf(pptx_path, artifact_dir / "pdf_probes")
    if not pdf_path:
        logger.warning("LibreOffice unavailable — skipping pptx visual check")
        return violations

    results = pdf_probe(pdf_path)

    if max_slides and results["page_count"] > max_slides + MAX_SLIDES_DEVIATION:
        violations.append(
            f"Slide count {results['page_count']} exceeds contract max {max_slides}"
        )

    return violations
