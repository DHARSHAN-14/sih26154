"""
kg/graph.py — NetworkX knowledge graph.
Provides the queries the rest of the system needs:
- neighbours, timeline subgraph, entity paths, contradiction edges.
Serialises to JSON alongside the SoT so the graph is part of the frozen state.
"""
from __future__ import annotations
import json
import pathlib
try:
    import networkx as nx
    _NX = True
except ImportError:
    _NX = False

from app.core.schemas import Entity, TimelineEvent


class KnowledgeGraph:
    def __init__(self) -> None:
        if not _NX:
            raise ImportError("networkx is required: pip install networkx")
        self.g: nx.MultiDiGraph = nx.MultiDiGraph()

    def add_entity(self, entity: Entity) -> None:
        self.g.add_node(
            entity.canonical_id,
            entity_type=entity.entity_type,
            surface_forms=entity.surface_forms,
            fact_ids=entity.fact_ids,
        )

    def add_triple(self, subject: str, predicate: str, obj: str,
                   fact_id: str, is_contradiction: bool = False) -> None:
        self.g.add_edge(
            subject, obj,
            predicate=predicate,
            fact_id=fact_id,
            is_contradiction=is_contradiction,
        )

    def contradiction_edges(self) -> list[dict]:
        return [
            {"source": u, "target": v, "data": d}
            for u, v, d in self.g.edges(data=True)
            if d.get("is_contradiction")
        ]

    def neighbours(self, node_id: str, depth: int = 1) -> list[str]:
        if depth == 1:
            return list(self.g.successors(node_id)) + list(self.g.predecessors(node_id))
        ego = nx.ego_graph(self.g, node_id, radius=depth)
        return [n for n in ego.nodes() if n != node_id]

    def to_cytoscape(self) -> dict:
        nodes = [
            {"data": {"id": n, **self.g.nodes[n]}}
            for n in self.g.nodes()
        ]
        edges = [
            {
                "data": {
                    "source": u, "target": v,
                    **{k: v2 for k, v2 in d.items()},
                    "color": "#ef4444" if d.get("is_contradiction") else "#64748b",
                }
            }
            for u, v, d in self.g.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges}

    def save(self, path: pathlib.Path) -> None:
        path.write_text(
            json.dumps(nx.node_link_data(self.g), indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: pathlib.Path) -> "KnowledgeGraph":
        kg = cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        kg.g = nx.node_link_graph(data, directed=True, multigraph=True)
        return kg
