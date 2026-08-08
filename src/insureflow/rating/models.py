from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle


class InsuranceLine(str, Enum):
    COMMERCIAL_PROPERTY = "commercial_property"
    GENERAL_LIABILITY = "general_liability"
    WORKERS_COMP = "workers_comp"
    BOP = "business_owners_policy"
    UMBRELLA = "umbrella"
    # Commercial specialty (non-COPE / non-TIV property math)
    DIRECTORS_AND_OFFICERS = "directors_and_officers"
    TRADE_CREDIT = "trade_credit"
    ERRORS_AND_OMISSIONS = "errors_and_omissions"
    KEY_PERSON = "key_person"
    # Personal lines
    PERSONAL_HOMEOWNERS = "personal_homeowners"
    PERSONAL_AUTO = "personal_auto"
    LIFE = "life"


PERSONAL_LINES = frozenset(
    {
        InsuranceLine.PERSONAL_HOMEOWNERS,
        InsuranceLine.PERSONAL_AUTO,
        InsuranceLine.LIFE,
    }
)

# Limit / receivable / face-amount rated — not building TIV + COPE
COMMERCIAL_SPECIALTY_LINES = frozenset(
    {
        InsuranceLine.DIRECTORS_AND_OFFICERS,
        InsuranceLine.TRADE_CREDIT,
        InsuranceLine.ERRORS_AND_OMISSIONS,
        InsuranceLine.KEY_PERSON,
    }
)

# Human-friendly line labels for reports / quotes / UI.
LINE_DISPLAY_NAMES: dict[str, str] = {
    "commercial_property": "Property & Business Interruption",
    "general_liability": "General Liability",
    "business_owners_policy": "Business Owners Policy (BOP)",
    "umbrella": "Commercial Umbrella",
    "workers_comp": "Workers' Compensation",
    "directors_and_officers": "Directors & Officers (D&O)",
    "trade_credit": "Trade Credit Insurance",
    "errors_and_omissions": "Errors & Omissions (E&O)",
    "key_person": "Key Person Insurance",
    "personal_homeowners": "Personal Homeowners",
    "personal_auto": "Personal Auto",
    "life": "Life Insurance",
}


def line_display_name(value: str) -> str:
    """Friendly display label for a line-of-business key (falls back to title case)."""
    return LINE_DISPLAY_NAMES.get(str(value or "").lower(), str(value or "").replace("_", " ").title())


@dataclass(frozen=True)
class RateComponent:
    name: str
    amount: float
    basis: str = ""
    modifier_pct: float = 0.0


@dataclass
class QuoteRequest:
    bundle_id: str
    line: InsuranceLine = InsuranceLine.COMMERCIAL_PROPERTY
    tiv: float = 0.0
    state: str = ""
    naics_code: str = ""
    loss_ratio: float = 0.0
    schedule_mod_pct: float = 0.0


@dataclass
class QuoteResult:
    bundle_id: str
    line: InsuranceLine
    base_premium: float
    adjusted_premium: float
    schedule_modifications: list[RateComponent] = field(default_factory=list)
    rate_per_100_tiv: float = 0.0
    quote_valid_until: str = ""
    eligible: bool = True
    ineligibility_reasons: list[str] = field(default_factory=list)
    policy_admin_reference: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class RatingAdapter(ABC):
    """Adapter interface for policy admin / rating systems (Guidewire, Duck Creek, etc.)."""

    @abstractmethod
    def submit_quote(self, request: QuoteRequest, memo: UnderwritingMemo, bundle: SubmissionBundle) -> QuoteResult: ...

    @abstractmethod
    def bind_policy(self, bundle_id: str, quote_reference: str, bound_by: str) -> dict[str, Any]: ...

    @abstractmethod
    def sync_status(self, reference: str) -> dict[str, Any]: ...
