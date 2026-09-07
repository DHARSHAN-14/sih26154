"""
app/kg — Knowledge Graph package.

Public API:
    KnowledgeGraph      — NetworkX-backed graph (graph.py)
    Triple              — Extracted subject-predicate-object triple (extractor.py)
    extract_triples     — Triple extraction from raw text (extractor.py)
    resolve_entities    — Map surface forms → canonical IDs (resolver.py)
    build_entities      — Build Entity objects from resolved surface forms (resolver.py)
    detect_contradictions — Deterministic contradiction detection (contradiction.py)
    to_cytoscape        — Export pruned graph as Cytoscape.js JSON (export.py)
"""

from app.kg.graph import KnowledgeGraph
from app.kg.extractor import Triple, extract_triples
from app.kg.resolver import resolve_entities, build_entities
from app.kg.contradiction import detect_contradictions
from app.kg.export import to_cytoscape

__all__ = [
    "KnowledgeGraph",
    "Triple",
    "extract_triples",
    "resolve_entities",
    "build_entities",
    "detect_contradictions",
    "to_cytoscape",
]
