"""
visual/screenshot.py — Screenshots for the results panel.
PPTX/DOCX: screenshot the LibreOffice-converted PDF via PyMuPDF.
HTML: screenshot via Playwright (done in html_probe.py).
Screenshots are stored as artifacts and shown in the UI results panel.
"""
from __future__ import annotations
import pathlib
from app.core.logging import get_logger

logger = get_logger(__name__)


def screenshot_pdf_page(
    pdf_path: pathlib.Path,
    output_path: pathlib.Path,
    page_num: int = 0,
    dpi: int = 150,
) -> pathlib.Path | None:
    """
    Render page `page_num` of a PDF to a PNG screenshot.
    Returns the output path, or None on failure.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        if page_num >= len(doc):
            return None
        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(output_path))
        doc.close()
        logger.info("Screenshot saved", path=str(output_path))
        return output_path
    except ImportError:
        logger.warning("PyMuPDF not installed — screenshot skipped")
        return None
    except Exception as exc:
        logger.warning("Screenshot failed", error=str(exc))
        return None


def screenshot_first_page(
    file_path: pathlib.Path,
    artifact_dir: pathlib.Path,
) -> pathlib.Path | None:
    """
    Convenience wrapper: screenshot the first page of a rendered office doc PDF.
    The PDF must already exist (rendered by render/pdf.py).
    """
    if file_path.suffix.lower() == ".pdf":
        pdf_path = file_path
    else:
        pdf_path = file_path.with_suffix(".pdf")
        if not pdf_path.exists():
            return None

    output_path = artifact_dir / "screenshots" / (file_path.stem + "_p1.png")
    return screenshot_pdf_page(pdf_path, output_path)
