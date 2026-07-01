from __future__ import annotations

import logging
import math
import re
from typing import Any

from insureflow.models.provenance import (
    ProvenanceNode,
    ProvenanceRecord,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.85


class EntityCluster:
    def __init__(self, seed: ProvenanceNode) -> None:
        self.nodes: list[ProvenanceNode] = [seed]
        self.canonical_value: Any = seed.value
        self.field_path: str = seed.field_path

    def add(self, node: ProvenanceNode) -> None:
        self.nodes.append(node)

    def merge(self, other: EntityCluster) -> None:
        self.nodes.extend(other.nodes)

    @property
    def size(self) -> int:
        return len(self.nodes)

    @property
    def is_deduplicated(self) -> bool:
        return self.size > 1

    def resolve_canonical(self) -> Any:
        ranked = sorted(
            self.nodes,
            key=lambda n: (
                n.source.hierarchy_rank,
                n.confidence,
            ),
            reverse=True,
        )
        if ranked:
            self.canonical_value = ranked[0].value
        return self.canonical_value


class EntityResolver:
    def __init__(self, threshold: float = SIMILARITY_THRESHOLD) -> None:
        self.threshold = threshold
        self._vectors: dict[str, list[float]] = {}

    def resolve_record(self, record: ProvenanceRecord) -> ProvenanceRecord:
        for field_path, nodes in list(record.nodes.items()):
            if len(nodes) < 2:
                continue

            clusters = self._cluster_nodes(nodes)
            merged: list[ProvenanceNode] = []

            for cluster in clusters:
                canonical = cluster.resolve_canonical()
                winner = cluster.nodes[0]
                winner.value = canonical
                winner.verification_status = VerificationStatus.VERIFIED
                for dupe in cluster.nodes[1:]:
                    dupe.verification_status = VerificationStatus.CONTRADICTED
                    dupe.notes = f"Deduplicated: merged with {winner.node_id}, similarity≥{self.threshold}"
                    if dupe not in merged:
                        merged.append(dupe)
                merged.append(winner)

            record.nodes[field_path] = merged

        return record

    def _cluster_nodes(self, nodes: list[ProvenanceNode]) -> list[EntityCluster]:
        clusters: list[EntityCluster] = []
        assigned: set[str] = set()

        for i, node in enumerate(nodes):
            if node.node_id in assigned:
                continue
            cluster = EntityCluster(node)
            assigned.add(node.node_id)

            for j, other in enumerate(nodes):
                if i == j or other.node_id in assigned:
                    continue
                sim = self._compute_similarity(node, other)
                if sim >= self.threshold:
                    cluster.add(other)
                    assigned.add(other.node_id)

            clusters.append(cluster)

        return clusters

    def _compute_similarity(self, a: ProvenanceNode, b: ProvenanceNode) -> float:
        vec_a = self._embed(str(a.value))
        vec_b = self._embed(str(b.value))
        return self._cosine_similarity(vec_a, vec_b)

    def _embed(self, text: str) -> list[float]:
        cached = self._vectors.get(text)
        if cached is not None:
            return cached
        cleaned = re.sub(r"[^a-z0-9]", "", text.lower())
        ngrams: list[str] = []
        for i in range(len(cleaned) - 2):
            ngrams.append(cleaned[i : i + 3])
        vec = [0.0] * 512
        for ng in ngrams:
            hashed = hash(ng) % 512
            vec[hashed] = vec[hashed] + 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        self._vectors[text] = vec
        return vec

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


def embedding_similarity(a: str, b: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    resolver = EntityResolver(threshold=threshold)
    vec_a = resolver._embed(a)
    vec_b = resolver._embed(b)
    sim = resolver._cosine_similarity(vec_a, vec_b)
    return sim >= threshold
