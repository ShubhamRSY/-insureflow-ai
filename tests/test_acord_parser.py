from __future__ import annotations

from insureflow.ingestion.acord_parser import ACORDParser


def test_parse_named_insured(sample_acord_xml: str) -> None:
    parser = ACORDParser()
    submission = parser.parse(sample_acord_xml, "test-001")
    assert submission.named_insured is not None
    assert submission.named_insured.legal_name == "Acme Manufacturing Corp"
    assert submission.named_insured.address == "100 Industrial Blvd"


def test_parse_broker(sample_acord_xml: str) -> None:
    parser = ACORDParser()
    submission = parser.parse(sample_acord_xml, "test-001")
    assert submission.broker is not None
    assert submission.broker.broker_name == "Risk Advisors LLC"


def test_parse_policy_period(sample_acord_xml: str) -> None:
    parser = ACORDParser()
    submission = parser.parse(sample_acord_xml, "test-001")
    assert submission.policy_period is not None
    assert submission.policy_period.effective_date.year == 2026
    assert submission.policy_period.expiration_date.year == 2027


def test_parse_coverages(sample_acord_xml: str) -> None:
    parser = ACORDParser()
    submission = parser.parse(sample_acord_xml, "test-001")
    assert len(submission.coverages) == 2
    assert submission.coverages[0].coverage_type == "General Liability"
    assert submission.coverages[0].limit_amount == 2_000_000


def test_parse_risk_profile(sample_acord_xml: str) -> None:
    parser = ACORDParser()
    submission = parser.parse(sample_acord_xml, "test-001")
    assert submission.risk_profile is not None
    assert submission.risk_profile.naics_code == "332710"
    assert submission.risk_profile.construction_type == "Masonry"
    assert submission.risk_profile.protection_class == 4
    assert submission.risk_profile.number_of_stories == 2


def test_parse_financial(sample_acord_xml: str) -> None:
    parser = ACORDParser()
    submission = parser.parse(sample_acord_xml, "test-001")
    assert submission.financial is not None
    assert submission.financial.annual_revenue == 15_000_000
    assert submission.financial.payroll == 4_200_000


def test_parse_empty_xml() -> None:
    parser = ACORDParser()
    submission = parser.parse("<ACORD></ACORD>", "test-empty")
    assert submission.named_insured is None
    assert submission.coverages == []
