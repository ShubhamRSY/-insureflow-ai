"""Submission entity graph (GraphRAG-lite) for memo grounding.

Parses structured + extracted fields into Entities (insured, location, coverage,
vehicle, claim) and Edges (insured_by, located_at, covered_by, excluded_from,
loss_on). The LLM (or deterministic memo builder) may only assert relationships
that exist as edges — inventing an edge is a citation failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from insureflow.models.submissions import SubmissionBundle


@dataclass
class EntityNode:
    entity_id: str
    entity_type: str  # insured | location | coverage | vehicle | claim | broker
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    page_number: int | None = None
    bbox: list[float] | None = None
    source_ref: str = ""


@dataclass
class EntityEdge:
    source: str
    target: str
    relation: str
    evidence: str = ""


@dataclass
class SubmissionEntityGraph:
    nodes: dict[str, EntityNode] = field(default_factory=dict)
    edges: list[EntityEdge] = field(default_factory=list)

    def add_node(self, node: EntityNode) -> None:
        self.nodes[node.entity_id] = node

    def add_edge(self, edge: EntityEdge) -> None:
        if edge.source in self.nodes and edge.target in self.nodes:
            self.edges.append(edge)

    def has_relation(self, source: str, relation: str, target: str) -> bool:
        return any(e.source == source and e.target == target and e.relation == relation for e in self.edges)

    def neighbors(self, entity_id: str) -> list[tuple[EntityEdge, EntityNode]]:
        out: list[tuple[EntityEdge, EntityNode]] = []
        for e in self.edges:
            if e.source == entity_id and e.target in self.nodes:
                out.append((e, self.nodes[e.target]))
            elif e.target == entity_id and e.source in self.nodes:
                out.append((e, self.nodes[e.source]))
        return out

    def facts(self, max_facts: int = 40) -> list[str]:
        rows: list[str] = []
        for e in self.edges[:max_facts]:
            src = self.nodes.get(e.source)
            dst = self.nodes.get(e.target)
            if not src or not dst:
                continue
            cite = f" [{e.evidence}]" if e.evidence else ""
            rows.append(f"{src.label} —{e.relation}→ {dst.label}{cite}")
        return rows

    def assert_allowed(self, source_label: str, relation: str, target_label: str) -> bool:
        """True only if an edge with that relation connects matching labels."""
        src_ids = {n.entity_id for n in self.nodes.values() if n.label.lower() == source_label.lower()}
        dst_ids = {n.entity_id for n in self.nodes.values() if n.label.lower() == target_label.lower()}
        for e in self.edges:
            if e.relation != relation:
                continue
            if e.source in src_ids and e.target in dst_ids:
                return True
            if e.target in src_ids and e.source in dst_ids:
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "entity_id": n.entity_id,
                    "entity_type": n.entity_type,
                    "label": n.label,
                    "properties": n.properties,
                    "page_number": n.page_number,
                    "bbox": n.bbox,
                    "source_ref": n.source_ref,
                }
                for n in self.nodes.values()
            ],
            "edges": [{"source": e.source, "target": e.target, "relation": e.relation, "evidence": e.evidence} for e in self.edges],
            "facts": self.facts(),
        }


def build_submission_entity_graph(bundle: SubmissionBundle) -> SubmissionEntityGraph:
    g = SubmissionEntityGraph()
    if not bundle.structured:
        return _from_extracted_only(bundle, g)

    s = bundle.structured
    insured_id = "insured:0"
    name = ""
    if s.named_insured:
        name = s.named_insured.legal_name or ""
        g.add_node(
            EntityNode(
                entity_id=insured_id,
                entity_type="insured",
                label=name or "Named Insured",
                properties={"tax_id": s.named_insured.tax_id or "", "address": s.named_insured.address or ""},
                source_ref="structured.named_insured",
            )
        )
    if s.broker:
        bid = "broker:0"
        g.add_node(
            EntityNode(
                entity_id=bid,
                entity_type="broker",
                label=s.broker.broker_name,
                properties={"email": s.broker.contact_email or ""},
                source_ref="structured.broker",
            )
        )
        if name:
            g.add_edge(EntityEdge(insured_id, bid, "brokered_by", evidence="structured.broker"))

    for i, loc in enumerate(s.locations or []):
        lid = f"location:{i}"
        label = f"{loc.address}, {loc.city}, {loc.state}".strip(", ")
        g.add_node(
            EntityNode(
                entity_id=lid,
                entity_type="location",
                label=label or f"Location {i + 1}",
                properties={
                    "building_value": loc.building_value,
                    "contents_value": loc.contents_value,
                    "year_built": loc.year_built,
                    "square_footage": loc.square_footage,
                },
                source_ref=f"structured.locations[{i}]",
            )
        )
        if name:
            g.add_edge(EntityEdge(insured_id, lid, "located_at", evidence=f"structured.locations[{i}]"))

    for i, cov in enumerate(s.coverages or []):
        cid = f"coverage:{i}"
        g.add_node(
            EntityNode(
                entity_id=cid,
                entity_type="coverage",
                label=cov.coverage_type or f"Coverage {i + 1}",
                properties={
                    "limit_amount": cov.limit_amount,
                    "deductible": cov.deductible,
                    "premium": cov.premium,
                },
                source_ref=f"structured.coverages[{i}]",
            )
        )
        if name:
            g.add_edge(EntityEdge(insured_id, cid, "covered_by", evidence=f"structured.coverages[{i}]"))
        # Link first location if present
        if s.locations:
            g.add_edge(EntityEdge(cid, "location:0", "applies_to", evidence=f"structured.coverages[{i}]"))

    if s.financial and s.financial.loss_run:
        for i, claim in enumerate(s.financial.loss_run.claims or []):
            kid = f"claim:{i}"
            g.add_node(
                EntityNode(
                    entity_id=kid,
                    entity_type="claim",
                    label=claim.claim_id or f"Claim {i + 1}",
                    properties={
                        "incurred_amount": claim.incurred_amount,
                        "cause": claim.cause,
                        "date_of_loss": str(claim.date_of_loss),
                    },
                    source_ref=f"structured.financial.loss_run.claims[{i}]",
                )
            )
            if name:
                g.add_edge(EntityEdge(insured_id, kid, "loss_on", evidence=f"loss_run[{i}]"))

    return g


def _from_extracted_only(bundle: SubmissionBundle, g: SubmissionEntityGraph) -> SubmissionEntityGraph:
    for doc in (*bundle.unstructured, *bundle.supplemental):
        for key, entries in (doc.extracted_fields or {}).items():
            if not entries or not entries[0].value:
                continue
            ef = entries[0]
            eid = f"field:{doc.submission_id}:{key}"
            g.add_node(
                EntityNode(
                    entity_id=eid,
                    entity_type="coverage" if "limit" in key.lower() or "coverage" in key.lower() else "insured",
                    label=f"{key}={ef.value}",
                    properties={"field": key, "value": ef.value},
                    page_number=ef.page_number,
                    bbox=ef.bbox,
                    source_ref=ef.source_ref or "",
                )
            )
    return g


def graph_context_block(bundle: SubmissionBundle, *, max_facts: int = 40) -> str:
    g = build_submission_entity_graph(bundle)
    facts = g.facts(max_facts=max_facts)
    if not facts:
        return "SUBMISSION_GRAPH: empty — do not invent insured/location/coverage relationships."
    return "SUBMISSION_GRAPH (only these relationships exist):\n- " + "\n- ".join(facts)


def ungrounded_relation_issues(
    assertions: Iterable[tuple[str, str, str]],
    graph: SubmissionEntityGraph,
) -> list[str]:
    """Return human-readable errors for (source, relation, target) not in the graph."""
    bad: list[str] = []
    for src, rel, dst in assertions:
        if not graph.assert_allowed(src, rel, dst):
            bad.append(f"No graph edge for {src!r} —{rel}→ {dst!r}")
    return bad
