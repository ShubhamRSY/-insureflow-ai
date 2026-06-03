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


CHEMICAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>ChemCorp Manufacturing Inc</Name></CommercialName></NameInfo>
        <Addr1>500 Industrial Parkway</Addr1>
        <City>Houston</City>
        <StateProvCd>TX</StateProvCd>
        <PostalCode>77001</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-03-01</EffectiveDate>
      <ExpirationDate>2027-03-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>25000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>185000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>95000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Environmental Liability</CoverageType>
      <Limit>10000000</Limit>
      <Deductible>100000</Deductible>
      <Premium>220000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>325199</NAICSCode>
      <ConstructionType>Masonry</ConstructionType>
      <Occupancy>Chemical Manufacturing</Occupancy>
      <ProtectionClass>6</ProtectionClass>
      <NumberOfStories>3</NumberOfStories>
      <TotalSquareFootage>85000</TotalSquareFootage>
      <Sprinklered>Full</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>45000000</AnnualRevenue>
      <Payroll>8500000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

FOOD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>FreshBake Foods LLC</Name></CommercialName></NameInfo>
        <Addr1>1200 Distribution Ave</Addr1>
        <City>Chicago</City>
        <StateProvCd>IL</StateProvCd>
        <PostalCode>60607</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-02-15</EffectiveDate>
      <ExpirationDate>2027-02-15</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>12000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>110000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>3000000</Limit>
      <Deductible>15000</Deductible>
      <Premium>65000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Product Liability</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>88000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Equipment Breakdown</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>10000</Deductible>
      <Premium>35000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>311812</NAICSCode>
      <ConstructionType>Frame</ConstructionType>
      <Occupancy>Food Processing</Occupancy>
      <ProtectionClass>5</ProtectionClass>
      <NumberOfStories>2</NumberOfStories>
      <TotalSquareFootage>65000</TotalSquareFootage>
      <Sprinklered>Full</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>28000000</AnnualRevenue>
      <Payroll>5200000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

HEALTHCARE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>Mercy Health Systems Inc</Name></CommercialName></NameInfo>
        <Addr1>1 Medical Center Drive</Addr1>
        <City>Boston</City>
        <StateProvCd>MA</StateProvCd>
        <PostalCode>02115</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-01-01</EffectiveDate>
      <ExpirationDate>2027-01-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>50000000</Limit>
      <Deductible>100000</Deductible>
      <Premium>420000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>10000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>180000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Professional Liability</CoverageType>
      <Limit>15000000</Limit>
      <Deductible>75000</Deductible>
      <Premium>350000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Cyber Liability</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>95000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>622110</NAICSCode>
      <ConstructionType>Fire Resistive</ConstructionType>
      <Occupancy>Hospital</Occupancy>
      <ProtectionClass>2</ProtectionClass>
      <NumberOfStories>8</NumberOfStories>
      <TotalSquareFootage>250000</TotalSquareFootage>
      <Sprinklered>Full</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>120000000</AnnualRevenue>
      <Payroll>65000000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

RETAIL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>ValueMart Retail Corp</Name></CommercialName></NameInfo>
        <Addr1>850 Commerce Blvd</Addr1>
        <City>Atlanta</City>
        <StateProvCd>GA</StateProvCd>
        <PostalCode>30303</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-04-01</EffectiveDate>
      <ExpirationDate>2027-04-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>35000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>275000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>120000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Workers Compensation</CoverageType>
      <Limit>1000000</Limit>
      <Deductible>5000</Deductible>
      <Premium>310000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>452112</NAICSCode>
      <ConstructionType>Masonry</ConstructionType>
      <Occupancy>Retail Store</Occupancy>
      <ProtectionClass>4</ProtectionClass>
      <NumberOfStories>2</NumberOfStories>
      <TotalSquareFootage>120000</TotalSquareFootage>
      <Sprinklered>Partial</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>85000000</AnnualRevenue>
      <Payroll>15000000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

