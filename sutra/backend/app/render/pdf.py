"""
render/pdf.py — PDF export via LibreOffice headless (for DOCX/PPTX) or WeasyPrint (for HTML).
LibreOffice path is the real layout-accurate path used by visual/pdf_probe.py.
WeasyPrint path is the fallback for HTML infographics.
"""
from __future__ import annotations
import pathlib
import subprocess
from app.core.logging import get_logger

logger = get_logger(__name__)


def docx_to_pdf(docx_path: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path | None:
    """
    Convert a DOCX to PDF using LibreOffice headless.
    Returns the PDF path, or None if LibreOffice is not available.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [
                "libreoffice", "--headless", "--convert-to", "pdf",
                "--outdir", str(output_dir), str(docx_path),
            ],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            pdf_name = docx_path.stem + ".pdf"
            pdf_path = output_dir / pdf_name
            if pdf_path.exists():
                logger.info("DOCX -> PDF", path=str(pdf_path))
                return pdf_path
        logger.warning("LibreOffice conversion failed",
                       stderr=result.stderr[:200])
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("LibreOffice not available", error=str(exc))
        return None


def pptx_to_pdf(pptx_path: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path | None:
    """Convert a PPTX to PDF using LibreOffice headless."""
    return docx_to_pdf(pptx_path, output_dir)


def html_to_pdf(html_path: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path | None:
    """
    Convert an HTML file to PDF using WeasyPrint.
    Falls back gracefully if WeasyPrint is not installed.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / (html_path.stem + ".pdf")
    try:
        from weasyprint import HTML  # type: ignore
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        logger.info("HTML -> PDF", path=str(pdf_path))
        return pdf_path
    except ImportError:
        logger.warning("WeasyPrint not installed — HTML->PDF skipped")
        return None
    except Exception as exc:
        logger.warning("WeasyPrint conversion failed", error=str(exc))
        return None
