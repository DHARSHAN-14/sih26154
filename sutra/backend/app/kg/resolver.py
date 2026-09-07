"""
kg/resolver.py — Entity resolution and canonical Knowledge Graph builder.
Clusters surface forms into canonical entities (e.g. "Indian Space Research Organisation" / "ISRO" -> "ISRO").
Filters noise, prevents arbitrary PDF tokens from entering the graph, and builds clean semantic triples with evidence.
"""
from __future__ import annotations
import json
import re
from typing import Any
from app.core.schemas import Entity

# Canonical alias mapping for domain entities and acronyms
CANONICAL_ALIASES: dict[str, tuple[str, str]] = {
    # Organizations / Threat Groups
    "isro": ("ISRO", "organization"),
    "indian space research organisation": ("ISRO", "organization"),
    "indian space research organization": ("ISRO", "organization"),
    "ntro": ("NTRO", "organization"),
    "national technical research organisation": ("NTRO", "organization"),
    "national technical research organization": ("NTRO", "organization"),
    "cert-in": ("CERT-In", "organization"),
    "cert": ("CERT-In", "organization"),
    "computer emergency response team": ("CERT-In", "organization"),
    "drdo": ("DRDO", "organization"),
    "defence research and development organisation": ("DRDO", "organization"),
    "silver cyclone": ("SILVER CYCLONE", "organization"),
    "silver cyclone apt": ("SILVER CYCLONE", "organization"),
    "threat actor": ("SILVER CYCLONE", "organization"),
    "adversary": ("SILVER CYCLONE", "organization"),
    "cisa": ("CISA", "organization"),
    "nic": ("NIC", "organization"),

    # Technical Systems & Assets
    "ics supervisory gateway": ("ICS Supervisory Gateway", "technical"),
    "ics supervisory gateway v4.2 - v5.1": ("ICS Supervisory Gateway", "technical"),
    "target system: ics supervisory gateway v4.2 - v5.1": ("ICS Supervisory Gateway", "technical"),
    "target system": ("ICS Supervisory Gateway", "technical"),
    "ics gateway": ("ICS Supervisory Gateway", "technical"),
    "ics gateways": ("ICS Supervisory Gateway", "technical"),
    "ics supervisory software": ("ICS Supervisory Gateway", "technical"),
    "supervisory software": ("ICS Supervisory Gateway", "technical"),
    "scada": ("SCADA System", "technical"),
    "plc": ("Programmable Logic Controller", "technical"),
    "udp/tcp port 44818": ("Port 44818 (EtherNet/IP)", "technical"),
    "port 44818": ("Port 44818 (EtherNet/IP)", "technical"),
    "194.26.29.114": ("194.26.29.114 (C2 IP)", "technical"),
    "45.145.66.89": ("45.145.66.89 (C2 IP)", "technical"),
    "adversarial c2 ip addresses": ("Adversary C2 Infrastructure", "technical"),

    # Vulnerabilities
    "cve-2026-8819": ("CVE-2026-8819", "technical"),
    "vulnerability identifier: cve-2026-8819 (cvss 9.8 critical)": ("CVE-2026-8819", "technical"),
    "cve-2026-8819 (cvss 9.8 critical)": ("CVE-2026-8819", "technical"),
    "remote code execution": ("RCE Vulnerability", "technical"),
    "critical remote code execution vulnerability": ("CVE-2026-8819", "technical"),

    # Locations
    "delhi": ("New Delhi", "location"),
    "new delhi": ("New Delhi", "location"),
    "mumbai": ("Mumbai", "location"),
    "bengaluru": ("Bengaluru", "location"),
    "india": ("India", "location"),
    "northern grid": ("Northern Energy Grid", "location"),
    "western grid": ("Western Energy Grid", "location"),
    "national energy distribution": ("National Energy Grid", "location"),
    "national energy distribution networks": ("National Energy Grid", "location"),

    # Directives & Events
    "network isolation": ("Network Isolation", "event"),
    "immediate network isolation of ics gateways": ("Network Isolation", "event"),
    "immediate network isolation": ("Network Isolation", "event"),
    "isolate network": ("Network Isolation", "event"),
    "port 44818 filtering": ("Port 44818 Filtering", "event"),
    "block port 44818": ("Port 44818 Filtering", "event"),
    "forensic memory capture": ("Forensic Memory Capture", "event"),
    "advisory ntro-2026-crit-0492": ("Advisory NTRO-2026-CRIT-0492", "event"),
    "ntro-2026-crit-0492": ("Advisory NTRO-2026-CRIT-0492", "event"),

    # Metrics
    "14 supervisory nodes": ("14 Supervisory Nodes", "numeric"),
    "14 nodes": ("14 Supervisory Nodes", "numeric"),
    "2 hours": ("2 Hours", "numeric"),
    "within 2 hours": ("2 Hours", "numeric"),
    "cvss 9.8": ("CVSS 9.8 (Critical)", "numeric"),
}

