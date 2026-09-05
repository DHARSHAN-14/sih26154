from __future__ import annotations
import hashlib
import json
from app.core.schemas import SourceOfTruth


def compute_lock_hash(sot: SourceOfTruth) -> str:
    """SHA-256 over sorted (fact_id|canonical_text) pairs. Deterministic."""
    entries = sorted(
        fact.fact_id + "|" + fact.canonical_text
        for fact in sot.facts
    )
    payload = json.dumps(entries, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify(sot: SourceOfTruth, expected_hash: str) -> bool:
    return compute_lock_hash(sot) == expected_hash


def hash_bytes(data: bytes) -> str:
    """Content-address an uploaded file."""
    return hashlib.sha256(data).hexdigest()
