from __future__ import annotations
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for the Sutra backend.
    All values are read from environment variables or the .env file.
    A number lives here if a judge could ask 'why that value?' — nowhere else.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "sutra"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True

    # ── API ───────────────────────────────────────────────────────────────────
    api_prefix: str = "/api"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://sutra:sutra@localhost:5432/sutra_db"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ── LLM / Model Backend ───────────────────────────────────────────────────
    model_backend: str = "fast"          # "sovereign" | "fast"
    litellm_local_base: str = "http://localhost:8001"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # ── RAG / Retrieval ───────────────────────────────────────────────────────
    retrieval_token_threshold: int = 25000
    enable_route_b: bool = True
    enable_kg: bool = True

    # ── Vector Store ──────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_prefix: str = "sutra"

    # ── Confidence Weights ────────────────────────────────────────────────────
    confidence_w1_extraction_agreement: float = 0.35
    confidence_w2_source_quality: float = 0.30
    confidence_w3_support_count: float = 0.20
    confidence_w4_contradiction_penalty: float = 0.15

    # ── Confidence Bands ──────────────────────────────────────────────────────
    confidence_exclude_below: float = 0.5
    confidence_caveat_below: float = 0.75

    # ── Validation ────────────────────────────────────────────────────────────
    entailment_threshold: float = 0.7
    max_repair_attempts: int = 2

    # ── Feature Flags ─────────────────────────────────────────────────────────
    enable_video_package: bool = True
    demo_mode: bool = False

    # ── Storage ───────────────────────────────────────────────────────────────
    artifact_dir: str = "./data/artifacts"
    max_upload_size_mb: int = 100

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "console"    # "console" | "json"


@lru_cache()
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()
