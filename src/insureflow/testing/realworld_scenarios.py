"""Realistic commercial P&C submission scenarios for all-condition pipeline testing.

Each scenario mimics a broker package a carrier would receive: ACORD XML,
loss run, SOV, and inspection notes — with intentional risk signals so we can
assert appetite decline, referral, missing-data REFER, and clean-path behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ScenarioExpectation:
    """Loose expectations — agents may add findings; appetite gates are hard."""

    decision_in: tuple[str, ...]
    appetite_passed: bool | None = None  # None = don't assert
    human_review_required: bool | None = None
    quote_eligible: bool | None = None
    must_have_finding_substr: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class RealWorldScenario:
    id: str
    title: str
    condition: str  # decline | refer | accept_path | missing_data | conditional
    insured_name: str
    acord_xml: str
    loss_run: str | None = None
    schedule_of_values: str | None = None
    inspection_reports: tuple[str, ...] = ()
    supplemental_docs: tuple[str, ...] = ()
    expectation: ScenarioExpectation = field(
        default_factory=lambda: ScenarioExpectation(decision_in=("accept", "conditional_accept", "refer", "decline"))
    )


def _acord(
    *,
    name: str,
    dba: str,
    tax_id: str,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    naics: str,
    building: float,
    contents: float,
    bi: float = 0.0,
    occupancy: str = "Mercantile",
    construction: str = "Masonry Non-Combustible",
    year_built: int = 2008,
    sqft: int = 45000,
    premium_property: float = 28000,
    premium_gl: float = 12000,
    entity_type: str = "Corporation",
    year_organized: int = 2005,
    broker: str = "Summit Commercial Brokers",
    broker_email: str = "desk@summitcb.com",
    limit_property: float | None = None,
) -> str:
    prop_limit = limit_property if limit_property is not None else building + contents + bi
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ACORD xmlns="http://www.acord.org/standards/PC_Surety/ACORD">
  <Submission>
    <NamedInsured>
      <GeneralPartyInfo>
        <NameInfo>
          <CommercialName>
            <Name>{name}</Name>
            <DBA>{dba}</DBA>
          </CommercialName>
        </NameInfo>
        <Addr1>{address}</Addr1>
        <City>{city}</City>
        <StateProvCd>{state}</StateProvCd>
        <PostalCode>{zip_code}</PostalCode>
        <TaxIdentity><TaxID>{tax_id}</TaxID></TaxIdentity>
        <BusinessType>{entity_type}</BusinessType>
        <YearOrganized>{year_organized}</YearOrganized>
      </GeneralPartyInfo>
    </NamedInsured>
    <Broker>
      <GeneralPartyInfo>
        <ID>BRK-RW-10001</ID>
        <NameInfo>
          <CommercialName><Name>{broker}</Name></CommercialName>
        </NameInfo>
        <ContactName>Alex Rivera, CIC</ContactName>
        <Email>{broker_email}</Email>
      </GeneralPartyInfo>
    </Broker>
    <PolicyPeriod>
      <EffectiveDate>2026-11-01</EffectiveDate>
      <ExpirationDate>2027-11-01</ExpirationDate>
    </PolicyPeriod>
    <Coverage>
      <CoverageType>Commercial General Liability</CoverageType>
      <Limit>2000000</Limit>
      <Deductible>0</Deductible>
      <Premium>{premium_gl:.0f}</Premium>
    </Coverage>
    <Coverage>
      <CoverageType>Property</CoverageType>
      <Limit>{prop_limit:.0f}</Limit>
      <Deductible>10000</Deductible>
      <Premium>{premium_property:.0f}</Premium>
    </Coverage>
    <Location>
      <LocNumber>1</LocNumber>
      <Addr1>{address}</Addr1>
      <City>{city}</City>
      <StateProvCd>{state}</StateProvCd>
      <PostalCode>{zip_code}</PostalCode>
      <BuildingOccupancy>{occupancy}</BuildingOccupancy>
      <Occupancy>{occupancy}</Occupancy>
      <ConstructionType>{construction}</ConstructionType>
      <YearBuilt>{year_built}</YearBuilt>
      <SquareFootage>{sqft}</SquareFootage>
      <EstimatedValue>{building:.0f}</EstimatedValue>
      <BuildingValue>{building:.0f}</BuildingValue>
      <ContentsValue>{contents:.0f}</ContentsValue>
      <BusinessIncomeValue>{bi:.0f}</BusinessIncomeValue>
      <ProtectionClass>4</ProtectionClass>
      <Sprinklered>Yes</Sprinklered>
    </Location>
    <Risk>
      <NAICSCode>{naics}</NAICSCode>
      <Description>{occupancy} operations</Description>
    </Risk>
  </Submission>
</ACORD>
"""


