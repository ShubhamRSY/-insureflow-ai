from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GoldenCase:
    name: str
    acord_xml: str
    expected_insured_name: str
    expected_construction: str
    expected_occupancy: str
    expected_protection_class: int | None
    expected_square_footage: float | None
    expected_stories: int | None
    expected_naics: str | None
    expected_revenue: float | None
    expected_payroll: float | None
    expected_coverage_count: int | None = None
    expected_location_count: int | None = None
    tolerance: float = 0.05


FRAME_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>Frame Builders Inc</Name></CommercialName></NameInfo>
      </GeneralPartyInfo>
    </NamedInsured>
    <Risk>
      <NAICSCode>236115</NAICSCode>
      <ConstructionType>Frame</ConstructionType>
      <Occupancy>Manufacturing</Occupancy>
      <ProtectionClass>5</ProtectionClass>
      <NumberOfStories>2</NumberOfStories>
      <TotalSquareFootage>15000</TotalSquareFootage>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>5000000</AnnualRevenue>
      <Payroll>1250000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

MASONRY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>Masonry Properties LLC</Name></CommercialName></NameInfo>
        <Addr1>200 Brick Lane</Addr1>
        <City>Portland</City>
        <StateProvCd>OR</StateProvCd>
        <PostalCode>97201</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-01-01</EffectiveDate>
      <ExpirationDate>2027-01-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>75000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>2000000</Limit>
      <Deductible>10000</Deductible>
      <Premium>45000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>531190</NAICSCode>
      <ConstructionType>Masonry</ConstructionType>
      <Occupancy>Office</Occupancy>
      <ProtectionClass>3</ProtectionClass>
      <NumberOfStories>4</NumberOfStories>
      <TotalSquareFootage>45000</TotalSquareFootage>
      <Sprinklered>Full</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>12000000</AnnualRevenue>
    </FinancialInfo>
  </Submission>
</ACORD>"""

FIRE_RESISTIVE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>FireSafe Tower Corp</Name></CommercialName></NameInfo>
      </GeneralPartyInfo>
    </NamedInsured>
    <Risk>
      <NAICSCode>531120</NAICSCode>
      <ConstructionType>Fire Resistive</ConstructionType>
      <Occupancy>Office</Occupancy>
      <ProtectionClass>2</ProtectionClass>
      <NumberOfStories>12</NumberOfStories>
      <TotalSquareFootage>120000</TotalSquareFootage>
    </Risk>
  </Submission>
</ACORD>"""


def golden_dataset() -> list[GoldenCase]:
    return [
        GoldenCase(
            name="frame_manufacturing",
            acord_xml=FRAME_XML,
            expected_insured_name="Frame Builders Inc",
            expected_construction="Frame",
            expected_occupancy="Manufacturing",
            expected_protection_class=5,
            expected_square_footage=15000.0,
            expected_stories=2,
            expected_naics="236115",
            expected_revenue=5000000.0,
            expected_payroll=1250000.0,
            expected_coverage_count=0,
            expected_location_count=0,
        ),
        GoldenCase(
            name="masonry_office",
            acord_xml=MASONRY_XML,
            expected_insured_name="Masonry Properties LLC",
            expected_construction="Masonry",
            expected_occupancy="Office",
            expected_protection_class=3,
            expected_square_footage=45000.0,
            expected_stories=4,
            expected_naics="531190",
            expected_revenue=12000000.0,
            expected_payroll=None,
            expected_coverage_count=2,
            expected_location_count=1,
        ),
        GoldenCase(
            name="fire_resistive_office",
            acord_xml=FIRE_RESISTIVE_XML,
            expected_insured_name="FireSafe Tower Corp",
            expected_construction="Fire Resistive",
            expected_occupancy="Office",
            expected_protection_class=2,
            expected_square_footage=120000.0,
            expected_stories=12,
            expected_naics="531120",
            expected_revenue=None,
            expected_payroll=None,
            expected_coverage_count=0,
            expected_location_count=0,
        ),
    ]
