"""
kg/export.py — Convert NetworkX graph to Cytoscape.js JSON.
Prunes to a readable subgraph: top entities by degree + all contradiction edges.
"""
from __future__ import annotations
from app.kg.graph import KnowledgeGraph


def to_cytoscape(kg: KnowledgeGraph, max_nodes: int = 50) -> dict:
    """Export a pruned, Cytoscape.js-ready element list."""
    try:
        import networkx as nx
    except ImportError:
        return {"nodes": [], "edges": []}

    g = kg.g
    if len(g.nodes()) == 0:
        return {"nodes": [], "edges": []}

    # Always include nodes involved in contradictions
    contradiction_nodes: set[str] = set()
    for u, v, d in g.edges(data=True):
        if d.get("is_contradiction"):
            contradiction_nodes.update([u, v])

    # Top nodes by degree
    degrees = sorted(g.degree(), key=lambda x: x[1], reverse=True)
    top_nodes = {n for n, _ in degrees[:max_nodes]} | contradiction_nodes

    sub = g.subgraph(top_nodes)

    nodes = [
        {"data": {"id": n, "label": n[:30], **dict(sub.nodes[n])}}
        for n in sub.nodes()
    ]
    edges = [
        {
            "data": {
                "id": f"{u}-{v}-{i}",
                "source": u,
                "target": v,
                **d,
                "color": "#ef4444" if d.get("is_contradiction") else "#64748b",
            }
        }
        for i, (u, v, d) in enumerate(sub.edges(data=True))
    ]
    return {"nodes": nodes, "edges": edges}