def _clean_loss_run(insured: str, earned: float = 180_000, incurred: float = 22_000) -> str:
    lr = (incurred / earned * 100.0) if earned else 0.0
    return f"""# Loss Run — {insured}
Carrier: Prior Mutual Insurance Company
Policy Term: 2021-11-01 to 2026-10-31 (5 years)
Claim count: 2
Total incurred: ${incurred:,.0f}

## LOSS RATE ANALYSIS
| Policy Period | Earned Premium | Total Incurred Loss | Loss Ratio |
|---|---|---|---|
| 2021-2022 | ${earned * 0.18:,.0f} | ${incurred * 0.2:,.0f} | {lr * 0.9:.1f}% |
| 2022-2023 | ${earned * 0.19:,.0f} | ${incurred * 0.15:,.0f} | {lr * 0.7:.1f}% |
| 2023-2024 | ${earned * 0.20:,.0f} | ${incurred * 0.25:,.0f} | {lr * 1.1:.1f}% |
| 2024-2025 | ${earned * 0.21:,.0f} | ${incurred * 0.25:,.0f} | {lr * 1.0:.1f}% |
| 2025-2026 | ${earned * 0.22:,.0f} | ${incurred * 0.15:,.0f} | {lr * 0.6:.1f}% |
| 2021-2026 | ${earned:,.0f} | ${incurred:,.0f} | {lr:.1f}% |

No open claims. No prior cancellations or non-renewals.
"""


def _bad_loss_run(insured: str, ratio: float = 0.92) -> str:
    earned = 200_000.0
    incurred = earned * ratio
    pct = ratio * 100.0
    return f"""# Loss Run — {insured}
Carrier: Harbor Specialty
Claim count: 3
Total incurred: ${incurred:,.0f}
Loss Ratio: {pct:.0f}%

## LOSS RATE ANALYSIS
| Policy Period | Earned Premium | Total Incurred Loss | Loss Ratio |
|---|---|---|---|
| 2021-2022 | $40,000 | ${incurred * 0.2:,.0f} | {pct * 0.9:.1f}% |
| 2022-2023 | $40,000 | ${incurred * 0.2:,.0f} | {pct * 0.95:.1f}% |
| 2023-2024 | $40,000 | ${incurred * 0.25:,.0f} | {pct * 1.05:.1f}% |
| 2024-2025 | $40,000 | ${incurred * 0.2:,.0f} | {pct:.1f}% |
| 2025-2026 | $40,000 | ${incurred * 0.15:,.0f} | {pct * 0.85:.1f}% |
| 2021-2026 | ${earned:,.0f} | ${incurred:,.0f} | {pct:.1f}% |

## Claims
| DOL | Claim # | Type | Status | Incurred |
|-----|---------|------|--------|----------|
| 2022-01-10 | CLM-100 | Fire | Closed | ${incurred * 0.4:,.0f} |
| 2023-06-18 | CLM-220 | GL bodily injury | Open | ${incurred * 0.35:,.0f} |
| 2025-02-01 | CLM-330 | Theft | Closed | ${incurred * 0.25:,.0f} |

Prior carrier issued notice of non-renewal effective 2026-06-01.
"""


def _sov(insured: str, building: float, contents: float) -> str:
    return f"""# Schedule of Values — {insured}
| Loc | Building | Contents | BI | Total |
|-----|----------|----------|----|-------|
| 1 | ${building:,.0f} | ${contents:,.0f} | $0 | ${building + contents:,.0f} |
"""


