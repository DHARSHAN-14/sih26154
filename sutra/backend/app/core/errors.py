from __future__ import annotations
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


# ─── Base ─────────────────────────────────────────────────────────────────────

class SutraError(Exception):
    """Base exception for all domain errors in the Sutra platform."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str = "An unexpected error occurred.", **kwargs: Any) -> None:
        self.detail = detail
        self.extra = kwargs
        super().__init__(detail)


# ─── Source of Truth ──────────────────────────────────────────────────────────

class SoTNotLockedError(SutraError):
    """Raised when generation is attempted against an unlocked Source of Truth."""
    status_code = 409
    error_code = "SOT_NOT_LOCKED"

    def __init__(
        self,
        detail: str = "Source of Truth must be locked before generating outputs.",
    ) -> None:
        super().__init__(detail)


class SoTAlreadyLockedError(SutraError):
    """Raised when a mutation is attempted on a frozen Source of Truth."""
    status_code = 409
    error_code = "SOT_ALREADY_LOCKED"

    def __init__(
        self,
        detail: str = "Source of Truth is already locked and cannot be modified.",
    ) -> None:
        super().__init__(detail)


# ─── Ingestion ────────────────────────────────────────────────────────────────

class UnsupportedSourceTypeError(SutraError):
    """Raised when an uploaded file type is not in the supported MIME allow-list."""
    status_code = 415
    error_code = "UNSUPPORTED_SOURCE_TYPE"

    def __init__(self, detail: str = "The uploaded file type is not supported.") -> None:
        super().__init__(detail)


class ExtractionFailedError(SutraError):
    """Raised when document parsing or fact extraction fails unrecoverably."""
    status_code = 422
    error_code = "EXTRACTION_FAILED"

    def __init__(self, detail: str = "Failed to extract content from the source.") -> None:
        super().__init__(detail)


# ─── Generation & Validation ──────────────────────────────────────────────────

class ContractViolationError(SutraError):
    """Raised when generated output violates the template content or layout contract."""
    status_code = 422
    error_code = "CONTRACT_VIOLATION"

    def __init__(
        self,
        detail: str = "Output violates the template content or layout contract.",
    ) -> None:
        super().__init__(detail)


class RenderFailedError(SutraError):
    """Raised when the renderer cannot produce a valid artifact."""
    status_code = 500
    error_code = "RENDER_FAILED"

    def __init__(self, detail: str = "Failed to render the output artifact.") -> None:
        super().__init__(detail)


class ValidationExhaustedError(SutraError):
    """Raised when MAX_REPAIR_ATTEMPTS is reached without a passing validation."""
    status_code = 422
    error_code = "VALIDATION_EXHAUSTED"

    def __init__(
        self,
        detail: str = "Maximum repair attempts exhausted. Output requires human review.",
    ) -> None:
        super().__init__(detail)


# ─── Security ─────────────────────────────────────────────────────────────────

class InjectionDetectedError(SutraError):
    """Raised when the sanitizer finds potential prompt-injection in uploaded content."""
    status_code = 400
    error_code = "INJECTION_DETECTED"

    def __init__(
        self,
        detail: str = "Potential prompt injection detected in the source document.",
    ) -> None:
        super().__init__(detail)


# ─── Session / Job ────────────────────────────────────────────────────────────

class SessionNotFoundError(SutraError):
    """Raised when a session_id does not exist."""
    status_code = 404
    error_code = "SESSION_NOT_FOUND"

    def __init__(self, session_id: str = "") -> None:
        detail = f"Session '{session_id}' not found." if session_id else "Session not found."
        super().__init__(detail)


class JobNotFoundError(SutraError):
    """Raised when a job_id does not exist."""
    status_code = 404
    error_code = "JOB_NOT_FOUND"

    def __init__(self, job_id: str = "") -> None:
        detail = f"Job '{job_id}' not found." if job_id else "Job not found."
        super().__init__(detail)


# ─── FastAPI exception handlers ───────────────────────────────────────────────

async def sutra_error_handler(request: Request, exc: SutraError) -> JSONResponse:
    """Maps SutraError subclasses to structured JSON error responses."""
    logger.warning(
        "Application error",
        error_code=exc.error_code,
        detail=exc.detail,
        path=str(request.url.path),
        method=request.method,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "detail": exc.detail,
            "path": str(request.url.path),
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions — preserve HTTPException status codes."""
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "detail": exc.detail,
                "path": str(request.url.path),
            },
        )
    logger.exception(
        "Unhandled exception",
        path=str(request.url.path),
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "detail": str(exc) or "An unexpected internal error occurred.",
            "path": str(request.url.path),
        },
    )
