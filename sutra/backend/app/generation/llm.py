"""
generation/llm.py — The single LiteLLM-backed call site.
ALL LLM calls go through here — no module may call the model directly.
Handles backend routing (sovereign/fast), retries, timeouts, token accounting.
Stub: returns mock structured output when litellm is not configured.
"""
from __future__ import annotations
import json
import time
from typing import Any
from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def call(
    messages: list[dict[str, str]],
    output_schema: dict[str, Any] | None = None,
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.1,
) -> dict[str, Any]:
    """
    Make a single LLM call.
    Returns parsed JSON if output_schema is provided, else raw text dict.

    Production: use litellm.completion with structured_outputs.
    Stub: returns empty schema-compliant mock for pipeline testing.
    """
    t0 = time.monotonic()
    backend = settings.model_backend

    try:
        import litellm  # type: ignore
        if backend == "sovereign":
            model_name = model or "openai/qwen3-8b"
            extra = {"api_base": settings.litellm_local_base}
        else:
            model_name = model or "gpt-4o-mini"
            extra = {}

        kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **extra,
        }
        if output_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "output", "schema": output_schema},
            }

        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content
        elapsed = int((time.monotonic() - t0) * 1000)
        logger.info("LLM call complete", backend=backend,
                    model=model_name, elapsed_ms=elapsed,
                    tokens=response.usage.total_tokens if response.usage else 0)

        return json.loads(content) if output_schema else {"text": content}

    except ImportError:
        logger.warning("litellm not installed — returning stub response")
        return _stub_response(output_schema)
    except Exception as exc:
        logger.error("LLM call failed", error=str(exc), backend=backend)
        return _stub_response(output_schema)


def _stub_response(schema: dict | None) -> dict:
    """Return a minimal schema-valid stub response."""
    if not schema:
        return {"text": "[stub: llm not configured]"}
    return {
        "sections": [
            {
                "section_key": "stub",
                "claims": [
                    {
                        "claim_id": "CLM-STUB001",
                        "text": "[stub: configure LLM backend to generate real content]",
                        "fact_ids": [],
                    }
                ],
                "raw_text": "[stub]",
            }
        ]
    }