TECH_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>CloudBase Technologies Inc</Name></CommercialName></NameInfo>
        <Addr1>200 Innovation Way</Addr1>
        <City>San Francisco</City>
        <StateProvCd>CA</StateProvCd>
        <PostalCode>94105</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-05-01</EffectiveDate>
      <ExpirationDate>2027-05-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>15000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>95000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>3000000</Limit>
      <Deductible>10000</Deductible>
      <Premium>48000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Cyber Liability</CoverageType>
      <Limit>10000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>185000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Errors & Omissions</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>145000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>541511</NAICSCode>
      <ConstructionType>Fire Resistive</ConstructionType>
      <Occupancy>Office</Occupancy>
      <ProtectionClass>3</ProtectionClass>
      <NumberOfStories>5</NumberOfStories>
      <TotalSquareFootage>60000</TotalSquareFootage>
      <Sprinklered>Full</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>65000000</AnnualRevenue>
      <Payroll>38000000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

TRANSPORT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>SwiftHaul Logistics Co</Name></CommercialName></NameInfo>
        <Addr1>780 Freight Terminal Rd</Addr1>
        <City>Memphis</City>
        <StateProvCd>TN</StateProvCd>
        <PostalCode>38101</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-01-15</EffectiveDate>
      <ExpirationDate>2027-01-15</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Auto Liability</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>450000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Physical Damage</CoverageType>
      <Limit>15000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>280000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>3000000</Limit>
      <Deductible>15000</Deductible>
      <Premium>75000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Workers Compensation</CoverageType>
      <Limit>1000000</Limit>
      <Deductible>5000</Deductible>
      <Premium>520000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Cargo Liability</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>10000</Deductible>
      <Premium>125000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>484121</NAICSCode>
      <ConstructionType>Frame</ConstructionType>
      <Occupancy>Trucking Terminal</Occupancy>
      <ProtectionClass>6</ProtectionClass>
      <NumberOfStories>1</NumberOfStories>
      <TotalSquareFootage>45000</TotalSquareFootage>
      <Sprinklered>None</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>52000000</AnnualRevenue>
      <Payroll>18000000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

HOSPITALITY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>Grand Shores Resort & Spa</Name></CommercialName></NameInfo>
        <Addr1>1 Oceanfront Drive</Addr1>
        <City>Miami Beach</City>
        <StateProvCd>FL</StateProvCd>
        <PostalCode>33139</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-06-01</EffectiveDate>
      <ExpirationDate>2027-06-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>75000000</Limit>
      <Deductible>100000</Deductible>
      <Premium>680000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>10000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>220000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Liquor Liability</CoverageType>
      <Limit>2000000</Limit>
      <Deductible>10000</Deductible>
      <Premium>85000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Workers Compensation</CoverageType>
      <Limit>1000000</Limit>
      <Deductible>5000</Deductible>
      <Premium>410000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>721110</NAICSCode>
      <ConstructionType>Fire Resistive</ConstructionType>
      <Occupancy>Hotel / Resort</Occupancy>
      <ProtectionClass>2</ProtectionClass>
      <NumberOfStories>15</NumberOfStories>
      <TotalSquareFootage>280000</TotalSquareFootage>
      <Sprinklered>Full</Sprinklered>
      <Windstorm>Yes</Windstorm>
      <FloodZone>AE</FloodZone>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>95000000</AnnualRevenue>
      <Payroll>28000000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

AGRICULTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>GreenField Ag Corp</Name></CommercialName></NameInfo>
        <Addr1>3000 Farm Route 12</Addr1>
        <City>Fresno</City>
        <StateProvCd>CA</StateProvCd>
        <PostalCode>93701</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-03-15</EffectiveDate>
      <ExpirationDate>2027-03-15</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>25000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>145000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>3000000</Limit>
      <Deductible>15000</Deductible>
      <Premium>55000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Crop Insurance</CoverageType>
      <Limit>15000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>320000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Equipment Floater</CoverageType>
      <Limit>8000000</Limit>
      <Deductible>10000</Deductible>
      <Premium>78000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>111998</NAICSCode>
      <ConstructionType>Frame</ConstructionType>
      <Occupancy>Agricultural Operations</Occupancy>
      <ProtectionClass>8</ProtectionClass>
      <NumberOfStories>1</NumberOfStories>
      <TotalSquareFootage>35000</TotalSquareFootage>
      <Sprinklered>None</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>22000000</AnnualRevenue>
      <Payroll>4500000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

