from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class GuidelineCategory(str, Enum):
    CONSTRUCTION = "construction"
    PROTECTION = "protection"
    OCCUPANCY = "occupancy"
    VALUATION = "valuation"
    COVERAGE = "coverage"
    LOSS_HISTORY = "loss_history"
    COMPLIANCE = "compliance"
    GENERAL = "general"
    CARRIER_APPETITE = "carrier_appetite"


class GuidelineSource(str, Enum):
    ISO = "iso"
    AAIS = "aais"
    NCCI = "ncci"
    COMPANY = "company"
    REGULATORY = "regulatory"
    INDUSTRY_STANDARD = "industry_standard"


class Guideline(BaseModel):
    id: str
    category: GuidelineCategory
    source: GuidelineSource
    title: str
    content: str
    keywords: list[str] = Field(default_factory=list)
    risk_impact: str = "medium"
    applies_to_naics: list[str] = Field(default_factory=list)


class UnderwritingGuidelines(BaseModel):
    guidelines: list[Guideline] = Field(default_factory=list)

    def by_category(self, category: GuidelineCategory) -> list[Guideline]:
        return [g for g in self.guidelines if g.category == category]

    def search_keywords(self, terms: list[str]) -> list[Guideline]:
        return [
            g
            for g in self.guidelines
            if any(t.lower() in " ".join(g.keywords).lower() for t in terms)
        ]


def builtin_carrier_appetite_rules() -> UnderwritingGuidelines:
    """Strict carrier appetite / eligibility rules for fast-fail filtering."""
    return UnderwritingGuidelines(
        guidelines=[
            Guideline(
                id="APT-001",
                category=GuidelineCategory.CARRIER_APPETITE,
                source=GuidelineSource.COMPANY,
                title="NAICS Code Eligibility",
                content="Decline any risk with NAICS code in the following excluded industries: 7211 (casinos), 1133 (logging), 2131 (mining support), 4821 (rail transport), 4911 (postal service), 9211 (military). Preferred NAICS: 44-45 (retail), 53 (real estate), 54 (professional services), 56 (admin support), 62 (healthcare), 72 (accommodation/food excluding casinos), 81 (other services).",
                keywords=["naics", "industry", "eligible", "excluded", "decline"],
                risk_impact="high",
            ),
            Guideline(
                id="APT-002",
                category=GuidelineCategory.CARRIER_APPETITE,
                source=GuidelineSource.COMPANY,
                title="Minimum Premium Threshold",
                content="Minimum annual premium of $2,500 for any new business policy. Risks generating less than $2,500 in estimated premium are ineligible. Maximum annual premium of $250,000 without facultative reinsurance approval.",
                keywords=["premium", "minimum", "maximum", "threshold", "reinsurance"],
                risk_impact="high",
            ),
            Guideline(
                id="APT-003",
                category=GuidelineCategory.CARRIER_APPETITE,
                source=GuidelineSource.COMPANY,
                title="Geographic Restrictions (CAT Exposure)",
                content="No new business in coastal FL (zip codes 32000-34999), coastal TX (77500-78500), or HI. Louisiana and Mississippi coastal counties require additional CAT modeling and are ineligible for habitational risks. California wildfire zones (zip codes in high/Very High Fire Hazard Severity Zones per CalFire) are ineligible without fire suppression credits.",
                keywords=[
                    "geographic",
                    "coastal",
                    "florida",
                    "texas",
                    "california",
                    "cat",
                    "wildfire",
                    "hurricane",
                ],
                risk_impact="high",
            ),
            Guideline(
                id="APT-004",
                category=GuidelineCategory.CARRIER_APPETITE,
                source=GuidelineSource.COMPANY,
                title="Loss Ratio Eligibility",
                content="Accounts with a 5-year loss ratio exceeding 65% require underwriter referral. Accounts with a 5-year loss ratio exceeding 80% are ineligible for new business. Accounts with zero prior insurance history (no prior carrier) in the last 3 years require additional due diligence.",
                keywords=["loss ratio", "eligibility", "referral", "decline", "prior insurance"],
                risk_impact="high",
            ),
            Guideline(
                id="APT-005",
                category=GuidelineCategory.CARRIER_APPETITE,
                source=GuidelineSource.COMPANY,
                title="Minimum Years in Business",
                content="The named insured entity must have been in operation for a minimum of 2 years at the time of application. Startups and entities less than 2 years old require licensed UW exception with additional financial verification.",
                keywords=["years in business", "startup", "new venture", "operation history"],
                risk_impact="high",
            ),
            Guideline(
                id="APT-006",
                category=GuidelineCategory.CARRIER_APPETITE,
                source=GuidelineSource.COMPANY,
                title="Maximum TIV Per Location",
                content="Maximum total insured value per location is $25,000,000. Single locations exceeding $25M TIV require facultative reinsurance. Multi-location accounts with any location over $50M TIV require automatic facultative binding. Minimum TIV of $50,000 per location.",
                keywords=["tiv", "maximum", "location", "facultative", "reinsurance"],
                risk_impact="high",
            ),
            Guideline(
                id="APT-007",
                category=GuidelineCategory.CARRIER_APPETITE,
                source=GuidelineSource.COMPANY,
                title="Entity Type Restrictions",
                content="Government entities, non-profit organizations with annual revenue exceeding $10M, and religious institutions require specialized underwriting and are not eligible for standard appetite. Publicly traded companies with market cap under $50M require additional financial review.",
                keywords=[
                    "entity",
                    "government",
                    "nonprofit",
                    "religious",
                    "public",
                    "restriction",
                ],
                risk_impact="medium",
            ),
            Guideline(
                id="APT-008",
                category=GuidelineCategory.CARRIER_APPETITE,
                source=GuidelineSource.COMPANY,
                title="Prior Carrier Cancellation / Non-Renewal",
                content="Any applicant that has been cancelled or non-renewed by a prior carrier within the last 3 years is ineligible for standard appetite. Prior declination for the same risk from any admitted carrier in the last 12 months requires automatic referral to senior UW.",
                keywords=[
                    "cancellation",
                    "nonrenewal",
                    "non-renewal",
                    "declination",
                    "prior carrier",
                ],
                risk_impact="high",
            ),
        ]
    )