def _inspection(insured: str, city: str, year_built: int = 2008, sqft: int = 45000) -> str:
    return f"""# Property Inspection Report
Insured: {insured}
Location: {city}
Inspector: Meridian Loss Control LLC
Date: 2026-06-15

Construction: masonry non-combustible, year built {year_built}, measured {sqft:,} sq ft.
Fully sprinklered (wet system, last tested 2025-11).
Housekeeping: Good. No hazardous storage observed.
Recommendations: Update COPE photos at renewal; verify roof age documentation.
"""


def _manuscript_supplement(insured: str) -> str:
    return f"""# Manuscript Endorsement Request — {insured}

Broker requests the following non-standard / manuscript wording:
1. Additional Insured — blanket contractual (manuscript form)
2. Waiver of subrogation — all contracts
3. Custom pollution buy-back endorsement outside ISO CG forms
4. Non-standard deductibles subject to manuscript side letter

This document contains legal terms that may modify policy coverage outside standard ISO endorsements.
"""


def build_all_scenarios() -> list[RealWorldScenario]:
    """Return the full real-world condition matrix."""
    scenarios: list[RealWorldScenario] = []

    # 1. Clean preferred retail — inland Austin, preferred NAICS, clean losses
    clean_name = "Hill Country Mercantile LLC"
    scenarios.append(
        RealWorldScenario(
            id="clean_retail_accept_path",
            title="Clean retail warehouse — Austin TX",
            condition="accept_path",
            insured_name=clean_name,
            acord_xml=_acord(
                name=clean_name,
                dba="Hill Country Mercantile",
                tax_id="74-8829103",
                address="4100 Industrial Blvd",
                city="Austin",
                state="TX",
                zip_code="78745",
                naics="424990",  # preferred 42x wholesale/distribution-ish — wait 42 is NOT in preferred
                # preferred: 44,45,53,54,56,62,72,81 — use 452210 Department Stores → 45
                building=2_400_000,
                contents=850_000,
                bi=200_000,
                occupancy="Retail / Warehouse",
                premium_property=31_500,
                premium_gl=14_200,
            ).replace("<NAICSCode>424990</NAICSCode>", "<NAICSCode>452210</NAICSCode>"),
            loss_run=_clean_loss_run(clean_name),
            schedule_of_values=_sov(clean_name, 2_400_000, 850_000),
            inspection_reports=(_inspection(clean_name, "Austin, TX"),),
            expectation=ScenarioExpectation(
                decision_in=("accept", "conditional_accept", "refer"),
                appetite_passed=True,
                quote_eligible=True,
                description="Preferred NAICS + inland TX + clean losses should pass appetite",
            ),
        )
    )

    # 2. Coastal Florida — hard appetite decline
    fl_name = "Gulfstream Condo Services Inc"
    scenarios.append(
        RealWorldScenario(
            id="coastal_fl_appetite_decline",
            title="Coastal Miami FL — CAT excluded",
            condition="decline",
            insured_name=fl_name,
            acord_xml=_acord(
                name=fl_name,
                dba="Gulfstream Condo",
                tax_id="65-4419288",
                address="1800 Collins Avenue",
                city="Miami Beach",
                state="FL",
                zip_code="33139",
                naics="531311",
                building=3_200_000,
                contents=400_000,
            ),
            loss_run=_clean_loss_run(fl_name),
            schedule_of_values=_sov(fl_name, 3_200_000, 400_000),
            expectation=ScenarioExpectation(
                decision_in=("decline",),
                appetite_passed=False,
                must_have_finding_substr=("Florida", "appetite", "Coastal"),
                description="Coastal FL zip must hard-decline at appetite",
            ),
        )
    )

    # 3. Excluded NAICS (hotels 7211)
    hotel_name = "Palm Court Hospitality Group LLC"
    scenarios.append(
        RealWorldScenario(
            id="excluded_naics_decline",
            title="Hotel NAICS 7211 — excluded industry",
            condition="decline",
            insured_name=hotel_name,
            acord_xml=_acord(
                name=hotel_name,
                dba="Palm Court Inn",
                tax_id="86-2291044",
                address="900 S Mill Avenue",
                city="Tempe",
                state="AZ",
                zip_code="85281",
                naics="721110",
                building=8_500_000,
                contents=1_200_000,
                occupancy="Hotel",
            ),
            loss_run=_clean_loss_run(hotel_name, earned=400_000, incurred=40_000),
            expectation=ScenarioExpectation(
                decision_in=("decline",),
                appetite_passed=False,
                must_have_finding_substr=("Excluded NAICS", "NAICS"),
                description="7211 hotels excluded from carrier appetite",
            ),
        )
    )

    # 4. Mega TIV > $25M
    mega_name = "Heartland Distribution Campus LP"
    scenarios.append(
        RealWorldScenario(
            id="mega_tiv_decline",
            title="Single-location TIV over $25M",
            condition="decline",
            insured_name=mega_name,
            acord_xml=_acord(
                name=mega_name,
                dba="Heartland Campus",
                tax_id="36-9988771",
                address="1 Logistics Way",
                city="Joliet",
                state="IL",
                zip_code="60436",
                naics="493110",
                building=22_000_000,
                contents=6_000_000,
                bi=2_000_000,
                occupancy="Warehouse",
            ),
            loss_run=_clean_loss_run(mega_name, earned=900_000, incurred=90_000),
            expectation=ScenarioExpectation(
                decision_in=("decline",),
                appetite_passed=False,
                must_have_finding_substr=("TIV exceeds", "25"),
                description="TIV above $25M requires facultative — appetite decline",
            ),
        )
    )

    # 5. Catastrophic loss ratio > 80%
    burn_name = "Red River Fabricators Inc"
    scenarios.append(
        RealWorldScenario(
            id="loss_ratio_hard_decline",
            title="92% five-year loss ratio",
            condition="decline",
            insured_name=burn_name,
            acord_xml=_acord(
                name=burn_name,
                dba="Red River Fab",
                tax_id="75-3344556",
                address="2200 Industrial Park Rd",
                city="Fort Worth",
                state="TX",
                zip_code="76106",
                naics="332710",
                building=1_800_000,
                contents=900_000,
                occupancy="Machine Shop",
            ),
            loss_run=_bad_loss_run(burn_name, ratio=0.92),
            schedule_of_values=_sov(burn_name, 1_800_000, 900_000),
            expectation=ScenarioExpectation(
                decision_in=("decline",),
                appetite_passed=False,
                must_have_finding_substr=("Loss ratio",),
                description="LR > 80% hard appetite decline",
            ),
        )
    )

    # 6. Elevated LR referral (65–80%) — continues pipeline with referral flag
    mid_name = "Prairie Office Suites LLC"
    scenarios.append(
        RealWorldScenario(
            id="loss_ratio_uw_referral",
            title="72% loss ratio — UW referral",
            condition="refer",
            insured_name=mid_name,
            acord_xml=_acord(
                name=mid_name,
                dba="Prairie Suites",
                tax_id="41-7788990",
                address="500 Nicollet Mall",
                city="Minneapolis",
                state="MN",
                zip_code="55402",
                naics="531120",
                building=4_200_000,
                contents=350_000,
                occupancy="Office",
            ),
            loss_run=_bad_loss_run(mid_name, ratio=0.72),
            schedule_of_values=_sov(mid_name, 4_200_000, 350_000),
            inspection_reports=(_inspection(mid_name, "Minneapolis, MN", year_built=1995, sqft=120000),),
            expectation=ScenarioExpectation(
                decision_in=("refer", "conditional_accept", "decline", "accept"),
                appetite_passed=False,  # high findings → passed=False with needs_uw_referral
                human_review_required=True,
                description="LR 65-80% should flag appetite referral and continue analysis",
            ),
        )
    )

    # 7. Missing loss run / incomplete package → validation REFER
    thin_name = "Barebones Broker Slip Co"
    scenarios.append(
        RealWorldScenario(
            id="missing_docs_refer",
            title="ACORD only — missing loss run & SOV",
            condition="missing_data",
            insured_name=thin_name,
            acord_xml=_acord(
                name=thin_name,
                dba="Barebones",
                tax_id="99-1112233",
                address="12 Main Street",
                city="Boise",
                state="ID",
                zip_code="83702",
                naics="541611",
                building=750_000,
                contents=125_000,
                occupancy="Office",
            ),
            loss_run=None,
            schedule_of_values=None,
            expectation=ScenarioExpectation(
                decision_in=("refer", "conditional_accept", "decline"),
                appetite_passed=True,
                human_review_required=True,
                must_have_finding_substr=("Missing required",),
                description="Incomplete docs must not silently ACCEPT",
            ),
        )
    )

    # 8. Manuscript / non-standard endorsements
    ms_name = "Cascade Specialty Foods Inc"
    scenarios.append(
        RealWorldScenario(
            id="manuscript_terms_refer",
            title="Manuscript endorsement package",
            condition="conditional",
            insured_name=ms_name,
            acord_xml=_acord(
                name=ms_name,
                dba="Cascade Specialty",
                tax_id="91-5566778",
                address="7700 NE 42nd Ave",
                city="Portland",
                state="OR",
                zip_code="97218",
                naics="445110",
                building=1_100_000,
                contents=680_000,
                occupancy="Specialty Grocery",
            ),
            loss_run=_clean_loss_run(ms_name),
            schedule_of_values=_sov(ms_name, 1_100_000, 680_000),
            inspection_reports=(_inspection(ms_name, "Portland, OR"),),
            supplemental_docs=(_manuscript_supplement(ms_name),),
            expectation=ScenarioExpectation(
                decision_in=("refer", "conditional_accept", "decline"),
                human_review_required=True,
                must_have_finding_substr=("manuscript", "Manuscript", "non-standard", "legal terms"),
                description="Manuscript wording must elevate review",
            ),
        )
    )

    # 9. Hawaii — out of appetite
    hi_name = "Pacific Rim Warehousing LLC"
    scenarios.append(
        RealWorldScenario(
            id="hawaii_appetite_decline",
            title="Hawaii location — ineligible",
            condition="decline",
            insured_name=hi_name,
            acord_xml=_acord(
                name=hi_name,
                dba="PRW Honolulu",
                tax_id="99-3344556",
                address="91-150 Kaomi Loop",
                city="Kapolei",
                state="HI",
                zip_code="96707",
                naics="493110",
                building=2_000_000,
                contents=500_000,
            ),
            loss_run=_clean_loss_run(hi_name),
            expectation=ScenarioExpectation(
                decision_in=("decline",),
                appetite_passed=False,
                must_have_finding_substr=("Hawaii",),
                description="HI hard decline",
            ),
        )
    )

    # 10. Non-preferred NAICS construction → referral (HIGH)
    const_name = "Ironclad Construction Partners LLC"
    scenarios.append(
        RealWorldScenario(
            id="construction_naics_referral",
            title="Construction NAICS 2362 — non-preferred",
            condition="refer",
            insured_name=const_name,
            acord_xml=_acord(
                name=const_name,
                dba="Ironclad Builders",
                tax_id="84-2211009",
                address="3500 Blake Street",
                city="Denver",
                state="CO",
                zip_code="80205",
                naics="236220",
                building=900_000,
                contents=200_000,
                occupancy="Contractor Yard",
                premium_gl=45_000,
                premium_property=18_000,
            ),
            loss_run=_clean_loss_run(const_name, earned=250_000, incurred=35_000),
            schedule_of_values=_sov(const_name, 900_000, 200_000),
            expectation=ScenarioExpectation(
                decision_in=("refer", "conditional_accept", "decline", "accept"),
                appetite_passed=False,
                human_review_required=True,
                must_have_finding_substr=("Non-preferred NAICS", "NAICS"),
                description="Construction NAICS should UW-refer at appetite",
            ),
        )
    )

    # 11. Government entity referral
    gov_name = "County of Cedar Public Works"
    scenarios.append(
        RealWorldScenario(
            id="government_entity_referral",
            title="Government entity name",
            condition="refer",
            insured_name=gov_name,
            acord_xml=_acord(
                name=gov_name,
                dba="Cedar PW",
                tax_id="39-6000001",
                address="1 Courthouse Square",
                city="Madison",
                state="WI",
                zip_code="53703",
                naics="921190",  # also excluded 9211 — will hard decline on NAICS
                building=1_500_000,
                contents=200_000,
                entity_type="Government",
            ),
            # Use preferred-looking office NAICS override so entity check is the HIGH signal
            # Actually 921190 starts with 9211 → CRITICAL excluded. Use different approach:
            loss_run=_clean_loss_run(gov_name),
            expectation=ScenarioExpectation(
                decision_in=("decline",),
                appetite_passed=False,
                description="Government NAICS 9211 excluded — decline",
            ),
        )
    )
    # Fix gov scenario: use office NAICS but government in name for HIGH referral
    scenarios[-1] = RealWorldScenario(
        id="government_entity_referral",
        title="Government entity — specialized UW",
        condition="refer",
        insured_name=gov_name,
        acord_xml=_acord(
            name=gov_name,
            dba="Cedar PW",
            tax_id="39-6000001",
            address="1 Courthouse Square",
            city="Madison",
            state="WI",
            zip_code="53703",
            naics="561210",  # facilities support — preferred 56
            building=1_500_000,
            contents=200_000,
            entity_type="Government",
        ),
        loss_run=_clean_loss_run(gov_name),
        schedule_of_values=_sov(gov_name, 1_500_000, 200_000),
        expectation=ScenarioExpectation(
            decision_in=("refer", "conditional_accept", "decline", "accept"),
            appetite_passed=False,
            human_review_required=True,
            must_have_finding_substr=("Government",),
            description="Government entity name → HIGH appetite referral",
        ),
    )

    # 12. Coastal TX Galveston zip band
    tx_name = "Bayport Marine Supply LLC"
    scenarios.append(
        RealWorldScenario(
            id="coastal_tx_appetite_decline",
            title="Coastal Texas Galveston zip",
            condition="decline",
            insured_name=tx_name,
            acord_xml=_acord(
                name=tx_name,
                dba="Bayport Marine",
                tax_id="76-4455667",
                address="2500 Strand Street",
                city="Galveston",
                state="TX",
                zip_code="77550",
                naics="441222",
                building=1_200_000,
                contents=800_000,
            ),
            loss_run=_clean_loss_run(tx_name),
            expectation=ScenarioExpectation(
                decision_in=("decline",),
                appetite_passed=False,
                must_have_finding_substr=("Coastal Texas", "Texas"),
                description="TX coastal zip 775xx decline",
            ),
        )
    )

    # 13. Below-minimum TIV (HIGH referral, not critical)
    tiny_name = "Corner Kiosk Ventures LLC"
    scenarios.append(
        RealWorldScenario(
            id="below_min_tiv_referral",
            title="TIV under $50k minimum",
            condition="refer",
            insured_name=tiny_name,
            acord_xml=_acord(
                name=tiny_name,
                dba="Corner Kiosk",
                tax_id="82-1002003",
                address="88 Market Street",
                city="Salt Lake City",
                state="UT",
                zip_code="84101",
                naics="445120",
                building=25_000,
                contents=15_000,
                premium_property=800,
                premium_gl=1_200,
                occupancy="Kiosk Retail",
            ),
            loss_run=_clean_loss_run(tiny_name, earned=15_000, incurred=500),
            expectation=ScenarioExpectation(
                decision_in=("refer", "conditional_accept", "decline", "accept"),
                appetite_passed=False,
                human_review_required=True,
                must_have_finding_substr=("TIV below", "minimum"),
                description="Sub-$50k TIV → HIGH referral",
            ),
        )
    )

    # 14. Discrepancy-rich package (COPE mismatch inspection)
    disc_name = "Lakeside Plastics Manufacturing Inc"
    scenarios.append(
        RealWorldScenario(
            id="cope_discrepancy_package",
            title="ACORD vs inspection COPE conflicts",
            condition="refer",
            insured_name=disc_name,
            acord_xml=_acord(
                name=disc_name,
                dba="Lakeside Plastics",
                tax_id="39-8877665",
                address="1400 Polymer Drive",
                city="Sheboygan",
                state="WI",
                zip_code="53081",
                naics="326199",
                building=5_500_000,
                contents=2_100_000,
                year_built=2010,
                sqft=175000,
                construction="Fire Resistive",
                occupancy="Plastics Manufacturing",
            ),
            loss_run=_clean_loss_run(disc_name, earned=320_000, incurred=48_000),
            schedule_of_values=_sov(disc_name, 5_500_000, 2_100_000),
            inspection_reports=(
                f"""# Inspection — {disc_name}
Year built: 1988 (not 2010). Measured square footage: 152,400 (not 175,000).
Construction: unprotected steel frame (not fire resistive).
Sprinklers: PARTIAL only — warehouse annex dry system impaired.
Protection class: ISO 6 (submission shows 4).
Flammable resin storage exceeds disclosed quantities.
""",
            ),
            expectation=ScenarioExpectation(
                decision_in=("refer", "conditional_accept", "decline", "accept"),
                human_review_required=True,
                description="Material COPE conflicts should drive human review",
            ),
        )
    )

    return scenarios


