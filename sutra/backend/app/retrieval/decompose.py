"""
retrieval/decompose.py — Query decomposition for multi-hop retrieval (Route B).
Splits a generation request or content plan into targeted, section-specific sub-queries.
Each sub-query is independently embedded, retrieved via hybrid search, and reranked.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from app.core.schemas import SectionPlan


@dataclass
class SubQuery:
    section_key: str
    query_text: str
    preferred_fact_types: list[str] = field(default_factory=list)
    top_k: int = 10


_SECTION_TEMPLATES: dict[str, tuple[str, list[str]]] = {
    "key_findings": (
        "critical incidents key findings threat actor attribution summary overview",
        ["claim", "event", "organization"]
    ),
    "executive_summary": (
        "executive summary strategic briefing situation overview key findings operational impact",
        ["claim", "event", "numeric"]
    ),
    "affected_systems": (
        "affected systems infrastructure supervisory gateway hardware software versions nodes compromised",
        ["technical", "numeric", "organization"]
    ),
    "technical_threat_vectors": (
        "vulnerability CVE exploit remote code execution c2 command control port ip protocol",
        ["technical", "numeric"]
    ),
    "threat_vector": (
        "threat vectors intrusion mechanism CVE remote exploit malware communication",
        ["technical"]
    ),
    "recommended_actions": (
        "recommended mitigation actions patch isolation firewall block containment directives",
        ["claim", "action"]
    ),
    "mandated_response": (
        "mandatory containment actions patch emergency release isolate perimeter",
        ["claim", "action"]
    ),
    "indicators_of_compromise": (
        "indicators of compromise hashes IP addresses domains c2 beacons port telemetry",
        ["technical", "numeric"]
    ),
    "impact_assessment": (
        "impact operational consequence severity rating CVSS exfiltrated data nodes",
        ["numeric", "claim"]
    ),
    "situational_context": (
        "situational context background timeline national telemetry grid monitoring",
        ["event", "location", "date"]
    ),
    "tactical_defense": (
        "tactical defense mitigation instructions patch deployment network segment isolation",
        ["claim", "action"]
    ),
    "agenda": (
        "briefing agenda topics threat landscape technical exposure containment",
        ["claim"]
    ),
}


def decompose(
    sections: list[SectionPlan],
    sot_context: str = "",
    target_format: str = "",
) -> list[SubQuery]:
    """
    Decompose content sections into high-recall, semantic retrieval queries.
    Incorporates critical entities from sot_context (e.g. CVEs, actor names).
    """
    # Extract notable entities from sot_context if provided
    context_tokens = []
    if sot_context:
        cves = re.findall(r"cve-\d{4}-\d+", sot_context.lower())
        context_tokens.extend(cves)
        for actor in ["cyclone", "apt", "lazarus", "cobalt strike", "ntro"]:
            if actor in sot_context.lower():
                context_tokens.append(actor)
    context_suffix = f" ({' '.join(context_tokens[:3])})" if context_tokens else ""

    queries: list[SubQuery] = []
    for section in sections:
        key = section.section_key.lower().replace("-", "_")

        # Check pre-defined mapping
        template_match = _SECTION_TEMPLATES.get(key)
        if not template_match:
            for k_prefix, val in _SECTION_TEMPLATES.items():
                if k_prefix in key or key in k_prefix:
                    template_match = val
                    break

        if template_match:
            base_q, fact_types = template_match
            query_text = f"{base_q}{context_suffix}"
        else:
            human_name = key.replace("_", " ")
            query_text = f"information and facts regarding {human_name}{context_suffix}"
            fact_types = []

        if target_format:
            query_text += f" for {target_format}"

        top_k = (section.max_claims * 3) if getattr(section, "max_claims", None) else 10
        queries.append(SubQuery(
            section_key=section.section_key,
            query_text=query_text.strip(),
            preferred_fact_types=fact_types,
            top_k=top_k,
        ))

    return queries
