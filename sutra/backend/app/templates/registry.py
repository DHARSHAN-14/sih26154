"""
templates/registry.py — Loads and validates every YAML in defs/ at startup.
Fails fast: a malformed contract at startup is better than a crash mid-demo.
"""
from __future__ import annotations
import pathlib
from typing import Any
try:
    import yaml
    _YAML = True
except ImportError:
    _YAML = False

from app.templates.contract import TemplateContract
from app.core.logging import get_logger

logger = get_logger(__name__)

_REGISTRY: dict[str, TemplateContract] = {}
_DEFS_DIR = pathlib.Path(__file__).parent / "defs"


def load_all() -> None:
    """Load all YAML contract files. Called at application startup."""
    if not _YAML:
        logger.warning("PyYAML not installed; template registry unavailable")
        return
    if not _DEFS_DIR.exists():
        logger.warning("templates/defs/ not found; no templates loaded")
        return
    for yaml_path in sorted(_DEFS_DIR.glob("*.yaml")):
        try:
            raw: dict[str, Any] = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            contract = TemplateContract.model_validate(raw)
            _REGISTRY[contract.id] = contract
            logger.info("Template loaded", template_id=contract.id,
                        version=contract.version)
        except Exception as exc:
            logger.error("Failed to load template",
                         path=str(yaml_path), error=str(exc))
            raise


def get(template_id: str) -> TemplateContract:
    if template_id not in _REGISTRY:
        raise KeyError(f"Template '{template_id}' not found in registry")
    return _REGISTRY[template_id]


def all_ids() -> list[str]:
    return list(_REGISTRY.keys())


def is_loaded() -> bool:
    return bool(_REGISTRY)
