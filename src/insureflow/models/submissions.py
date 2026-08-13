from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SubmissionStatus(str, Enum):
    RECEIVED = "received"
    PENDING_APPETITE_CHECK = "pending_appetite_check"
    APPETITE_DECLINED = "appetite_declined"
    PARSING = "parsing"
    PARSED = "parsed"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    EXTERNAL_ORACLE_CHECK = "external_oracle_check"
    RECONCILING = "reconciling"
    RECONCILED = "reconciled"
    SYNTHESIZING = "synthesizing"
    PORTFOLIO_REVIEW = "portfolio_review"
    REINSURANCE_REVIEW = "reinsurance_review"
    COMPLETED = "completed"
    FAILED = "failed"
    FLAGGED = "flagged"


class DocumentType(str, Enum):
    ACORD_XML = "acord_xml"
    BROKER_API_JSON = "broker_api_json"
    INSPECTION_REPORT = "inspection_report"
    LOSS_RUN = "loss_run"
    SCHEDULE_OF_VALUES = "schedule_of_values"
    FINANCIAL_STATEMENT = "financial_statement"
    FLOOR_PLAN = "floor_plan"
    SUPPLEMENTAL = "supplemental"


class ClaimStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING_LITIGATION = "pending_litigation"
    SUBROGATION = "subrogation"


class PolicyPeriod(BaseModel):
    effective_date: date
    expiration_date: date
    is_bound: bool = False


class NamedInsured(BaseModel):
    legal_name: str
    dba: Optional[str] = None
    tax_id: Optional[str] = None
    entity_type: Optional[str] = None
    address: Optional[str] = None


class BrokerInfo(BaseModel):
    broker_name: str
    broker_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    agency: Optional[str] = None


class CoverageDetail(BaseModel):
    coverage_type: str
    limit_amount: float
    deductible: float
    premium: float
    sublimits: dict[str, float] = Field(default_factory=dict)
    endorsements: list[str] = Field(default_factory=list)


class LocationData(BaseModel):
    address: str
    city: str
    state: str
    zip_code: str
    building_occupancy: Optional[str] = None
    year_built: Optional[int] = None
    square_footage: Optional[float] = None
    construction_type: Optional[str] = None
    protection_class: Optional[int] = None
    building_value: Optional[float] = None
    contents_value: Optional[float] = None
    bi_value: Optional[float] = None


class ClaimRecord(BaseModel):
    claim_id: str
    date_of_loss: date  # accident date — the loss occurrence date (CAS data organization)
    line_of_business: str
    cause: str
    description: str = ""
    incurred_amount: float
    paid_amount: float = 0.0
    open_reserve: float = 0.0
    claim_status: ClaimStatus = ClaimStatus.OPEN
    location: Optional[str] = None
    notes: str = ""
    # CAS reserving-standard timing fields (see docs/underwriting standards):
    date_reported: Optional[date] = None  # report date — first reported to the insurer
    date_closed: Optional[date] = None  # date the claim was settled/closed
    valuation_date: Optional[date] = None  # date through which transactions are valued
    reopened: bool = False  # closed claim reopened (reopened-claims potential)
    # Confidence that this claim was extracted faithfully from the source document
    # (0.0 = unknown/untrusted, 1.0 = fully verified). Computed by the parser from
    # extraction signals (table completeness, cross-source agreement, format).
    extraction_confidence: float = 0.0


class LossRunData(BaseModel):
    total_claims: int = 0
    total_incurred: float = 0.0
    total_paid: float = 0.0
    total_open_reserves: float = 0.0
    claims: list[ClaimRecord] = Field(default_factory=list)
    loss_ratios: dict[str, float] = Field(default_factory=dict)
    earned_premium: float = 0.0
    written_premium: float = 0.0


class ScheduleItem(BaseModel):
    item_number: str = ""
    description: str
    value: float = 0.0
    limit: Optional[float] = None
    coinsurance_pct: Optional[float] = None
    deductible: Optional[float] = None
    location_ref: Optional[str] = None


class ScheduleOfValues(BaseModel):
    schedule_type: str = ""
    coverage_type: str = ""
    items: list[ScheduleItem] = Field(default_factory=list)
    total_value: float = 0.0
    template_version: str = ""


