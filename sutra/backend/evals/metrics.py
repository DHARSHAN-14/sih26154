"""
evals/metrics.py — Evaluation metrics for the Sutra platform.
Computes:
- Unsupported claim rate (%)
- Citation validity (%)
- Contradiction recall (%)
- Injection neutralization rate (%)
- Visual / layout pass rate (%)
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EvalMetrics:
    total_claims: int = 0
    unsupported_claims: int = 0
    total_citations: int = 0
    valid_citations: int = 0
    total_injections: int = 0
    neutralized_injections: int = 0
    total_contradictions: int = 0
    detected_contradictions: int = 0
    total_rendered_pages: int = 0
    layout_violations: int = 0
    auto_repaired_outputs: int = 0
    escalated_to_review: int = 0

    @property
    def unsupported_claim_rate(self) -> float:
        if self.total_claims == 0:
            return 0.0
        return (self.unsupported_claims / self.total_claims) * 100.0

    @property
    def citation_validity_rate(self) -> float:
        if self.total_citations == 0:
            return 100.0
        return (self.valid_citations / self.total_citations) * 100.0

    @property
    def injection_catch_rate(self) -> float:
        if self.total_injections == 0:
            return 100.0
        return (self.neutralized_injections / self.total_injections) * 100.0

    @property
    def contradiction_recall(self) -> float:
        if self.total_contradictions == 0:
            return 100.0
        return (self.detected_contradictions / self.total_contradictions) * 100.0

    @property
    def layout_pass_rate(self) -> float:
        if self.total_rendered_pages == 0:
            return 100.0
        passes = max(0, self.total_rendered_pages - self.layout_violations)
        return (passes / self.total_rendered_pages) * 100.0
