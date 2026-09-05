from __future__ import annotations
import uuid


def generate_fact_id(index: int) -> str:
    """
    Generate a stable, zero-padded, sortable fact ID.

    Example: generate_fact_id(14) -> 'F-014'

    IDs are deterministic per index so the version diff and provenance
    links remain stable across re-runs of the same source.
    """
    return f"F-{index:03d}"


def generate_claim_id() -> str:
    """Generate a unique claim ID. Example: CLM-4A2B3C7D8E9F"""
    return f"CLM-{uuid.uuid4().hex[:12].upper()}"


def generate_chunk_id() -> str:
    """Generate a unique chunk ID. Example: CHK-4A2B3C7D8E9F"""
    return f"CHK-{uuid.uuid4().hex[:12].upper()}"


def generate_doc_id() -> str:
    """Generate a unique document ID. Example: DOC-4A2B3C7D8E9F"""
    return f"DOC-{uuid.uuid4().hex[:12].upper()}"


def generate_job_id() -> str:
    """Generate a unique pipeline job ID. Example: JOB-4A2B3C7D8E9F"""
    return f"JOB-{uuid.uuid4().hex[:12].upper()}"


def generate_session_id() -> str:
    """Generate a unique operator session ID (full UUID)."""
    return str(uuid.uuid4())
