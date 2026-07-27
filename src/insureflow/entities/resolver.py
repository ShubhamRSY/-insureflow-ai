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
        sim = self._cosine_similarity(vec_a, vec_b)
        if sim >= self.threshold:
            return sim
        # Fallback: token-overlap catches abbreviations like "Corp" vs "Corporation"
        return max(sim, _string_similarity(str(a.value), str(b.value)))

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


def _string_similarity(a: str, b: str) -> float:
    """String similarity combining token overlap and prefix/substring checks.

    Catches abbreviations like "Corp" vs "Corporation" and
    "Manufacturing" vs "Mfg" by checking both directions.
    """
    a_clean = re.sub(r"[^a-z0-9]", "", a.lower())
    b_clean = re.sub(r"[^a-z0-9]", "", b.lower())
    if not a_clean or not b_clean:
        return 0.0
    # Exact match after cleaning
    if a_clean == b_clean:
        return 1.0
    # One is a prefix of the other (catches "corp" in "corporation")
    if a_clean.startswith(b_clean) or b_clean.startswith(a_clean):
        shorter = min(len(a_clean), len(b_clean))
        longer = max(len(a_clean), len(b_clean))
        return shorter / longer
    # Token-level overlap
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if sa and sb:
        token_sim = len(sa & sb) / len(sa | sb)
        if token_sim > 0:
            return token_sim

    # Character n-gram Jaccard
    def ngrams(s: str, n: int = 3) -> set[str]:
        return {s[i : i + n] for i in range(len(s) - n + 1)}

    ag = ngrams(a_clean)
    bg = ngrams(b_clean)
    if ag and bg:
        return len(ag & bg) / len(ag | bg)
    return 0.0


def embedding_similarity(a: str, b: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    resolver = EntityResolver(threshold=threshold)
    vec_a = resolver._embed(a)
    vec_b = resolver._embed(b)
    sim = resolver._cosine_similarity(vec_a, vec_b)
    if sim >= threshold:
        return True
    # Fallback: token-overlap catches abbreviations like "Corp" vs "Corporation"
    return _string_similarity(a, b) >= threshold
