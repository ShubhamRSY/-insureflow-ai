from __future__ import annotations

from datetime import datetime, timezone

from insureflow.entities.resolver import EntityCluster, EntityResolver, embedding_similarity
from insureflow.models.provenance import (
    DataSource,
    ProvenanceNode,
    ProvenanceRecord,
    SourceType,
    TrustLevel,
)


def _make_node(field_path: str, value: str, rank: int = 5, node_id: str | None = None) -> ProvenanceNode:
    return ProvenanceNode(
        node_id=node_id or f"node-{field_path}-{id(value)}",
        field_path=field_path,
        value=value,
        source=DataSource(
            source_id=f"src-{field_path}",
            source_type=SourceType.STRUCTURED,
            source_name="test_source",
            received_at=datetime.now(timezone.utc),
            trust_level=TrustLevel.HIGH,
            hierarchy_rank=rank,
        ),
    )


def test_embedding_similarity_exact_match() -> None:
    assert embedding_similarity("Acme Manufacturing Corp", "Acme Manufacturing Corp")


def test_embedding_similarity_near_match() -> None:
    assert embedding_similarity("Acme Manufacturing Corp", "Acme Manufacturing Corporation")


def test_embedding_similarity_below_threshold() -> None:
    assert not embedding_similarity("Acme Manufacturing Corp", "XYZ Widgets LLC")


def test_entity_cluster_add() -> None:
    n1 = _make_node("name", "Acme Corp")
    n2 = _make_node("name", "Acme Corporation")
    cluster = EntityCluster(n1)
    cluster.add(n2)
    assert cluster.size == 2
    assert cluster.is_deduplicated


def test_entity_cluster_single() -> None:
    n1 = _make_node("name", "Acme Corp")
    cluster = EntityCluster(n1)
    assert not cluster.is_deduplicated
    assert cluster.size == 1


def test_entity_cluster_canonical_highest_rank() -> None:
    n1 = _make_node("name", "Acme Corp", rank=5)
    n2 = _make_node("name", "Acme Corporation", rank=10)
    cluster = EntityCluster(n1)
    cluster.add(n2)
    canonical = cluster.resolve_canonical()
    assert canonical == "Acme Corporation"


def test_entity_resolver_similar_values() -> None:
    resolver = EntityResolver(threshold=0.85)
    nodes = [
        _make_node("name", "Acme Manufacturing Corp", rank=10),
        _make_node("name", "Acme Manufacturing Corporation", rank=5),
    ]
    clusters = resolver._cluster_nodes(nodes)
    assert len(clusters) == 1
    assert clusters[0].size == 2


def test_entity_resolver_dissimilar_values() -> None:
    resolver = EntityResolver(threshold=0.85)
    nodes = [
        _make_node("name", "Acme Manufacturing Corp", rank=10),
        _make_node("name", "100 Industrial Blvd", rank=5),
    ]
    clusters = resolver._cluster_nodes(nodes)
    assert len(clusters) == 2


def test_entity_resolver_resolve_record() -> None:
    resolver = EntityResolver(threshold=0.85)
    n1 = _make_node("insured.name", "Acme Manufacturing Corp", rank=10, node_id="n1")
    n2 = _make_node("insured.name", "Acme Manufacturing Corporation", rank=5, node_id="n2")

    record = ProvenanceRecord(
        record_id="test-record",
        bundle_id="test-bundle",
        nodes={"insured.name": [n1, n2]},
    )
    resolved = resolver.resolve_record(record)

    nodes = resolved.nodes["insured.name"]
    assert len(nodes) == 2
    verified = [n for n in nodes if n.verification_status.value == "verified"]
    contradicted = [n for n in nodes if n.verification_status.value == "contradicted"]
    assert len(verified) == 1
    assert len(contradicted) == 1
    assert contradicted[0].notes is not None
    assert "Deduplicated" in contradicted[0].notes


def test_entity_resolver_single_node() -> None:
    resolver = EntityResolver(threshold=0.85)
    n1 = _make_node("name", "Acme Corp")
    record = ProvenanceRecord(
        record_id="test-record",
        bundle_id="test-bundle",
        nodes={"name": [n1]},
    )
    resolved = resolver.resolve_record(record)
    nodes = resolved.nodes["name"]
    assert len(nodes) == 1
    assert nodes[0].verification_status.value == "unverified"


def test_entity_resolver_provenance_integration() -> None:
    from insureflow.models.submissions import (
        NamedInsured,
        RiskProfile,
        StructuredSubmission,
        SubmissionBundle,
    )
    from insureflow.provenance.hierarchy import ProvenanceEngine

    engine = ProvenanceEngine(deduplicate=True)
    bundle = SubmissionBundle(
        bundle_id="test-dedup",
        structured=StructuredSubmission(
            submission_id="test-sub",
            named_insured=NamedInsured(
                legal_name="Acme Manufacturing Corp",
                entity_type="Corporation",
                address="100 Industrial Blvd",
            ),
            risk_profile=RiskProfile(
                naics_code="332710",
                construction_type="Masonry",
                occupancy_type="Manufacturing",
                protection_class=4,
            ),
        ),
    )
    record = engine.build_provenance(bundle)
    assert record is not None
    assert record.record_count() > 0

    name_nodes = record.nodes.get("named_insured.legal_name", [])
    if len(name_nodes) > 1:
        verified = [n for n in name_nodes if n.verification_status.value == "verified"]
        assert len(verified) >= 1
