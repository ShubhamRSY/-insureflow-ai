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
    date_of_loss: date
    line_of_business: str
    cause: str
    description: str = ""
    incurred_amount: float
    paid_amount: float = 0.0
    open_reserve: float = 0.0
    claim_status: ClaimStatus = ClaimStatus.OPEN
    location: Optional[str] = None
    notes: str = ""


class LossRunData(BaseModel):
    total_claims: int = 0
    total_incurred: float = 0.0
    total_paid: float = 0.0
    total_open_reserves: float = 0.0
    claims: list[ClaimRecord] = Field(default_factory=list)
    loss_ratios: dict[str, float] = Field(default_factory=dict)


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


class FinancialData(BaseModel):
    total_asset_value: Optional[float] = None
    annual_revenue: Optional[float] = None
    payroll: Optional[float] = None
    prior_losses: list[dict[str, Any]] = Field(default_factory=list)
    loss_run: Optional[LossRunData] = None
    credit_rating: Optional[str] = None


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

    raw_xml: Optional[str] = None
    raw_json: Optional[str] = None
    parsed_at: Optional[datetime] = None


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

    def all_sources(self) -> list[str]:
        sources = []
        if self.structured:
            sources.append(self.structured.source)
        for u in self.unstructured:
            sources.append(u.source)
        for s in self.supplemental:
            sources.append(s.source)
        return sources
