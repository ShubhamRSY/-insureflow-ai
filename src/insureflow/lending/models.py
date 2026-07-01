from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class LoanProductType(str, Enum):
    BUSINESS_TERM_LOAN = "business_term_loan"
    BUSINESS_LINE_OF_CREDIT = "business_line_of_credit"
    COMMERCIAL_REAL_ESTATE = "commercial_real_estate"
    CONSTRUCTION_LOAN = "construction_loan"
    SBA_7A = "sba_7a"
    SBA_504 = "sba_504"
    EQUIPMENT_FINANCING = "equipment_financing"
    INVOICE_FINANCING = "invoice_financing"
    PERSONAL_TERM_LOAN = "personal_term_loan"
    PERSONAL_LINE_OF_CREDIT = "personal_line_of_credit"
    AUTO_LOAN = "auto_loan"
    BOAT_LOAN = "boat_loan"
    HOME_EQUITY_LOAN = "home_equity_loan"
    HOME_EQUITY_LINE = "home_equity_line"
    SECURED_PERSONAL = "secured_personal"
    UNSECURED_PERSONAL = "unsecured_personal"


class LoanPurpose(str, Enum):
    WORKING_CAPITAL = "working_capital"
    DEBT_REFINANCE = "debt_refinance"
    EQUIPMENT_PURCHASE = "equipment_purchase"
    REAL_ESTATE_PURCHASE = "real_estate_purchase"
    CONSTRUCTION = "construction"
    BUSINESS_EXPANSION = "business_expansion"
    INVENTORY_FINANCING = "inventory_financing"
    ACQUISITION = "acquisition"
    SEASONAL_FINANCING = "seasonal_financing"
    AUTO_PURCHASE = "auto_purchase"
    BOAT_PURCHASE = "boat_purchase"
    HOME_IMPROVEMENT = "home_improvement"
    DEBT_CONSOLIDATION = "debt_consolidation"
    EDUCATION = "education"
    MEDICAL = "medical"
    OTHER = "other"


class LendingDocumentType(str, Enum):
    LOAN_APPLICATION = "loan_application"
    BUSINESS_PLAN = "business_plan"
    FINANCIAL_STATEMENT = "financial_statement"
    PROFIT_LOSS = "profit_loss"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    TAX_RETURN = "tax_return"
    BANK_STATEMENT = "bank_statement"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    ACCOUNTS_PAYABLE = "accounts_payable"
    DEBT_SCHEDULE = "debt_schedule"
    COLLATERAL_APPRAISAL = "collateral_appraisal"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    ARTICLES_OF_INCORPORATION = "articles_of_incorporation"
    OPERATING_AGREEMENT = "operating_agreement"
    BUSINESS_LICENSE = "business_license"
    FRANCHISE_AGREEMENT = "franchise_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    PURCHASE_AGREEMENT = "purchase_agreement"
    CONTRACT_OF_SALE = "contract_of_sale"
    TITLE_REPORT = "title_report"
    APPRAISAL = "appraisal"
    ENVIRONMENTAL_REPORT = "environmental_report"
    PERSONAL_FINANCIAL_STATEMENT = "personal_financial_statement"
    PAY_STUB = "pay_stub"
    W2 = "w2"
    CREDIT_REPORT = "credit_report"
    DRIVERS_LICENSE = "drivers_license"
    PASSPORT = "passport"
    VOIDED_CHECK = "voided_check"
    BUSINESS_CARD_STATEMENT = "business_card_statement"
    BUSINESS_DEBT_CARD_STATEMENT = "business_debt_card_statement"
    TREASURY_MGMT_AUTHORIZATION = "treasury_mgmt_authorization"
    ACH_AUTHORIZATION = "ach_authorization"
    WIRE_AUTHORIZATION = "wire_authorization"
    LOCKBOX_AGREEMENT = "lockbox_agreement"
    MERCHANT_APPLICATION = "merchant_application"
    TRUST_AGREEMENT = "trust_agreement"
    ESTATE_PLANNING_DOC = "estate_planning_doc"
    INVESTMENT_POLICY = "investment_policy"


