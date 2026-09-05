"""
sot/lock.py — Source of Truth freeze and hash verification.
After lock(), the SoT is immutable: any further mutation raises SoTAlreadyLockedError.
The lock_hash is what makes 'locked source of truth' a verifiable claim.
"""
from __future__ import annotations
from datetime import datetime
from app.core.schemas import SourceOfTruth
from app.core.hashing import compute_lock_hash
from app.core.errors import SoTAlreadyLockedError, SoTNotLockedError


def lock(sot: SourceOfTruth) -> SourceOfTruth:
    """
    Freeze the SoT: compute and set lock_hash, set is_locked=True.
    Returns the same object (mutated).
    Raises SoTAlreadyLockedError if called twice.
    """
    if sot.is_locked:
        raise SoTAlreadyLockedError()
    sot.lock_hash = compute_lock_hash(sot)
    sot.locked_at = datetime.utcnow()
    sot.is_locked = True
    return sot


def assert_locked(sot: SourceOfTruth) -> None:
    """Raise SoTNotLockedError if the SoT has not been locked."""
    if not sot.is_locked or not sot.lock_hash:
        raise SoTNotLockedError()


def verify_hash(sot: SourceOfTruth, expected: str) -> bool:
    """Return True if the SoT still matches the recorded lock hash."""
    from app.core.hashing import verify
    return verify(sot, expected)
