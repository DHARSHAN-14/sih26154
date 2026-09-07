from __future__ import annotations
import logging
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """
    Configure structlog for the application.

    In 'console' mode (development): coloured, human-readable output via Rich.
    In 'json' mode (production):     structured JSON lines for log aggregators.
    """
    level_int: int = getattr(logging, log_level.upper(), logging.INFO)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Standard library logging must be configured FIRST so structlog's
    # stdlib integration has a real Logger with a .name attribute.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level_int,
        force=True,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "console":
        processors: list[Any] = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        # Use stdlib integration so loggers have a proper .name attribute.
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger backed by stdlib logging."""
    return structlog.get_logger(name)