def builtin_guidelines() -> UnderwritingGuidelines:
    return UnderwritingGuidelines(
        guidelines=[
            Guideline(
                id="CON-001",
                category=GuidelineCategory.CONSTRUCTION,
                source=GuidelineSource.ISO,
                title="Frame Construction Maximum Exposure",
                content="Frame construction (Class 1) is restricted to a maximum per-building TIV of $2,000,000 and no more than 3 stories. Sprinklered frame may extend to $3,000,000 with approved protective safeguards.",
                keywords=["frame", "construction", "class 1", "stories", "tiv", "exposure"],
                risk_impact="high",
            ),
            Guideline(
                id="CON-002",
                category=GuidelineCategory.CONSTRUCTION,
                source=GuidelineSource.ISO,
                title="Masonry Construction Guidelines",
                content="Masonry (Class 2) and masonry-joist (Class 3) construction: maximum per-building TIV of $10,000,000. No more than 6 stories without engineered fire suppression review. Acceptable for most occupancy classes with proper protection class.",
                keywords=["masonry", "class 2", "class 3", "stories", "tiv"],
                risk_impact="medium",
            ),
            Guideline(
                id="CON-003",
                category=GuidelineCategory.CONSTRUCTION,
                source=GuidelineSource.ISO,
                title="Fire Resistive Construction",
                content="Fire resistive (Class 6) and modified fire resistive (Class 5) construction: maximum per-building TIV of $50,000,000. No story limit with approved fire suppression. Preferred for high-value and high-occupancy risks.",
                keywords=["fire resistive", "class 5", "class 6", "tiv", "high-value"],
                risk_impact="low",
            ),
            Guideline(
                id="PRO-001",
                category=GuidelineCategory.PROTECTION,
                source=GuidelineSource.ISO,
                title="Protection Class 4 Requirements",
                content="Protection Class 4 (PC 4) requires automatic sprinkler systems for any building exceeding 25,000 sq ft or 3 stories. Buildings under 25,000 sq ft may qualify without sprinklers if construction is masonry or better and distance to fire station is under 5 miles.",
                keywords=["protection class", "pc 4", "sprinkler", "square footage", "stories"],
                risk_impact="high",
            ),
            Guideline(
                id="PRO-002",
                category=GuidelineCategory.PROTECTION,
                source=GuidelineSource.ISO,
                title="Protection Class 5-6 Requirements",
                content="Protection Class 5 or 6: automatic sprinklers required for ALL buildings. Remote monitoring (central station alarm) required. Maximum TIV of $5,000,000 per location. No wood frame construction accepted.",
                keywords=["protection class", "pc 5", "pc 6", "sprinkler", "monitoring", "tiv"],
                risk_impact="high",
            ),
            Guideline(
                id="PRO-003",
                category=GuidelineCategory.PROTECTION,
                source=GuidelineSource.ISO,
                title="Protection Class 7-10 Requirements",
                content="Protection Class 7 through 10: maximum TIV of $1,000,000 per location. Full automatic sprinkler system with remote monitoring mandatory. No unprotected openings. Only masonry or fire resistive construction accepted. Not eligible for habitational or manufacturing risks.",
                keywords=["protection class", "pc 7", "pc 8", "pc 9", "pc 10", "tiv"],
                risk_impact="high",
            ),
            Guideline(
                id="OCC-001",
                category=GuidelineCategory.OCCUPANCY,
                source=GuidelineSource.ISO,
                title="Manufacturing Occupancy Restrictions",
                content="Manufacturing occupancy: automatic sprinklers required for buildings over 10,000 sq ft. Maximum TIV of $15,000,000 per location. Welding, grinding, or hot-work operations require separate occupancy limits. Combustible dust operations (woodworking, grain, metal grinding) require additional dust collection safeguards and increased protection class standards.",
                keywords=[
                    "manufacturing",
                    "occupancy",
                    "sprinkler",
                    "hot work",
                    "combustible dust",
                ],
                risk_impact="high",
            ),
            Guideline(
                id="OCC-002",
                category=GuidelineCategory.OCCUPANCY,
                source=GuidelineSource.ISO,
                title="Warehouse Occupancy Guidelines",
                content="Warehouse occupancy: maximum TIV of $20,000,000 per location. Storage height limited to 30 feet in sprinklered buildings, 20 feet in unsprinklered. Commodity classification required for rack storage. Flammable/combustible liquid storage subject to separate limit of $500,000.",
                keywords=["warehouse", "occupancy", "storage height", "commodity", "flammable"],
                risk_impact="medium",
            ),
            Guideline(
                id="OCC-003",
                category=GuidelineCategory.OCCUPANCY,
                source=GuidelineSource.ISO,
                title="Habitational Occupancy Standards",
                content="Habitational (apartments, condos, townhouses): maximum 5 stories without elevator. Automatic sprinklers mandatory for buildings over 30,000 sq ft or 4+ stories. Roof construction must be Class B or better. $5,000,000 maximum per-building TIV. No attached commercial units without separate fire barriers.",
                keywords=["habitational", "apartment", "condo", "sprinkler", "stories", "roof"],
                risk_impact="medium",
            ),
            Guideline(
                id="VAL-001",
                category=GuidelineCategory.VALUATION,
                source=GuidelineSource.INDUSTRY_STANDARD,
                title="Coinsurance Clause Requirements",
                content="Property policies must maintain at least 80% coinsurance on all buildings. Risks with actual TIV exceeding 90% of reported values require 100% coinsurance or an Agreed Value endorsement. Underinsurance beyond 25% triggers mandatory appraisal.",
                keywords=["coinsurance", "tiv", "underinsurance", "agreed value", "appraisal"],
                risk_impact="high",
            ),
            Guideline(
                id="VAL-002",
                category=GuidelineCategory.VALUATION,
                source=GuidelineSource.INDUSTRY_STANDARD,
                title="Replacement Cost Valuation Standards",
                content="All commercial property must be insured at replacement cost (RC) unless the building is over 50 years old or of historic designation, in which case Functional Replacement Cost (FRC) is acceptable. Actual Cash Value (ACV) is permitted only for buildings over 75 years old or with prior ACV endorsements.",
                keywords=["replacement cost", "rc", "acv", "frc", "valuation", "historic"],
                risk_impact="medium",
            ),
            Guideline(
                id="LOS-001",
                category=GuidelineCategory.LOSS_HISTORY,
                source=GuidelineSource.NCCI,
                title="Large Loss Frequency Thresholds",
                content="Three or more claims exceeding $50,000 in the past 3 years constitutes a large loss pattern. Two or more claims exceeding $100,000 in the past 3 years is considered severe. One claim exceeding $250,000 triggers mandatory catastrophic loss review and possible schedule rating adjustment.",
                keywords=["large loss", "claims", "frequency", "threshold", "schedule rating"],
                risk_impact="high",
            ),
            Guideline(
                id="LOS-002",
                category=GuidelineCategory.LOSS_HISTORY,
                source=GuidelineSource.NCCI,
                title="Loss Ratio Underwriting Guidelines",
                content="Accounts with a 5-year loss ratio exceeding 65% require a underwriter referral. Loss ratio over 75% is considered marginal and requires non-renewal consideration unless significant risk improvements are documented. Loss ratio over 90% requires decline or non-renewal.",
                keywords=[
                    "loss ratio",
                    "underwriter referral",
                    "marginal",
                    "non-renewal",
                    "decline",
                ],
                risk_impact="high",
            ),
            Guideline(
                id="COM-001",
                category=GuidelineCategory.COMPLIANCE,
                source=GuidelineSource.REGULATORY,
                title="State-Specific Compliance Requirements",
                content="All policies must comply with applicable state filing requirements. Surplus lines coverage requires affidavits filed within 30 days. State-specific cancellation and non-renewal notice periods apply. CAT-exposed coastal properties require separate wind/hail deductibles.",
                keywords=[
                    "compliance",
                    "state",
                    "surplus lines",
                    "cancellation",
                    "coastal",
                    "deductible",
                ],
                risk_impact="high",
            ),
            Guideline(
                id="COM-002",
                category=GuidelineCategory.COMPLIANCE,
                source=GuidelineSource.REGULATORY,
                title="Named Insured Verification Standards",
                content="The named insured on all policies must match the legal entity name as registered with the Secretary of State. DBAs must be listed as additional named insureds. Partnership and LLC structures require all partners/members to be listed. Trusts require trustee designation.",
                keywords=["named insured", "entity", "dba", "partnership", "llc", "trust"],
                risk_impact="medium",
            ),
            Guideline(
                id="COV-001",
                category=GuidelineCategory.COVERAGE,
                source=GuidelineSource.COMPANY,
                title="Sublimit Adequacy Standards",
                content="Ordinance or Law sublimits must be at least 25% of the building limit. Debris Removal sublimit must be at least $100,000 or 10% of the total limit, whichever is greater. Service Interruption coverage is recommended for all habitational risks with 50+ units.",
                keywords=["sublimit", "ordinance", "law", "debris removal", "coverage"],
                risk_impact="medium",
            ),
            Guideline(
                id="COV-002",
                category=GuidelineCategory.COVERAGE,
                source=GuidelineSource.INDUSTRY_STANDARD,
                title="Deductible Guidelines by Risk Tier",
                content="Preferred risks: minimum deductible of $1,000, standard $2,500. Standard risks: $2,500 minimum, standard $5,000. Non-preferred risks: $5,000 minimum, standard $10,000. Deductible buy-down programs available for qualified accounts with 3+ years loss-free.",
                keywords=["deductible", "preferred", "standard", "non-preferred", "buy-down"],
                risk_impact="low",
            ),
            Guideline(
                id="GEN-001",
                category=GuidelineCategory.GENERAL,
                source=GuidelineSource.COMPANY,
                title="Total Insured Value Concentration",
                content="No single location should exceed 40% of the total portfolio TIV. Single-location risks with TIV over $25,000,000 require cession to facultative reinsurance markets. Multi-location accounts with any location over $50,000,000 require automatic facultative binding authority.",
                keywords=["tiv", "concentration", "reinsurance", "facultative", "portfolio"],
                risk_impact="high",
            ),
            Guideline(
                id="GEN-002",
                category=GuidelineCategory.GENERAL,
                source=GuidelineSource.COMPANY,
                title="New Business Submission Requirements",
                content="New business submissions must include: completed ACORD application (all schedules), 5-year loss runs, financial statements (3 years), SOV with building valuations, inspection report if TIV exceeds $2,000,000 or risk is in protection class 6 or worse. Missing items require underwriter exception with 14-day follow-up.",
                keywords=["new business", "submission", "acord", "loss runs", "financials", "sov"],
                risk_impact="medium",
            ),
        ]
    )