ENERGY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>Summit Energy Partners LLC</Name></CommercialName></NameInfo>
        <Addr1>1800 Power Plant Road</Addr1>
        <City>Denver</City>
        <StateProvCd>CO</StateProvCd>
        <PostalCode>80202</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-02-01</EffectiveDate>
      <ExpirationDate>2027-02-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>100000000</Limit>
      <Deductible>250000</Deductible>
      <Premium>950000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>10000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>185000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Environmental Liability</CoverageType>
      <Limit>25000000</Limit>
      <Deductible>100000</Deductible>
      <Premium>450000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Equipment Breakdown</CoverageType>
      <Limit>50000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>320000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>221118</NAICSCode>
      <ConstructionType>Fire Resistive</ConstructionType>
      <Occupancy>Power Generation</Occupancy>
      <ProtectionClass>3</ProtectionClass>
      <NumberOfStories>2</NumberOfStories>
      <TotalSquareFootage>90000</TotalSquareFootage>
      <Sprinklered>Full</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>200000000</AnnualRevenue>
      <Payroll>25000000</Payroll>
    </FinancialInfo>
  </Submission>
</ACORD>"""

CONSTRUCTION_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo><CommercialName><Name>Pinnacle Construction Group</Name></CommercialName></NameInfo>
        <Addr1>450 Builder Avenue</Addr1>
        <City>Phoenix</City>
        <StateProvCd>AZ</StateProvCd>
        <PostalCode>85001</PostalCode>
      </GeneralPartyInfo>
    </NamedInsured>
    <PolicyPeriod>
      <EffectiveDate>2026-04-15</EffectiveDate>
      <ExpirationDate>2027-04-15</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>General Liability</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>25000</Deductible>
      <Premium>210000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Workers Compensation</CoverageType>
      <Limit>1000000</Limit>
      <Deductible>5000</Deductible>
      <Premium>680000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Equipment Floater</CoverageType>
      <Limit>5000000</Limit>
      <Deductible>15000</Deductible>
      <Premium>85000</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Builder's Risk</CoverageType>
      <Limit>20000000</Limit>
      <Deductible>50000</Deductible>
      <Premium>175000</Premium>
    </Coverage>
    <Risk>
      <NAICSCode>236220</NAICSCode>
      <ConstructionType>Masonry</ConstructionType>
      <Occupancy>Construction Yard</Occupancy>
      <ProtectionClass>5</ProtectionClass>
      <NumberOfStories>1</NumberOfStories>
      <TotalSquareFootage>20000</TotalSquareFootage>
      <Sprinklered>None</Sprinklered>
    </Risk>
    <FinancialInfo>
      <AnnualRevenue>38000000</AnnualRevenue>
      <Payroll>22000000</Payroll>
    </FinancialInfo>
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
        GoldenCase(
            name="chemical_manufacturing",
            acord_xml=CHEMICAL_XML,
            expected_insured_name="ChemCorp Manufacturing Inc",
            expected_construction="Masonry",
            expected_occupancy="Chemical Manufacturing",
            expected_protection_class=6,
            expected_square_footage=85000.0,
            expected_stories=3,
            expected_naics="325199",
            expected_revenue=45000000.0,
            expected_payroll=8500000.0,
            expected_coverage_count=3,
            expected_location_count=1,
        ),
        GoldenCase(
            name="food_processing",
            acord_xml=FOOD_XML,
            expected_insured_name="FreshBake Foods LLC",
            expected_construction="Frame",
            expected_occupancy="Food Processing",
            expected_protection_class=5,
            expected_square_footage=65000.0,
            expected_stories=2,
            expected_naics="311812",
            expected_revenue=28000000.0,
            expected_payroll=5200000.0,
            expected_coverage_count=4,
            expected_location_count=1,
        ),
        GoldenCase(
            name="healthcare_hospital",
            acord_xml=HEALTHCARE_XML,
            expected_insured_name="Mercy Health Systems Inc",
            expected_construction="Fire Resistive",
            expected_occupancy="Hospital",
            expected_protection_class=2,
            expected_square_footage=250000.0,
            expected_stories=8,
            expected_naics="622110",
            expected_revenue=120000000.0,
            expected_payroll=65000000.0,
            expected_coverage_count=4,
            expected_location_count=1,
        ),
        GoldenCase(
            name="retail_store",
            acord_xml=RETAIL_XML,
            expected_insured_name="ValueMart Retail Corp",
            expected_construction="Masonry",
            expected_occupancy="Retail Store",
            expected_protection_class=4,
            expected_square_footage=120000.0,
            expected_stories=2,
            expected_naics="452112",
            expected_revenue=85000000.0,
            expected_payroll=15000000.0,
            expected_coverage_count=3,
            expected_location_count=1,
        ),
        GoldenCase(
            name="technology_company",
            acord_xml=TECH_XML,
            expected_insured_name="CloudBase Technologies Inc",
            expected_construction="Fire Resistive",
            expected_occupancy="Office",
            expected_protection_class=3,
            expected_square_footage=60000.0,
            expected_stories=5,
            expected_naics="541511",
            expected_revenue=65000000.0,
            expected_payroll=38000000.0,
            expected_coverage_count=4,
            expected_location_count=1,
        ),
        GoldenCase(
            name="transportation_trucking",
            acord_xml=TRANSPORT_XML,
            expected_insured_name="SwiftHaul Logistics Co",
            expected_construction="Frame",
            expected_occupancy="Trucking Terminal",
            expected_protection_class=6,
            expected_square_footage=45000.0,
            expected_stories=1,
            expected_naics="484121",
            expected_revenue=52000000.0,
            expected_payroll=18000000.0,
            expected_coverage_count=5,
            expected_location_count=1,
        ),
        GoldenCase(
            name="hospitality_resort",
            acord_xml=HOSPITALITY_XML,
            expected_insured_name="Grand Shores Resort & Spa",
            expected_construction="Fire Resistive",
            expected_occupancy="Hotel / Resort",
            expected_protection_class=2,
            expected_square_footage=280000.0,
            expected_stories=15,
            expected_naics="721110",
            expected_revenue=95000000.0,
            expected_payroll=28000000.0,
            expected_coverage_count=4,
            expected_location_count=1,
        ),
        GoldenCase(
            name="agriculture_farming",
            acord_xml=AGRICULTURE_XML,
            expected_insured_name="GreenField Ag Corp",
            expected_construction="Frame",
            expected_occupancy="Agricultural Operations",
            expected_protection_class=8,
            expected_square_footage=35000.0,
            expected_stories=1,
            expected_naics="111998",
            expected_revenue=22000000.0,
            expected_payroll=4500000.0,
            expected_coverage_count=4,
            expected_location_count=1,
        ),
        GoldenCase(
            name="energy_power_generation",
            acord_xml=ENERGY_XML,
            expected_insured_name="Summit Energy Partners LLC",
            expected_construction="Fire Resistive",
            expected_occupancy="Power Generation",
            expected_protection_class=3,
            expected_square_footage=90000.0,
            expected_stories=2,
            expected_naics="221118",
            expected_revenue=200000000.0,
            expected_payroll=25000000.0,
            expected_coverage_count=4,
            expected_location_count=1,
        ),
        GoldenCase(
            name="construction_general_contractor",
            acord_xml=CONSTRUCTION_XML,
            expected_insured_name="Pinnacle Construction Group",
            expected_construction="Masonry",
            expected_occupancy="Construction Yard",
            expected_protection_class=5,
            expected_square_footage=20000.0,
            expected_stories=1,
            expected_naics="236220",
            expected_revenue=38000000.0,
            expected_payroll=22000000.0,
            expected_coverage_count=4,
            expected_location_count=1,
        ),
    ]
