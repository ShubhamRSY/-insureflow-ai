from __future__ import annotations

from insureflow.models.provenance import (
    ProvenanceHierarchy,
    TrustLevel,
    VerificationStatus,
)
from insureflow.provenance.hierarchy import ProvenanceEngine
from insureflow.provenance.rules import VerificationRule, VerificationRuleSet
from insureflow.provenance.trust_scorer import TrustScorer


def test_provenance_hierarchy_ranking() -> None:
    hierarchy = ProvenanceHierarchy()
    assert hierarchy.rank_for_source("broker_acord_xml") > 0
    assert hierarchy.rank_for_source("inspection_report") > 0

    higher = hierarchy.higher_ranked("broker_acord_xml", "inspection_report")
    assert higher == "broker_acord_xml"


def test_provenance_engine_builds_record(sample_bundle) -> None:
    engine = ProvenanceEngine()
    record = engine.build_provenance(sample_bundle)

    assert record.bundle_id == "test-bundle-001"
    assert record.record_count() > 0


def test_provenance_engine_verification(sample_bundle) -> None:
    engine = ProvenanceEngine()
    record = engine.build_provenance(sample_bundle)

    status = engine.verify_against_authority(record, "risk_profile.construction_type", "Masonry")
    assert status == VerificationStatus.VERIFIED


def test_verification_rule_exact_match() -> None:
    rule = VerificationRule(
        name="test_exact",
        field_path="test.field",
        description="Test exact match",
    )
    ok, detail = rule.verify(["value_a", "value_a"])
    assert ok is True
    assert detail == "exact_match"


def test_verification_rule_mismatch() -> None:
    rule = VerificationRule(
        name="test_mismatch",
        field_path="test.field",
        description="Test mismatch",
    )
    ok, detail = rule.verify(["value_a", "value_b"])
    assert ok is False
    assert "mismatch" in detail


def test_verification_rule_tolerance() -> None:
    rule = VerificationRule(
        name="test_tolerance",
        field_path="test.field",
        description="Test numeric tolerance",
        tolerance=0.10,
    )
    ok, detail = rule.verify(["1000", "1050"])
    assert ok is True
    assert "within_tolerance" in detail


def test_verification_rule_tolerance_exceeded() -> None:
    rule = VerificationRule(
        name="test_tolerance_exceeded",
        field_path="test.field",
        description="Test tolerance exceeded",
        tolerance=0.10,
    )
    ok, detail = rule.verify(["1000", "1500"])
    assert ok is False


def test_trust_scorer(sample_bundle) -> None:
    engine = ProvenanceEngine()
    record = engine.build_provenance(sample_bundle)

    scorer = TrustScorer()
    scores = scorer.score(record)
    assert scores["overall"] >= 0
    assert scores["verified_fields"] >= 0
    assert scores["total_fields"] > 0


def test_trust_level_thresholds() -> None:
    scorer = TrustScorer()
    assert scorer.overall_trust_level(95) == TrustLevel.AUTHORITATIVE
    assert scorer.overall_trust_level(80) == TrustLevel.HIGH
    assert scorer.overall_trust_level(65) == TrustLevel.MEDIUM
    assert scorer.overall_trust_level(40) == TrustLevel.LOW
    assert scorer.overall_trust_level(10) == TrustLevel.UNVERIFIED


def test_default_rule_set() -> None:
    rule_set = VerificationRuleSet.default_rules()
    assert len(rule_set.rules) > 0

    rule = rule_set.get_rule("named_insured.legal_name")
    assert rule is not None
    assert rule.priority == 1
