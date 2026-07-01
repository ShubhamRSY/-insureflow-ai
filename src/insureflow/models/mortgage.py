from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProductLine(str, Enum):
    INSURANCE = "insurance"
    RESIDENTIAL_MORTGAGE = "residential_mortgage"
    COMMERCIAL_MORTGAGE = "commercial_mortgage"


class MortgageDocumentType(str, Enum):
    W2 = "w2"
    PAY_STUB = "pay_stub"
    TAX_RETURN_1040 = "tax_return_1040"
    TAX_RETURN_1065 = "tax_return_1065"
    PROFIT_LOSS = "profit_loss"
    SCHEDULE_C = "schedule_c"
    BANK_STATEMENT = "bank_statement"
    INVESTMENT_STATEMENT = "investment_statement"
    RETIREMENT_401K = "retirement_401k"
    GIFT_LETTER = "gift_letter"
    CREDIT_REPORT = "credit_report"
    CREDIT_CARD_STATEMENT = "credit_card_statement"
    AUTO_LOAN_STATEMENT = "auto_loan_statement"
    STUDENT_LOAN_STATEMENT = "student_loan_statement"
    RENT_HISTORY = "rent_history"
    RESIDENTIAL_APPRAISAL = "residential_appraisal"
    COMMERCIAL_APPRAISAL = "commercial_appraisal"
    PURCHASE_AGREEMENT = "purchase_agreement"
    HOMEOWNERS_INSURANCE = "homeowners_insurance"
    GOVERNMENT_ID = "government_id"
    DIVORCE_DECREE = "divorce_decree"
    BALANCE_SHEET = "balance_sheet"
    COMMERCIAL_LEASE = "commercial_lease"
    TENANT_ESTOPPEL = "tenant_estoppel"
    RENT_ROLL = "rent_roll"
    OPERATING_STATEMENT = "operating_statement"
    BUSINESS_CREDIT_REPORT = "business_credit_report"
    BUSINESS_DEBT_SCHEDULE = "business_debt_schedule"
    CORPORATE_GOVERNANCE = "corporate_governance"
    ZONING_REPORT = "zoning_report"
    PHASE_I_ESA = "phase_i_esa"
    TITLE_POLICY = "title_policy"
    PROPERTY_SURVEY = "property_survey"
    CAPEX_BUDGET = "capex_budget"
    PROPERTY_MANAGER_RESUME = "property_manager_resume"
    LOAN_APPLICATION_1003 = "loan_application_1003"
    PRE_APPROVAL = "pre_approval"
    PRE_APPROVAL_LETTER = "pre_approval_letter"
    UNIFORM_RESIDENTIAL_LOAN_APPLICATION = "uniform_residential_loan_application"
    FEMA_FLOOD_CERT = "fema_flood_cert"
    FLOOD_ZONE_DETERMINATION = "flood_zone_determination"
    TITLE_COMMITMENT = "title_commitment"
    TITLE_PRELIMINARY_REPORT = "title_preliminary_report"
    VOE = "voe"
    VERIFICATION_OF_EMPLOYMENT = "verification_of_employment"
    VOD = "vod"
    VERIFICATION_OF_DEPOSIT = "verification_of_deposit"
    HAZARD_INSURANCE = "hazard_insurance"
    HAZARD_INSURANCE_DECLARATION = "hazard_insurance_declaration"
    PROPERTY_TAX_BILL = "property_tax_bill"
    PROPERTY_TAX_RECEIPT = "property_tax_receipt"
    UW_APPROVAL_MEMO = "uw_approval_memo"
    UNDERWRITING_APPROVAL_MEMO = "underwriting_approval_memo"
    CLOSING_DISCLOSURE = "closing_disclosure"
    TRID_CLOSING_DISCLOSURE = "trid_closing_disclosure"
    LOAN_ESTIMATE = "loan_estimate"
    PAYOFF_STATEMENT = "payoff_statement"
    MORTGAGE_STATEMENT = "mortgage_statement"
    RENTAL_HISTORY = "rental_history"
    RENTAL_HISTORY_LETTER = "rental_history_letter"
    UNKNOWN = "unknown"


