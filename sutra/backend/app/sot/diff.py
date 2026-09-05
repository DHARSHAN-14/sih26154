"""
sot/diff.py — Compare two SoT versions fact by fact.
Returns added / removed / changed / unchanged fact sets.
Maps changed/removed facts to previously-generated outputs (stale detection).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from app.core.schemas import SourceOfTruth, Fact


@dataclass
class SotDiff:
    added: list[Fact] = field(default_factory=list)
    removed: list[Fact] = field(default_factory=list)
    changed: list[tuple[Fact, Fact]] = field(default_factory=list)  # (v1, v2)
    unchanged: list[Fact] = field(default_factory=list)

    @property
    def changed_ids(self) -> set[str]:
        return {v2.fact_id for _, v2 in self.changed}

    @property
    def removed_ids(self) -> set[str]:
        return {f.fact_id for f in self.removed}

    @property
    def stale_fact_ids(self) -> set[str]:
        return self.changed_ids | self.removed_ids


def diff(v1: SourceOfTruth, v2: SourceOfTruth) -> SotDiff:
    """
    Diff two locked SoTs.  Facts matched by fact_id;
    changed = same ID, different canonical_text or object.
    """
    v1_map = {f.fact_id: f for f in v1.facts}
    v2_map = {f.fact_id: f for f in v2.facts}
    result = SotDiff()

    for fid, f2 in v2_map.items():
        if fid not in v1_map:
            result.added.append(f2)
        else:
            f1 = v1_map[fid]
            if f1.canonical_text != f2.canonical_text or f1.object != f2.object:
                result.changed.append((f1, f2))
            else:
                result.unchanged.append(f2)

    for fid, f1 in v1_map.items():
        if fid not in v2_map:
            result.removed.append(f1)

    return result


def stale_outputs(
    sot_diff: SotDiff,
    output_citations: dict[str, set[str]],  # output_id -> set of fact_ids
) -> list[str]:
    """Return output_ids that cited at least one stale fact."""
    stale = sot_diff.stale_fact_ids
    return [oid for oid, fids in output_citations.items()
            if fids & stale]
