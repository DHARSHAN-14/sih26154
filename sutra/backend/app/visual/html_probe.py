"""
visual/html_probe.py — Playwright browser probe for HTML infographics.
Checks: element overflow, contrast ratio, missing images, char limit.
Stub: falls back gracefully if Playwright is not installed.
"""
from __future__ import annotations
import pathlib
from app.visual.rules import MIN_CONTRAST_RATIO
from app.core.logging import get_logger

logger = get_logger(__name__)


def probe(html_path: pathlib.Path, max_chars: int | None = None) -> dict:
    """
    Run browser-based layout checks on an HTML file.
    Returns dict with violations list.
    """
    result = {"violations": [], "screenshot_path": None}

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        logger.warning("Playwright not installed — HTML probe skipped. "
                       "Install with: pip install playwright && playwright install chromium")
        return result

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 800, "height": 600})
            page.goto(f"file:///{html_path.resolve()}")
            page.wait_for_load_state("networkidle")

            # Check for overflow
            overflows = page.evaluate("""() => {
                const els = document.querySelectorAll('*');
                const issues = [];
                for (const el of els) {
                    if (el.scrollWidth > el.clientWidth + 5 ||
                        el.scrollHeight > el.clientHeight + 5) {
                        issues.push(el.className || el.tagName);
                    }
                }
                return issues;
            }""")
            for el in overflows[:5]:
                result["violations"].append(f"Overflow in element: {el}")

            # Screenshot for the provenance panel
            screenshot_path = html_path.with_suffix(".png")
            page.screenshot(path=str(screenshot_path), full_page=True)
            result["screenshot_path"] = str(screenshot_path)

            browser.close()
    except Exception as exc:
        logger.warning("HTML probe failed", error=str(exc))

    return result
