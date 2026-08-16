"""Graph-net fraud rings: shared identity keys fire; isolated files stay quiet."""

from __future__ import annotations

from insureflow.agents.fraud_detection_agent import FraudDetectionAgent
from insureflow.ml.fraud_graph import EntitySnapshot, FraudRingIndex, default_ring_index, detect_fraud_rings, snapshot_from_bundle
from insureflow.models.submissions import (
    ExtractedField,
    NamedInsured,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)


def _phone_bundle(bundle_id: str, phone: str, name: str = "Acme") -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id=bundle_id,
        structured=StructuredSubmission(
            submission_id=bundle_id,
            named_insured=NamedInsured(legal_name=name),
        ),
        unstructured=[
            UnstructuredSubmission(
                submission_id=bundle_id,
                extracted_fields={"phone": [ExtractedField(field_name="phone", value=phone)]},
            )
        ],
    )


def test_shared_phone_across_three_files_is_a_ring() -> None:
    entities = [
        EntitySnapshot(entity_id="a", legal_name="A LLC", phone="555-010-1111"),
        EntitySnapshot(entity_id="b", legal_name="B Inc", phone="(555) 010-1111"),
        EntitySnapshot(entity_id="c", legal_name="C Co", phone="15550101111"),
    ]
    hits = detect_fraud_rings(entities)
    assert hits
    assert set(hits[0].member_ids) == {"a", "b", "c"}
    assert "phone" in hits[0].shared_keys
    assert hits[0].ring_score > 0


def test_isolated_entity_is_not_a_ring() -> None:
    entities = [
        EntitySnapshot(entity_id="solo", phone="555-010-9999"),
        EntitySnapshot(entity_id="other", phone="555-010-8888", email="other@example.com"),
    ]
    assert detect_fraud_rings(entities) == []


def test_single_file_never_rings() -> None:
    assert detect_fraud_rings([EntitySnapshot(entity_id="only", phone="555-010-1111")]) == []


def test_index_scores_across_files() -> None:
    index = FraudRingIndex()
    index.ingest_bundle(_phone_bundle("p1", "2125550100", "First"))
    index.ingest_bundle(_phone_bundle("p2", "212-555-0100", "Cousin"))
    hits = index.hits_for("p2")
    assert hits
    assert "p1" in hits[0].member_ids


def test_snapshot_reads_phone_from_extracted_fields() -> None:
    snap = snapshot_from_bundle(_phone_bundle("x", "415-555-0101"))
    assert snap.phone.endswith("0101") or "4155550101" in snap.identity_keys().get("phone", "")
    assert snap.identity_keys()["phone"] == "4155550101"


def test_fraud_agent_flags_linked_files() -> None:
    index = default_ring_index()
    index.clear()
    agent = FraudDetectionAgent()
    first = agent.run(_phone_bundle("ring-a", "6175550199", "Alpha"))
    assert not any(f.category == "fraud_ring" for f in first.findings)
    second = agent.run(_phone_bundle("ring-b", "617-555-0199", "Beta"))
    assert any(f.category == "fraud_ring" for f in second.findings)
    index.clear()
