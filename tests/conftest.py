from __future__ import annotations

from datetime import date

import pytest

from insureflow.models.submissions import (
    BrokerInfo,
    CoverageDetail,
    ExtractedField,
    FinancialData,
    NamedInsured,
    PolicyPeriod,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)

SAMPLE_ACORD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo>
          <CommercialName>
            <Name>Acme Manufacturing Corp</Name>
          </CommercialName>
        </NameInfo>
        <Addr1>100 Industrial Blvd</Addr1>
        <City>Chicago</City>
        <StateProvCd>IL</StateProvCd>
        <PostalCode>60601</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <Broker>
      <GeneralPartyInfo>
        <NameInfo>
          <CommercialName>
            <Name>Risk Advisors LLC</Name>
          </CommercialName>
        </NameInfo>
      </GeneralPartyInfo>
    </Broker>
    <PolicyPeriod>
      <EffectiveDate>2026-07-01</EffectiveDate>
      <ExpirationDate>2027-07-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>2000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>85000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>120000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>332710</NAICSCode>
      <ConstructionType>Masonry</ConstructionType>
      <Occupancy>Manufacturing</Occupancy>
      <ProtectionClass>4</ProtectionClass>
      <NumberOfStories>2</NumberOfStories>
      <TotalSquareFootage>85000</TotalSquareFootage>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>15000000</AnnualRevenue>
      <Payroll>4200000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

SAMPLE_INSPECTION_REPORT = """# INSPECTION REPORT
## Acme Manufacturing Corp
## 100 Industrial Blvd, Chicago, IL 60601

### BUILDING CONSTRUCTION
The building is a 2-story masonry structure built in 1995.
Total square footage is approximately 85,000 sq ft.

### FIRE PROTECTION
The building is fully sprinklered with a central station alarm.
Protection class: 4.

### PRIOR LOSSES
One prior claim in 2023 for water damage ($15,000).
"""


@pytest.fixture
def sample_acord_xml() -> str:
    return SAMPLE_ACORD_XML


@pytest.fixture
def sample_inspection_report() -> str:
    return SAMPLE_INSPECTION_REPORT


@pytest.fixture
def sample_structured_submission() -> StructuredSubmission:
    return StructuredSubmission(
        submission_id="test-001",
        named_insured=NamedInsured(
            legal_name="Acme Manufacturing Corp",
            entity_type="Corporation",
            address="100 Industrial Blvd",
        ),
        broker=BrokerInfo(broker_name="Risk Advisors LLC"),
        policy_period=PolicyPeriod(
            effective_date=date(2026, 7, 1),
            expiration_date=date(2027, 7, 1),
        ),
        coverages=[
            CoverageDetail(
                coverage_type="General Liability",
                limit_amount=2_000_000,
                deductible=25_000,
                premium=85_000,
            ),
        ],
        risk_profile=RiskProfile(
            naics_code="332710",
            construction_type="Masonry",
            occupancy_type="Manufacturing",
            protection_class=4,
            number_of_stories=2,
            total_square_footage=85000,
        ),
        financial=FinancialData(annual_revenue=15_000_000, payroll=4_200_000),
    )


@pytest.fixture
def sample_bundle(sample_structured_submission: StructuredSubmission) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="test-bundle-001",
        structured=sample_structured_submission,
        unstructured=[
            UnstructuredSubmission(
                submission_id="test-001-inspection-0",
                source="inspection_report",
                raw_text=SAMPLE_INSPECTION_REPORT,
                extracted_fields={
                    "construction_type": [ExtractedField(field_name="construction_type", value="Masonry", confidence=0.7)],
                    "year_built": [ExtractedField(field_name="year_built", value="1995", confidence=0.7)],
                    "square_footage": [ExtractedField(field_name="square_footage", value="85000", confidence=0.7)],
                    "number_of_stories": [ExtractedField(field_name="number_of_stories", value="2", confidence=0.7)],
                    "sprinklered": [ExtractedField(field_name="sprinklered", value="fully", confidence=0.7)],
                    "protection_class": [ExtractedField(field_name="protection_class", value="4", confidence=0.7)],
                },
            )
        ],
    )
