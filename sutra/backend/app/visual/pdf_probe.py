"""
visual/pdf_probe.py — PyMuPDF layout extraction after LibreOffice conversion.
Extracts: page count, text block heights, font sizes, overflow indicators.
This is the ground-truth check (post-render).
"""
from __future__ import annotations
import pathlib
from app.visual.rules import MIN_FONT_SIZE_PT
from app.core.logging import get_logger

logger = get_logger(__name__)


def probe(pdf_path: pathlib.Path) -> dict:
    """
    Extract layout info from a PDF file.
    Returns a dict with page_count, font_violations, overflow_indicators.
    """
    result = {
        "page_count": 0,
        "font_violations": [],
        "overflow_indicators": [],
    }

    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed — PDF probe skipped. "
                       "Install with: pip install pymupdf")
        return result

    try:
        doc = fitz.open(str(pdf_path))
        result["page_count"] = len(doc)

        for page_num, page in enumerate(doc, 1):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") != 0:  # text block
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font_size = span.get("size", 12)
                        if font_size < MIN_FONT_SIZE_PT:
                            result["font_violations"].append(
                                f"Page {page_num}: font size {font_size:.1f}pt "
                                f"below minimum {MIN_FONT_SIZE_PT}pt"
                            )

                # Check if text extends beyond page bounds
                bbox = block.get("bbox", [])
                if bbox and len(bbox) == 4:
                    page_rect = page.rect
                    if bbox[3] > page_rect.height + 5:  # 5pt tolerance
                        result["overflow_indicators"].append(
                            f"Page {page_num}: text block overflows page bottom"
                        )
        doc.close()
    except Exception as exc:
        logger.warning("PDF probe failed", error=str(exc))

    return result
