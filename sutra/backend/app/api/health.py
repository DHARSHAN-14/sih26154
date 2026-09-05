from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.deps import DbDep, SettingsDep

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    summary="Liveness check",
    description="Returns 200 immediately. Use this to confirm the process is alive.",
)
async def health_check(settings: SettingsDep) -> dict[str, Any]:
    """
    Liveness probe.

    Does not touch the database — if the HTTP server is responding, this
    returns 200. Kubernetes / Docker HEALTHCHECK can use this endpoint.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description=(
        "Returns 200 when all dependencies (database, etc.) are reachable. "
        "Returns 503 with a checks object describing which component failed."
    ),
)
async def readiness_check(
    settings: SettingsDep,
    db: DbDep,
) -> JSONResponse:
    """
    Readiness probe.

    Checks every critical dependency and returns a structured report.
    A 503 body tells the operator exactly which component is unhealthy.
    """
    checks: dict[str, Any] = {}
    overall_ok = True

    # ── Database ─────────────────────────────────────────────────────────────
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok", "detail": "PostgreSQL reachable"}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        overall_ok = False
        logger.warning("Database readiness check failed", error=str(exc))

    status = "ready" if overall_ok else "degraded"
    http_status = 200 if overall_ok else 503

    return JSONResponse(
        status_code=http_status,
        content={
            "status": status,
            "service": settings.app_name,
            "version": settings.app_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        },
    )
