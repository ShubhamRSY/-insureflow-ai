from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RateFilingMethod(str, Enum):
    PRIOR_APPROVAL = "prior_approval"
    FILE_AND_USE = "file_and_use"
    USE_AND_FILE = "use_and_file"
    FLEX_RATING = "flex_rating"
    NO_FILE = "no_file"


class TortModel(str, Enum):
    PURE_COMPARATIVE = "pure_comparative"
    MODIFIED_COMPARATIVE_50 = "modified_comparative_50"
    MODIFIED_COMPARATIVE_51 = "modified_comparative_51"
    CONTRIBUTORY = "contributory"


class SurplusLinesRequirement(str, Enum):
    DILIGENT_SEARCH = "diligent_search"
    STAMPING_OFFICE = "stamping_office"
    EXPORT_FEE = "export_fee"
    TAX_FILING = "tax_filing"
    BROKER_OF_RECORD = "broker_of_record"


class ComplianceSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class StateRule(BaseModel):
    state_code: str
    state_name: str

    rate_filing: RateFilingMethod = RateFilingMethod.NO_FILE
    rate_filing_notes: str = ""

    surplus_lines: list[SurplusLinesRequirement] = Field(default_factory=list)
    surplus_lines_notes: str = ""

    binder_requires_written: bool = False
    binder_notes: str = ""

    claims_prompt_pay_days: Optional[int] = None
    claims_notes: str = ""

    commission_cap_pct: Optional[float] = None
    commission_cap_notes: str = ""

    tort_model: TortModel = TortModel.PURE_COMPARATIVE
    tort_notes: str = ""

    windstorm_hurricane_deductible: bool = False
    windstorm_notes: str = ""

    hurricane_license_required: bool = False

    workers_comp_state_fund: bool = False
    workers_comp_notes: str = ""

    surplus_lines_tax_rate: float = 0.0
    surplus_lines_stamping_fee: float = 0.0

    admitted_only: bool = False
    admitted_notes: str = ""

    mandatory_coverages: list[str] = Field(default_factory=list)
    mandatory_coverages_notes: str = ""

    regulatory_notes: str = ""


class ComplianceFlag(BaseModel):
    state_code: str
    rule_category: str
    severity: ComplianceSeverity
    message: str
    action_required: str = ""


class StateComplianceResult(BaseModel):
    state_code: str
    state_name: str
    flags: list[ComplianceFlag] = Field(default_factory=list)
    rule: Optional[StateRule] = None
    summary: str = ""
