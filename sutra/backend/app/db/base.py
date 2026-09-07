from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 declarative base for all Sutra ORM models.
    Import this base in every model module; never create a second base.
    """
    pass


class TimestampMixin:
    """
    Adds created_at / updated_at audit columns to any model.

    created_at: set once by the database on INSERT.
    updated_at: updated by the database on every UPDATE.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SessionMixin:
    """
    Adds a session_id column to any model for per-operator isolation.

    The security/isolation.py guard rejects any DB query that does not
    include a session_id filter, enforcing the concurrent-operator
    isolation guarantee described in the architecture.
    """
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )
