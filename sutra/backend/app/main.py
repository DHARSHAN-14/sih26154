"""
app/main.py — Sutra API entry point.
Wires all routers, middleware, exception handlers, and lifespan.
"""
from __future__ import annotations
import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.errors import SutraError, sutra_error_handler, generic_error_handler
from app.api import health
from app.api import (
    routes_session, routes_sot, routes_jobs,
    routes_stream, routes_outputs, routes_admin,
)
from app.db.session import init_db
from app.templates.registry import load_all as load_templates

settings = get_settings()

configure_logging(
    log_level=settings.log_level,
    log_format="console" if settings.debug else settings.log_format,
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "Starting Sutra API",
        version=settings.app_version,
        environment=settings.app_env,
        model_backend=settings.model_backend,
        demo_mode=settings.demo_mode,
    )

    # Load template contracts
    try:
        load_templates()
        logger.info("Template registry loaded")
    except Exception as exc:
        logger.warning("Template registry load failed", error=str(exc))

    # Init database
    try:
        await init_db()
        logger.info("Database ready")
    except Exception as exc:
        logger.warning("Database init failed — continuing", error=str(exc))

    logger.info(
        "Sutra API ready",
        host=settings.api_host,
        port=settings.api_port,
        docs=f"http://{settings.api_host}:{settings.api_port}/docs",
        health=f"http://{settings.api_host}:{settings.api_port}{settings.api_prefix}/health",
    )

    yield

    logger.info("Sutra API shutting down")


app = FastAPI(
    title="Sutra API",
    description=(
        "**SIH26154** — Gen AI Platform for Automated Content Transformation\n\n"
        "One locked, verified source of truth → multiple consistent, validated output formats.\n\n"
        "**Outputs:** Advisory · Executive Summary · Presentation · "
        "LinkedIn · Twitter/X · Infographic · Video Package\n\n"
        "Every generated claim traces back to the exact source sentence."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_exception_handler(SutraError, sutra_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# ── Routers ──────────────────────────────────────────────────────────────────
PFX = settings.api_prefix

app.include_router(health.router,            prefix=PFX)
app.include_router(routes_session.router,    prefix=PFX)
app.include_router(routes_sot.router,        prefix=PFX)
app.include_router(routes_jobs.router,       prefix=PFX)
app.include_router(routes_stream.router,     prefix=PFX)
app.include_router(routes_outputs.router,    prefix=PFX)
app.include_router(routes_admin.router,      prefix=PFX)


@app.get("/", tags=["Root"], summary="API root — service info")
async def root() -> dict:
    from app.templates.registry import all_ids, is_loaded
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "description": "Gen AI Platform for Automated Content Transformation",
        "environment": settings.app_env,
        "docs": "/docs",
        "health": f"{PFX}/health",
        "ready": f"{PFX}/health/ready",
        "templates_loaded": is_loaded(),
        "available_formats": all_ids() if is_loaded() else [],
    }