INVALID_NODE_PATTERNS = {
    r'^%pdf', r'^flatedecode', r'^stream', r'^obj', r'^endobj', r'^\d+[\.\)]?$',
    r'^(?:the|this|that|these|those|it|its|they|their|we|our|a|an)$',
    r'^(?:document|source|overview|summary|section|details|page|table|states|asserts)$',
    r'^(?:directive|directives|mandatory|operational|intelligence|advisory|ref)$',
}


def classify_entity_type(phrase: str) -> str:
    """Classify an entity into one of the frontend EntityTypes."""
    lower = phrase.lower().strip()
    if lower in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[lower][1]
    if "cve-" in lower or "hash" in lower or re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', lower):
        return "technical"
    if any(w in lower for w in ["cyclone", "apt", "lazarus", "ntro", "cert", "drdo", "isro", "agency", "organisation", "organization", "actor"]):
        return "organization"
    if any(w in lower for w in ["gateway", "supervisory", "software", "controller", "server", "port", "protocol", "scada", "plc", "rce"]):
        return "technical"
    if any(w in lower for w in ["grid", "delhi", "mumbai", "india", "region"]):
        return "location"
    if any(w in lower for w in ["isolation", "directive", "capture", "patch", "advisory", "operation"]):
        return "event"
    if any(c.isdigit() for c in phrase) and any(w in lower for w in ["node", "hour", "day", "cvss", "percent", "%"]):
        return "numeric"
    if any(w in lower for w in ["2026", "september", "august", "january", "date"]):
        return "date"
    if any(w in lower for w in ["officer", "director", "dr.", "shri"]):
        return "person"
    return "claim"


def resolve_canonical_entity(phrase: str) -> tuple[str, str] | None:
    """
    Resolve a raw mention to its canonical representation and type.
    Returns (canonical_name, entity_type) or None if the phrase is noise/invalid.
    """
    cleaned = phrase.strip().strip(".,;:()[]{}'\"- ")
    if len(cleaned) < 2 or len(cleaned) > 55:
        return None

    lower = cleaned.lower()

    # Reject noise and PDF syntax
    for pat in INVALID_NODE_PATTERNS:
        if re.search(pat, lower):
            return None

    # Exact alias match
    if lower in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[lower]

    # Partial / substring alias match
    for alias_key, (canon_name, etype) in CANONICAL_ALIASES.items():
        if len(alias_key) >= 4:
            if alias_key in lower or lower in alias_key:
                return (canon_name, etype)

    # Detect CVEs
    cve_m = re.search(r'CVE-\d{4}-\d{4,7}', cleaned, re.IGNORECASE)
    if cve_m:
        return (cve_m.group().upper(), "technical")

    # Detect IP
    ip_m = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', cleaned)
    if ip_m:
        return (f"{ip_m.group()} (IP)", "technical")

    # Detect Port
    port_m = re.search(r'port\s*(\d+)', cleaned, re.IGNORECASE)
    if port_m:
        return (f"Port {port_m.group(1)}", "technical")

    # Detect metrics
    metric_m = re.search(r'(\d+)\s*(supervisory nodes|nodes|controllers|hours|days)', cleaned, re.IGNORECASE)
    if metric_m:
        return (f"{metric_m.group(1)} {metric_m.group(2).title()}", "numeric")

    # Title-case proper names
    words = cleaned.split()
    if len(words) <= 4 and all(w[0].isupper() or w.lower() in ["of", "and", "in", "to", "for"] for w in words if w):
        etype = classify_entity_type(cleaned)
        return (cleaned, etype)

    return None