def scenario_by_id(scenario_id: str) -> RealWorldScenario:
    for s in build_all_scenarios():
        if s.id == scenario_id:
            return s
    raise KeyError(f"Unknown scenario: {scenario_id}")


def run_scenario(scenario: RealWorldScenario, *, org_id: str = "realworld-test") -> dict[str, Any]:
    """Execute InsurancePipeline for one scenario (deterministic, no LLM required)."""
    from insureflow.insurance.pipeline import InsurancePipeline

    pipeline = InsurancePipeline(org_id=org_id, use_llm=False)
    result = pipeline.run(
        acord_xml=scenario.acord_xml,
        loss_run=scenario.loss_run,
        schedule_of_values=scenario.schedule_of_values,
        inspection_reports=list(scenario.inspection_reports) or None,
        supplemental_docs=list(scenario.supplemental_docs) or None,
        bundle_id=f"rw-{scenario.id}",
        skip_oracles=False,
        skip_portfolio=False,
        skip_core_integration=True,  # avoid simulated core noise in matrix runs
    )
    return result


def evaluate_result(scenario: RealWorldScenario, result: dict[str, Any]) -> list[str]:
    """Return list of assertion failure messages (empty = pass)."""
    failures: list[str] = []
    exp = scenario.expectation
    decision = str(result.get("ai_decision") or "").lower()
    if decision not in exp.decision_in:
        failures.append(f"decision={decision!r} not in {exp.decision_in}")

    if exp.appetite_passed is not None:
        actual = bool(result.get("appetite_filter_passed"))
        if actual != exp.appetite_passed:
            failures.append(f"appetite_passed={actual} expected {exp.appetite_passed}")

    if exp.human_review_required is True and not result.get("human_review_required"):
        # Appetite hard-declines may complete without UW review flag
        if decision != "decline":
            failures.append("expected human_review_required=True")

    if exp.quote_eligible is not None:
        eligible = (result.get("quote") or {}).get("eligible")
        if eligible is not None and bool(eligible) != exp.quote_eligible:
            failures.append(f"quote.eligible={eligible} expected {exp.quote_eligible}")

    if exp.must_have_finding_substr:
        blob = _findings_blob(result)
        if not any(s.lower() in blob for s in exp.must_have_finding_substr):
            failures.append(f"missing expected finding containing one of {exp.must_have_finding_substr}")

    return failures


