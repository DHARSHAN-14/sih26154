from __future__ import annotations
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.core.logging import get_logger
from app.db.base import Base

logger = get_logger(__name__)
_settings = get_settings()

# ─── Engine ───────────────────────────────────────────────────────────────────

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.database_echo,
    pool_size=_settings.database_pool_size,
    max_overflow=_settings.database_max_overflow,
    future=True,
    pool_pre_ping=True,    # validate connections before use
)

# ─── Session factory ──────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ─── FastAPI dependency ───────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session per request.

    Commits on clean exit; rolls back on any exception.
    Used as a FastAPI Depends() in route handlers.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─── Startup helper ───────────────────────────────────────────────────────────

async def init_db() -> None:
    """
    Create all tables defined via Base.metadata on application startup.

    This is development-mode convenience only.
    Production migrations are managed by Alembic.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized (create_all)")
