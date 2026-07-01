from __future__ import annotations

from datetime import datetime, timezone

from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.reconciliation.discrepancies import DiscrepancyDetector
from insureflow.reconciliation.engine import ReconciliationEngine


def test_reconciliation_matches(sample_bundle) -> None:
    engine = ProvenanceEngine()
    record = engine.build_provenance(sample_bundle)

    reconciler = ReconciliationEngine()
    result = reconciler.reconcile(record)

    assert result.bundle_id == "test-bundle-001"
    assert result.match_rate > 0.5


def test_discrepancy_detection() -> None:
    detector = DiscrepancyDetector()
    from insureflow.models.provenance import DataSource, ProvenanceNode, SourceType, TrustLevel

    now = datetime.now(timezone.utc)

    source_a = DataSource(
        source_id="src-a",
        source_type=SourceType.STRUCTURED,
        source_name="broker_acord_xml",
        received_at=now,
        trust_level=TrustLevel.HIGH,
        hierarchy_rank=4,
    )
    source_b = DataSource(
        source_id="src-b",
        source_type=SourceType.UNSTRUCTURED,
        source_name="inspection_report",
        received_at=now,
        trust_level=TrustLevel.LOW,
        hierarchy_rank=2,
    )

    node_a = ProvenanceNode(
        node_id="n1",
        field_path="risk_profile.construction_type",
        value="Masonry",
        source=source_a,
        confidence=0.95,
    )
    node_b = ProvenanceNode(
        node_id="n2",
        field_path="risk_profile.construction_type",
        value="Frame",
        source=source_b,
        confidence=0.6,
    )

    result = detector.detect("risk_profile.construction_type", [node_a, node_b])
    assert result is not None
    assert result.field_path == "risk_profile.construction_type"
    assert result.structured_value == "Masonry"
    assert result.unstructured_value == "Frame"
    assert result.severity.value == "warning"


def test_no_discrepancy_on_match() -> None:
    detector = DiscrepancyDetector()
    from datetime import datetime, timezone

    from insureflow.models.provenance import DataSource, ProvenanceNode, SourceType, TrustLevel

    now = datetime.now(timezone.utc)

    source_a = DataSource(
        source_id="src-a",
        source_type=SourceType.STRUCTURED,
        source_name="broker_acord_xml",
        received_at=now,
        trust_level=TrustLevel.HIGH,
        hierarchy_rank=4,
    )
    source_b = DataSource(
        source_id="src-b",
        source_type=SourceType.UNSTRUCTURED,
        source_name="inspection_report",
        received_at=now,
        trust_level=TrustLevel.LOW,
        hierarchy_rank=2,
    )

    node_a = ProvenanceNode(
        node_id="n1",
        field_path="risk_profile.protection_class",
        value="4",
        source=source_a,
        confidence=0.95,
    )
    node_b = ProvenanceNode(
        node_id="n2",
        field_path="risk_profile.protection_class",
        value="4",
        source=source_b,
        confidence=0.7,
    )

    result = detector.detect("risk_profile.protection_class", [node_a, node_b])
    assert result is None