def _findings_blob(result: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.append(str(result.get("decline_reason") or ""))
    parts.append(str(result.get("appetite_reason") or ""))
    memo = result.get("memo") or {}
    for f in memo.get("key_findings") or []:
        if isinstance(f, dict):
            parts.append(str(f.get("title") or ""))
            parts.append(str(f.get("description") or ""))
        else:
            parts.append(str(f))
    for reason in memo.get("human_review_reasons") or []:
        parts.append(str(reason))
    return " ".join(parts).lower()


def run_all_scenarios(
    *,
    org_id: str = "realworld-test",
    filter_fn: Callable[[RealWorldScenario], bool] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in build_all_scenarios():
        if filter_fn and not filter_fn(scenario):
            continue
        result = run_scenario(scenario, org_id=org_id)
        failures = evaluate_result(scenario, result)
        rows.append(
            {
                "id": scenario.id,
                "title": scenario.title,
                "condition": scenario.condition,
                "decision": result.get("ai_decision"),
                "appetite_passed": result.get("appetite_filter_passed"),
                "human_review": result.get("human_review_required"),
                "quote_eligible": (result.get("quote") or {}).get("eligible"),
                "passed": not failures,
                "failures": failures,
                "bundle_id": result.get("bundle_id"),
            }
        )
    return rows
