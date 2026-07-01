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
    def submit_quote(self, request: QuoteRequest, memo: UnderwritingMemo, bundle: SubmissionBundle) -> QuoteResult:
        ...

    @abstractmethod
    def bind_policy(self, bundle_id: str, quote_reference: str, bound_by: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def sync_status(self, reference: str) -> dict[str, Any]:
        ...