class BusinessFinancialData(BaseModel):
    annual_revenue: float = 0.0
    net_income: float = 0.0
    cost_of_goods_sold: float = 0.0
    gross_profit: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    current_assets: float = 0.0
    current_liabilities: float = 0.0
    accounts_receivable: float = 0.0
    accounts_payable: float = 0.0
    inventory: float = 0.0
    cash_and_equivalents: float = 0.0
    shareholder_equity: float = 0.0
    retained_earnings: float = 0.0
    ebitda: float = 0.0
    debt_service: float = 0.0
    year: int = 0


class ConsumerFinancialData(BaseModel):
    annual_income: float = 0.0
    monthly_housing_expense: float = 0.0
    total_monthly_debt: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    cash_and_equivalents: float = 0.0
    credit_score: int = 0
    employment_years: float = 0.0
    bankruptcies_last_7_years: int = 0
    foreclosures_last_7_years: int = 0


class Collateral(BaseModel):
    collateral_type: str = ""
    description: str = ""
    estimated_value: float = 0.0
    appraised_value: Optional[float] = None
    lien_position: str = "first"
    condition: str = ""
    location: str = ""


class Guarantor(BaseModel):
    name: str = ""
    personal_guarantee: bool = False
    net_worth: float = 0.0
    credit_score: int = 0
    liquidity: float = 0.0


class BusinessLoanApplication(BaseModel):
    application_id: str = Field(default_factory=lambda: f"biz-{uuid4().hex[:10]}")
    business_name: str = ""
    legal_structure: str = ""
    industry: str = ""
    naics_code: str = ""
    years_in_business: float = 0.0
    number_of_employees: int = 0
    product_type: LoanProductType = LoanProductType.BUSINESS_TERM_LOAN
    loan_purpose: LoanPurpose = LoanPurpose.WORKING_CAPITAL
    requested_amount: float = 0.0
    requested_term_months: int = 0
    existing_relationship: bool = False
    financials: list[BusinessFinancialData] = Field(default_factory=list)
    collateral: list[Collateral] = Field(default_factory=list)
    guarantors: list[Guarantor] = Field(default_factory=list)


class ConsumerLoanApplication(BaseModel):
    application_id: str = Field(default_factory=lambda: f"con-{uuid4().hex[:10]}")
    first_name: str = ""
    last_name: str = ""
    ssn_last_four: str = ""
    date_of_birth: Optional[date] = None
    employment_status: str = ""
    employer_name: str = ""
    years_at_job: float = 0.0
    product_type: LoanProductType = LoanProductType.PERSONAL_TERM_LOAN
    loan_purpose: LoanPurpose = LoanPurpose.DEBT_CONSOLIDATION
    requested_amount: float = 0.0
    requested_term_months: int = 0
    existing_relationship: bool = False
    financial_data: ConsumerFinancialData = Field(default_factory=ConsumerFinancialData)


class CreditAnalysis(BaseModel):
    analysis_id: str = Field(default_factory=lambda: f"ca-{uuid4().hex[:10]}")
    credit_score_tier: str = ""
    dscr: float = 0.0
    debt_to_income_ratio: float = 0.0
    loan_to_value: float = 0.0
    coverage_ratio: float = 0.0
    liquidity_ratio: float = 0.0
    leverage_ratio: float = 0.0
    profitability_score: float = 0.0
    management_score: float = 0.0
    industry_risk_score: float = 0.0
    overall_risk_score: float = 0.0
    risk_rating: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    mitigants: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)


class LoanDecision(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    DECLINED = "declined"
    SUSPENDED = "suspended"
    REFERRED = "referred"


class LendingPipelineResult(BaseModel):
    application_id: str
    product_type: LoanProductType
    decision: LoanDecision
    risk_score: float = 0.0
    risk_rating: str = ""
    requested_amount: float = 0.0
    approved_amount: Optional[float] = None
    approved_rate: Optional[float] = None
    approved_term_months: Optional[int] = None
    conditions: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    human_review_reasons: list[str] = Field(default_factory=list)
    compliance_violations: list[dict[str, Any]] = Field(default_factory=list)
    credit_analysis: Optional[CreditAnalysis] = None
    document_count: int = 0
    lender_notes: str = ""
