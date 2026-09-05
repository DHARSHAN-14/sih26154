"""
validation/citation.py — Check 1: every fact_id in every claim exists in the
locked SoT and the lock_hash matches what generation was given.
Cheap, deterministic, catches the entire class of invented-citation failures.
"""
from __future__ import annotations
from app.core.schemas import GeneratedOutput, SourceOfTruth
from app.core.errors import ContractViolationError
from app.core.hashing import verify


def check(output: GeneratedOutput, sot: SourceOfTruth) -> list[str]:
    """
    Return list of error messages.  Empty = pass.
    Hard fail: missing fact_id or hash mismatch.
    """
    errors: list[str] = []

    # Hash must match
    if sot.lock_hash and output.lock_hash != sot.lock_hash:
        errors.append(
            f"Lock hash mismatch: generation used {output.lock_hash!r} "            f"but SoT is {sot.lock_hash!r}"
        )
        return errors   # no point checking claims against wrong SoT

    known_ids = {f.fact_id for f in sot.facts}
    for section in output.sections:
        for claim in section.claims:
            for fid in claim.fact_ids:
                if fid not in known_ids:
                    errors.append(
                        f"Claim {claim.claim_id!r} cites unknown fact {fid!r}"
                    )
    return errors