class FinancialData(BaseModel):
    total_asset_value: Optional[float] = None
    annual_revenue: Optional[float] = None
    payroll: Optional[float] = None
    employee_count: Optional[int] = None
    prior_losses: list[dict[str, Any]] = Field(default_factory=list)
    loss_run: Optional[LossRunData] = None
    credit_rating: Optional[str] = None

    # ── Financial-statement line items (FinancialStatementParser) ──
    statement_type: Optional[str] = None  # balance_sheet | income_statement | cash_flow | tax_return | combined
    as_of_date: Optional[str] = None  # "2025-12-31" — statement period end
    fiscal_year: Optional[str] = None  # e.g. "2025"
    audit_type: Optional[str] = None  # audited | reviewed | compiled | internal
    is_audited: Optional[bool] = None

    # Balance sheet
    current_assets: Optional[float] = None
    total_assets: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    shareholder_equity: Optional[float] = None
    total_equity: Optional[float] = None

    # Income statement
    net_income: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    ebitda: Optional[float] = None


class FloorPlanData(BaseModel):
    """Schematic / floor-plan features extracted from a plan, drawing, or survey."""

    floor_area_sqft: Optional[float] = None
    floor_area_m2: Optional[float] = None
    number_of_stories: Optional[int] = None
    fire_compartments: Optional[int] = None
    compartmentalization: Optional[str] = None  # open | compartmented | mixed | unknown
    number_of_exits: Optional[int] = None
    exit_types: list[str] = Field(default_factory=list)
    stairwells: Optional[int] = None
    fire_alarm: Optional[str] = None  # yes | no | unknown
    sprinklered: Optional[str] = None  # yes | no | partial | unknown
    notes: str = ""
    source: str = ""


class RiskProfile(BaseModel):
    naics_code: Optional[str] = None
    sic_code: Optional[str] = None
    ncci_class_code: Optional[str] = None
    business_description: Optional[str] = None
    occupancy_type: Optional[str] = None
    construction_type: Optional[str] = None
    protection_class: Optional[int] = None
    sprinklered: Optional[bool] = None
    number_of_stories: Optional[int] = None
    total_square_footage: Optional[float] = None
    prior_claims: list[ClaimRecord] = Field(default_factory=list)
    safety_certifications: list[str] = Field(default_factory=list)


class StructuredSubmission(BaseModel):
    submission_id: str
    source: str = "broker_acord_xml"
    received_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    named_insured: Optional[NamedInsured] = None
    broker: Optional[BrokerInfo] = None
    policy_period: Optional[PolicyPeriod] = None
    coverages: list[CoverageDetail] = Field(default_factory=list)
    locations: list[LocationData] = Field(default_factory=list)
    financial: Optional[FinancialData] = None
    risk_profile: Optional[RiskProfile] = None
    schedule_of_values: list[ScheduleOfValues] = Field(default_factory=list)
    floor_plan: Optional[FloorPlanData] = None
    # Detected ACORD form numbers for the submission (e.g. "125", "126",
    # "130", "140"), sourced from <FormNumber> elements, "ACORD <n>" mentions,
    # or coverage-derived inference.
    acord_forms: list[str] = Field(default_factory=list)

    raw_xml: Optional[str] = None
    raw_json: Optional[str] = None
    parsed_at: Optional[datetime] = None

    # Per-field extraction confidence keyed by the same dotted paths emitted by
    # provenance (e.g. "named_insured.legal_name", "coverage.0.limit"). Values
    # are computed from extraction signals (typed element present, coercion
    # success, cross-field agreement) and consulted when provenance builds
    # field nodes and when reconciliation resolves conflicts.
    field_confidence: dict[str, float] = Field(default_factory=dict)
    # Human-readable notes about extraction quality per field path (e.g. a
    # defaulted value because the source element was missing).
    field_notes: dict[str, str] = Field(default_factory=dict)


class UnstructuredSubmission(BaseModel):
    submission_id: str
    source: str = "inspection_report"
    document_type: str = "inspection_report"
    received_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    raw_text: str = ""
    chunks: list[ExtractedChunk] = Field(default_factory=list)
    extracted_fields: dict[str, list[ExtractedField]] = Field(default_factory=dict)
    processed_at: Optional[datetime] = None


class ExtractedChunk(BaseModel):
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    page_number: Optional[int] = None


class ExtractedField(BaseModel):
    field_name: str
    value: str
    confidence: float = 0.0
    context: str = ""
    chunk_index: int = 0
    page_number: Optional[int] = None


class SubmissionBundle(BaseModel):
    bundle_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    status: SubmissionStatus = SubmissionStatus.RECEIVED

    structured: Optional[StructuredSubmission] = None
    unstructured: list[UnstructuredSubmission] = Field(default_factory=list)
    supplemental: list[UnstructuredSubmission] = Field(default_factory=list)
    visual_analysis: Optional[dict[str, Any]] = None

    def all_sources(self) -> list[str]:
        sources = []
        if self.structured:
            sources.append(self.structured.source)
        for u in self.unstructured:
            sources.append(u.source)
        for s in self.supplemental:
            sources.append(s.source)
        return sources