class MortgageBundleStatus(str, Enum):
    RECEIVED = "received"
    CLASSIFIED = "classified"
    PARSED = "parsed"
    RECONCILED = "reconciled"
    ANALYZED = "analyzed"
    COMPLETED = "completed"
    FAILED = "failed"


class MortgageDecision(str, Enum):
    APPROVE = "approve"
    SUSPEND = "suspend"
    REFER = "refer"
    DENY = "deny"


class ExtractedMortgageField(BaseModel):
    field_name: str
    value: str
    confidence: float = 0.85
    context: str = ""


class MortgageDocument(BaseModel):
    document_id: str
    source_path: str = ""
    document_type: MortgageDocumentType
    product_line: ProductLine = ProductLine.RESIDENTIAL_MORTGAGE
    raw_text: str = ""
    extracted_fields: dict[str, list[ExtractedMortgageField]] = Field(default_factory=dict)
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def get_field(self, name: str, default: str = "") -> str:
        entries = self.extracted_fields.get(name, [])
        return entries[0].value if entries else default

    def get_float(self, name: str, default: float = 0.0) -> float:
        raw = self.get_field(name, "")
        if not raw:
            return default
        cleaned = raw.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return default


class BorrowerProfile(BaseModel):
    full_name: str = ""
    ssn_last4: str = ""
    spouse_name: str = ""
    address: str = ""
    employer: str = ""
    occupation: str = ""


class IncomeSummary(BaseModel):
    annual_wages: float = 0.0
    self_employment_income: float = 0.0
    total_income: float = 0.0
    adjusted_gross_income: float = 0.0
    sources: list[str] = Field(default_factory=list)


class CreditSummary(BaseModel):
    bureau: str = ""
    credit_score: int = 0
    total_balance: float = 0.0
    total_monthly_payment: float = 0.0
    utilization_rate: float = 0.0
    open_accounts: int = 0
    derogatory_flags: list[str] = Field(default_factory=list)


class AssetSummary(BaseModel):
    total_liquid_assets: float = 0.0
    accounts: list[dict[str, Any]] = Field(default_factory=list)
    gift_funds: float = 0.0


class CollateralSummary(BaseModel):
    property_address: str = ""
    appraised_value: float = 0.0
    purchase_price: float = 0.0
    ltv: float = 0.0


class ReconciliationIssue(BaseModel):
    field_path: str
    source_a: str
    source_b: str
    value_a: str
    value_b: str
    severity: str = "warning"
    rule_id: str = ""


class ComplianceViolation(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    message: str
    document_refs: list[str] = Field(default_factory=list)


class MortgageFinding(BaseModel):
    title: str
    description: str
    severity: str = "moderate"
    category: str = ""
    document_refs: list[str] = Field(default_factory=list)


class MortgageAgentResult(BaseModel):
    agent_name: str
    success: bool = True
    findings: list[MortgageFinding] = Field(default_factory=list)
    risk_score: float = 0.5
    summary: str = ""


class MortgageMemo(BaseModel):
    bundle_id: str
    product_line: ProductLine
    borrower_name: str = ""
    decision: MortgageDecision = MortgageDecision.REFER
    risk_score: float = 0.5
    dti_ratio: Optional[float] = None
    ltv_ratio: Optional[float] = None
    summary: str = ""
    key_findings: list[MortgageFinding] = Field(default_factory=list)
    reconciliation_issues: list[ReconciliationIssue] = Field(default_factory=list)
    compliance_violations: list[ComplianceViolation] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class MortgageBundle(BaseModel):
    bundle_id: str
    product_line: ProductLine = ProductLine.RESIDENTIAL_MORTGAGE
    status: MortgageBundleStatus = MortgageBundleStatus.RECEIVED
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    documents: list[MortgageDocument] = Field(default_factory=list)
    borrowers: list[BorrowerProfile] = Field(default_factory=list)
    income: Optional[IncomeSummary] = None
    credit: Optional[CreditSummary] = None
    assets: Optional[AssetSummary] = None
    collateral: Optional[CollateralSummary] = None
    reconciliation_issues: list[ReconciliationIssue] = Field(default_factory=list)
    compliance_violations: list[ComplianceViolation] = Field(default_factory=list)

    def documents_by_type(self, doc_type: MortgageDocumentType) -> list[MortgageDocument]:
        return [d for d in self.documents if d.document_type == doc_type]
