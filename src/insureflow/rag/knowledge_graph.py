"""Underwriting knowledge graph for hybrid retrieval (RAG + graph neighborhood).

Not Neo4j — a lightweight in-process graph of UW concepts:
construction, occupancy, NAICS, protection class, guidelines, controls.
Used as *retrieved context* alongside vector guideline search.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class KGNode:
    node_id: str
    label: str
    node_type: str  # construction | occupancy | naics | protection | guideline | control | hazard
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class KGEdge:
    source: str
    target: str
    relation: str  # requires | limits | excludes | related_to | applies_to | mitigates
    weight: float = 1.0


class UnderwritingKnowledgeGraph:
    """Directed multi-relation graph for UW domain retrieval."""

    def __init__(self) -> None:
        self.nodes: dict[str, KGNode] = {}
        self.out_edges: dict[str, list[KGEdge]] = defaultdict(list)
        self.in_edges: dict[str, list[KGEdge]] = defaultdict(list)

    def add_node(self, node: KGNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: KGEdge) -> None:
        self.out_edges[edge.source].append(edge)
        self.in_edges[edge.target].append(edge)

    def get(self, node_id: str) -> KGNode | None:
        return self.nodes.get(node_id)

    def neighbors(self, node_id: str, depth: int = 1) -> list[tuple[KGNode, str, float]]:
        """BFS neighborhood with relation labels."""
        if node_id not in self.nodes:
            return []
        seen = {node_id}
        q: deque[tuple[str, int]] = deque([(node_id, 0)])
        found: list[tuple[KGNode, str, float]] = []
        while q:
            current, d = q.popleft()
            if d >= depth:
                continue
            for edge in self.out_edges.get(current, []):
                if edge.target in seen:
                    continue
                seen.add(edge.target)
                node = self.nodes[edge.target]
                found.append((node, edge.relation, edge.weight))
                q.append((edge.target, d + 1))
            for edge in self.in_edges.get(current, []):
                if edge.source in seen:
                    continue
                seen.add(edge.source)
                node = self.nodes[edge.source]
                found.append((node, f"rev:{edge.relation}", edge.weight))
                q.append((edge.source, d + 1))
        return found

    def match_seeds(self, query: str) -> list[str]:
        """Map free-text query tokens to seed node ids."""
        q = query.lower()
        seeds: list[str] = []
        for nid, node in self.nodes.items():
            hay = f"{node.label} {nid} {' '.join(str(v) for v in node.properties.values())}".lower()
            # match node label tokens (>=4 chars) appearing in query
            for token in set(hay.replace("/", " ").replace("-", " ").split()):
                if len(token) >= 4 and token in q:
                    seeds.append(nid)
                    break
            if node.label.lower() in q or nid.lower().replace("_", " ") in q:
                if nid not in seeds:
                    seeds.append(nid)
        return seeds[:8]

    def retrieve_context(self, query: str, depth: int = 2, max_facts: int = 12) -> list[str]:
        """Return natural-language graph facts for RAG-style retrieved_contexts."""
        seeds = self.match_seeds(query)
        if not seeds:
            # Fallback: protection / construction hubs
            fallback = ("construction_masonry", "occupancy_manufacturing", "pc_5")
            seeds = [n for n in fallback if n in self.nodes][:2]

        facts: list[str] = []
        seen_facts: set[str] = set()
        for seed in seeds:
            seed_node = self.nodes[seed]
            header = f"[KG:{seed_node.node_type}] {seed_node.label}"
            if header not in seen_facts:
                facts.append(header)
                seen_facts.add(header)
            for neighbor, relation, weight in self.neighbors(seed, depth=depth):
                fact = f"{seed_node.label} --{relation}--> {neighbor.label} ({neighbor.node_type}; w={weight:.1f})"
                if neighbor.properties.get("rule"):
                    fact += f" | rule: {neighbor.properties['rule']}"
                if fact not in seen_facts:
                    facts.append(fact)
                    seen_facts.add(fact)
                if len(facts) >= max_facts:
                    return facts
        return facts

    def format_context_block(self, query: str, depth: int = 2, max_facts: int = 12) -> str:
        facts = self.retrieve_context(query, depth=depth, max_facts=max_facts)
        if not facts:
            return ""
        lines = ["=== UNDERWRITING KNOWLEDGE GRAPH CONTEXT ===", *facts, ""]
        return "\n".join(lines)

    def stats(self) -> dict[str, Any]:
        return {
            "nodes": len(self.nodes),
            "edges": sum(len(v) for v in self.out_edges.values()),
            "node_types": sorted({n.node_type for n in self.nodes.values()}),
            "relations": sorted({e.relation for edges in self.out_edges.values() for e in edges}),
        }


def build_underwriting_knowledge_graph() -> UnderwritingKnowledgeGraph:
    """Seed a bank/carrier-style UW domain graph used at retrieval time."""
    kg = UnderwritingKnowledgeGraph()

    nodes = [
        KGNode("construction_frame", "Frame construction", "construction", {"iso_class": "1"}),
        KGNode("construction_masonry", "Masonry construction", "construction", {"iso_class": "2"}),
        KGNode("construction_fire_resistive", "Fire resistive construction", "construction", {"iso_class": "6"}),
        KGNode("occupancy_manufacturing", "Manufacturing occupancy", "occupancy"),
        KGNode("occupancy_office", "Office occupancy", "occupancy"),
        KGNode("occupancy_retail", "Retail occupancy", "occupancy"),
        KGNode("occupancy_hospital", "Hospital / healthcare occupancy", "occupancy"),
        KGNode("occupancy_chemical", "Chemical manufacturing occupancy", "occupancy"),
        KGNode("occupancy_cold_storage", "Cold storage / ammonia refrigeration", "occupancy"),
        KGNode("pc_1_3", "Protection class 1-3", "protection", {"severity": "favorable"}),
        KGNode("pc_4", "Protection class 4", "protection"),
        KGNode("pc_5", "Protection class 5", "protection"),
        KGNode("pc_6", "Protection class 6", "protection"),
        KGNode("pc_7_10", "Protection class 7-10", "protection", {"severity": "challenging"}),
        KGNode("hazard_ammonia", "Anhydrous ammonia refrigeration", "hazard"),
        KGNode("hazard_combustible_dust", "Combustible dust operations", "hazard"),
        KGNode("hazard_hot_work", "Welding / hot-work", "hazard"),
        KGNode("control_sprinkler", "Automatic sprinkler system", "control"),
        KGNode("control_central_station", "Central station fire alarm", "control"),
        KGNode("control_dust_collection", "Industrial dust collection", "control"),
        KGNode(
            "guideline_sprinkler_10k",
            "Sprinklers required >10k sqft manufacturing",
            "guideline",
            {"rule": "Manufacturing over 10,000 sq ft requires automatic sprinklers"},
        ),
        KGNode(
            "guideline_masonry_tiv",
            "Masonry max TIV $10M",
            "guideline",
            {"rule": "Masonry per-building TIV max $10,000,000"},
        ),
        KGNode(
            "guideline_naics_exclude",
            "Excluded NAICS appetite",
            "guideline",
            {"rule": "Exclude casinos/logging/mining support/rail/postal/military from standard appetite"},
        ),
        KGNode("naics_311812", "NAICS 311812 Bakery product manufacturing", "naics"),
        KGNode("naics_325199", "NAICS 325199 Chemical manufacturing", "naics"),
        KGNode("naics_622110", "NAICS 622110 General medical/surgical hospitals", "naics"),
        KGNode("naics_484121", "NAICS 484121 General freight trucking", "naics"),
    ]
    for n in nodes:
        kg.add_node(n)

    edges: Iterable[KGEdge] = [
        KGEdge("occupancy_manufacturing", "guideline_sprinkler_10k", "requires"),
        KGEdge("occupancy_manufacturing", "control_sprinkler", "requires", 0.9),
        KGEdge("occupancy_chemical", "hazard_combustible_dust", "related_to"),
        KGEdge("occupancy_chemical", "guideline_naics_exclude", "related_to", 0.3),
        KGEdge("naics_325199", "occupancy_chemical", "applies_to"),
        KGEdge("naics_311812", "occupancy_manufacturing", "applies_to"),
        KGEdge("naics_622110", "occupancy_hospital", "applies_to"),
        KGEdge("occupancy_cold_storage", "hazard_ammonia", "related_to"),
        KGEdge("hazard_ammonia", "control_central_station", "mitigates", 0.7),
        KGEdge("hazard_combustible_dust", "control_dust_collection", "mitigates"),
        KGEdge("hazard_hot_work", "control_sprinkler", "requires"),
        KGEdge("construction_masonry", "guideline_masonry_tiv", "limits"),
        KGEdge("pc_5", "control_sprinkler", "requires", 0.6),
        KGEdge("pc_6", "control_central_station", "requires", 0.7),
        KGEdge("pc_7_10", "guideline_sprinkler_10k", "requires", 0.8),
        KGEdge("construction_frame", "pc_5", "related_to", 0.4),
        KGEdge("construction_fire_resistive", "pc_1_3", "related_to", 0.5),
        KGEdge("occupancy_retail", "construction_masonry", "related_to", 0.3),
        KGEdge("occupancy_hospital", "construction_fire_resistive", "requires", 0.6),
        KGEdge("naics_484121", "occupancy_manufacturing", "related_to", 0.2),
    ]
    for e in edges:
        kg.add_edge(e)

    return kg


# Module singleton for retrieval
_KG: UnderwritingKnowledgeGraph | None = None


def get_knowledge_graph() -> UnderwritingKnowledgeGraph:
    global _KG
    if _KG is None:
        _KG = build_underwriting_knowledge_graph()
    return _KG