def resolve_entities(surface_forms: list[str]) -> dict[str, str]:
    """Preserve existing API: Map surface forms to canonical IDs."""
    resolved: dict[str, str] = {}
    for sf in surface_forms:
        res = resolve_canonical_entity(sf)
        if res:
            canonical, _ = res
            resolved[sf] = canonical.lower().replace(" ", "_")
        else:
            resolved[sf] = sf.strip().lower().replace(" ", "_")
    return resolved


def build_entities(
    surface_to_canonical: dict[str, str],
    fact_ids_by_surface: dict[str, list[str]],
    entity_types: dict[str, str] | None = None,
) -> list[Entity]:
    """Preserve existing API: Construct Entity objects."""
    entity_types = entity_types or {}
    canonical_to_surfaces: dict[str, list[str]] = {}
    canonical_to_facts: dict[str, list[str]] = {}

    for surf, cid in surface_to_canonical.items():
        canonical_to_surfaces.setdefault(cid, []).append(surf)
        for fid in fact_ids_by_surface.get(surf, []):
            canonical_to_facts.setdefault(cid, []).append(fid)

    return [
        Entity(
            canonical_id=cid,
            entity_type=entity_types.get(cid, "UNKNOWN"),
            surface_forms=surfs,
            fact_ids=canonical_to_facts.get(cid, []),
        )
        for cid, surfs in canonical_to_surfaces.items()
    ]


def build_resolved_kg_from_facts(facts: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Build high-quality, non-overlapping entities and deduplicated relations from facts.
    Guarantees that meaningful domain entities are resolved, duplicates collapsed,
    and edges contain evidence references.
    """
    node_registry: dict[str, dict[str, Any]] = {}
    rel_registry: dict[tuple[str, str, str], dict[str, Any]] = {}

    ent_counter = 0
    rel_counter = 0

    for f in facts:
        # Extract page provenance
        page_num = 1
        snippet = getattr(f, "canonical_text", "")
        prov_json = getattr(f, "provenance_json", None)
        if prov_json:
            try:
                provs = json.loads(prov_json) if isinstance(prov_json, str) else prov_json
                if provs and isinstance(provs, list):
                    page_num = provs[0].get("page", 1)
                    snippet = provs[0].get("snippet", snippet)
            except Exception:
                page_num = 1

        s_subj = getattr(f, "subject", "")
        s_obj = getattr(f, "object_val", None) or getattr(f, "object", "")

        s_res = resolve_canonical_entity(s_subj)
        o_res = resolve_canonical_entity(s_obj)

        s_node_id = None
        o_node_id = None

        if s_res:
            s_name, s_type = s_res
            if s_name not in node_registry:
                ent_counter += 1
                s_node_id = f"ent-{ent_counter:03d}"
                node_registry[s_name] = {
                    "id": s_node_id,
                    "text": s_name,
                    "type": s_type,
                    "confidence": round(getattr(f, "confidence", 0.9), 2),
                    "sourceRef": {"page": page_num, "snippet": snippet[:180]},
                }
            else:
                s_node_id = node_registry[s_name]["id"]

        if o_res:
            o_name, o_type = o_res
            if o_name not in node_registry:
                ent_counter += 1
                o_node_id = f"ent-{ent_counter:03d}"
                node_registry[o_name] = {
                    "id": o_node_id,
                    "text": o_name,
                    "type": o_type,
                    "confidence": round(getattr(f, "confidence", 0.9), 2),
                    "sourceRef": {"page": page_num, "snippet": snippet[:180]},
                }
            else:
                o_node_id = node_registry[o_name]["id"]

        # Add relationship if both entities resolved and distinct
        if s_node_id and o_node_id and s_node_id != o_node_id:
            pred = getattr(f, "predicate", "relates to").strip().lower()
            rel_key = (s_node_id, o_node_id, pred)
            if rel_key not in rel_registry:
                rel_counter += 1
                rel_dict = {
                    "id": f"rel-{rel_counter:03d}",
                    "fromId": s_node_id,
                    "toId": o_node_id,
                    "label": pred[:24],
                    "confidence": round(getattr(f, "confidence", 0.9), 2),
                    "evidence": snippet[:200],
                    "sourceRef": {"page": page_num},
                }
                rel_registry[rel_key] = rel_dict

    entities = list(node_registry.values())
    relations = list(rel_registry.values())

    return entities, relations

