"""
api/routes_admin.py — Admin: model toggle, full health, eval trigger.
"""
from __future__ import annotations
from fastapi import APIRouter
from app.deps import SettingsDep
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/status", summary="Detailed system status")
async def system_status(settings: SettingsDep) -> dict:
    return {
        "model_backend": settings.model_backend,
        "enable_kg": settings.enable_kg,
        "enable_route_b": settings.enable_route_b,
        "demo_mode": settings.demo_mode,
        "artifact_dir": settings.artifact_dir,
        "qdrant_host": settings.qdrant_host,
        "qdrant_port": settings.qdrant_port,
        "entailment_threshold": settings.entailment_threshold,
        "max_repair_attempts": settings.max_repair_attempts,
    }


@router.post("/model-backend", summary="Toggle model backend")
async def set_model_backend(backend: str, settings: SettingsDep) -> dict:
    if backend not in ("sovereign", "fast"):
        return {"error": "backend must be 'sovereign' or 'fast'"}
    # In production, update the running config; for now, log and ack.
    logger.info("Model backend toggle requested", backend=backend)
    return {"model_backend": backend, "note": "restart required to apply"}
