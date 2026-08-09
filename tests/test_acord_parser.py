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


def test_detect_forms_from_form_number_elements() -> None:
    xml = """<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
      <Submission>
        <FormNumber>125</FormNumber>
        <FormNumber>130</FormNumber>
        <FormNumber>140</FormNumber>
      </Submission>
    </ACORD>"""
    submission = ACORDParser().parse(xml, "forms-001")
    assert submission.acord_forms == ["125", "130", "140"]


def test_detect_forms_from_acord_mention() -> None:
    xml = """<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
      <Submission>
        <Notes>Completed as ACORD 126 for the primary GL placement.</Notes>
      </Submission>
    </ACORD>"""
    submission = ACORDParser().parse(xml, "forms-002")
    assert "126" in submission.acord_forms
    assert "125" in submission.acord_forms


def test_detect_forms_infers_sections_from_coverages() -> None:
    xml = """<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
      <Submission>
        <Coverage>
          <CoverageType>General Liability</CoverageType>
          <Limit>2000000</Limit>
        </Coverage>
        <Coverage>
          <CoverageType>Commercial Property</CoverageType>
          <Limit>5000000</Limit>
        </Coverage>
        <Coverage>
          <CoverageType>Commercial Umbrella</CoverageType>
          <Limit>5000000</Limit>
        </Coverage>
      </Submission>
    </ACORD>"""
    submission = ACORDParser().parse(xml, "forms-003")
    assert submission.acord_forms == ["126", "130", "140", "125"]


def test_detect_forms_ignores_limits_that_look_like_numbers() -> None:
    xml = """<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
      <Submission>
        <Coverage>
          <CoverageType>General Liability</CoverageType>
          <Limit>1250000</Limit>
          <Deductible>12600</Deductible>
        </Coverage>
      </Submission>
    </ACORD>"""
    submission = ACORDParser().parse(xml, "forms-004")
    assert submission.acord_forms == ["126", "125"]


def test_detect_forms_none_for_empty() -> None:
    submission = ACORDParser().parse("<ACORD></ACORD>", "forms-empty")
    assert submission.acord_forms == []
