"""
db/models.py — SQLAlchemy 2.0 ORM tables for sutra.
Every table carries session_id for isolation.  No JSON blobs for queryable
columns — facts are stored in their own table for sorting/filtering.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, SessionMixin


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    artifact_dir: Mapped[str] = mapped_column(String(512))
    qdrant_collection: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sources: Mapped[list["SourceDocument"]] = relationship(back_populates="session")
    jobs: Mapped[list["Job"]] = relationship(back_populates="session")


class SourceDocument(Base, TimestampMixin, SessionMixin):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128))
    file_hash: Mapped[str] = mapped_column(String(64))
    file_path: Mapped[str] = mapped_column(String(512))
    parsed_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="sources")


class SotVersion(Base, TimestampMixin, SessionMixin):
    __tablename__ = "sot_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    lock_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    graph_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fact_count: Mapped[int] = mapped_column(Integer, default=0)

    facts: Mapped[list["FactRecord"]] = relationship(back_populates="sot")


class FactRecord(Base, TimestampMixin, SessionMixin):
    __tablename__ = "facts"

    db_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(32), index=True)   # "F-014"
    sot_id: Mapped[str] = mapped_column(String(36), ForeignKey("sot_versions.id"))
    fact_type: Mapped[str] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(512))
    predicate: Mapped[str] = mapped_column(String(256))
    object_val: Mapped[str] = mapped_column(String(1024))
    canonical_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    sensitivity: Mapped[str] = mapped_column(String(32), default="internal")
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    contradicts: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    depends_on: Mapped[str] = mapped_column(Text, default="[]")   # JSON list
    provenance_json: Mapped[str] = mapped_column(Text, default="[]")

    sot: Mapped["SotVersion"] = relationship(back_populates="facts")


class Job(Base, TimestampMixin, SessionMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sot_id: Mapped[str] = mapped_column(String(36), ForeignKey("sot_versions.id"))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    formats: Mapped[str] = mapped_column(Text, default="[]")      # JSON list
    params_json: Mapped[str] = mapped_column(Text, default="{}")  # operator params
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="jobs")
    outputs: Mapped[list["OutputArtifact"]] = relationship(back_populates="job")
    events: Mapped[list["StageEventRecord"]] = relationship(back_populates="job")


class OutputArtifact(Base, TimestampMixin, SessionMixin):
    __tablename__ = "output_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    output_format: Mapped[str] = mapped_column(String(64))
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    validation_verdict: Mapped[str] = mapped_column(String(32), default="pending")
    validation_json: Mapped[str] = mapped_column(Text, default="{}")
    visual_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    generated_content_json: Mapped[str] = mapped_column(Text, default="{}")
    lock_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="outputs")


class StageEventRecord(Base, TimestampMixin, SessionMixin):
    __tablename__ = "stage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"))
    stage: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text, default="")
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0)
    counters_json: Mapped[str] = mapped_column(Text, default="{}")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    job: Mapped["Job"] = relationship(back_populates="events")


class SecurityDetection(Base, TimestampMixin, SessionMixin):
    __tablename__ = "security_detections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(36))
    pattern_class: Mapped[str] = mapped_column(String(64))
    span: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locator: Mapped[str] = mapped_column(String(128), default="")
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    neutralized: Mapped[bool] = mapped_column(Boolean, default=True)


class ReviewItem(Base, TimestampMixin, SessionMixin):
    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    output_id: Mapped[str] = mapped_column(String(36), ForeignKey("output_artifacts.id"))
    failure_type: Mapped[str] = mapped_column(String(64))
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
