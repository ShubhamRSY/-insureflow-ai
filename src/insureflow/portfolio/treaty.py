from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TreatyType(str, Enum):
    QUOTA_SHARE = "quota_share"
    SURPLUS_SHARE = "surplus_share"
    PER_RISK_EXCESS = "per_risk_excess"
    CATASTROPHE_EXCESS = "catastrophe_excess"
    FACULTATIVE = "facultative"
    STOP_LOSS = "stop_loss"


class ReinsuranceTreaty(BaseModel):
    treaty_id: str
    treaty_name: str
    treaty_type: TreatyType
    is_active: bool = True

    # Cession parameters
    cession_pct: float = 0.0
    cession_limit: float = 0.0
    cession_attachment: float = 0.0
    aggregate_limit: float = 0.0
    aggregate_used: float = 0.0

    # Eligibility filters
    eligible_states: list[str] = Field(default_factory=list)
    eligible_naics_prefixes: list[str] = Field(default_factory=list)
    excluded_occupancies: list[str] = Field(default_factory=list)
    max_single_risk_tiv: float = 0.0
    max_annual_premium: float = 0.0

    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def aggregate_remaining(self) -> float:
        return max(0.0, self.aggregate_limit - self.aggregate_used)

    @property
    def utilization_pct(self) -> float:
        if self.aggregate_limit <= 0:
            return 0.0
        return (self.aggregate_used / self.aggregate_limit) * 100


class TreatyAllocation(BaseModel):
    """Result of applying a treaty to a specific risk."""
    treaty_id: str
    treaty_name: str
    treaty_type: TreatyType
    ceded_pct: float
    ceded_amount: float
    is_applicable: bool = True
    exclusion_reason: str = ""


class TreatyAttachmentResult(BaseModel):
    """Whether a risk attaches to the treaty and at what level."""
    treaty_id: str
    treaty_name: str
    treaty_type: TreatyType
    attaches: bool = False
    attachment_point: float = 0.0
    cession_limit: float = 0.0
    ceded_amount: float = 0.0
    retained_amount: float = 0.0
    reason: str = ""


class TreatyStore:
    """In-memory store of reinsurance treaties with utilization tracking."""

    def __init__(self) -> None:
        self._treaties: dict[str, ReinsuranceTreaty] = {}
        self._load_demo_treaties()

    def _load_demo_treaties(self) -> None:
        treaties = [
            ReinsuranceTreaty(
                treaty_id="treaty-qs-001",
                treaty_name="Quota Share — 50% Cession",
                treaty_type=TreatyType.QUOTA_SHARE,
                cession_pct=0.50,
                cession_limit=10_000_000,
                cession_attachment=0,
                aggregate_limit=100_000_000,
                aggregate_used=42_000_000,
                eligible_states=["FL", "TX", "LA", "CA", "NY", "IL"],
                eligible_naics_prefixes=["44", "45", "53", "54", "56", "62", "72", "81"],
                max_single_risk_tiv=20_000_000,
                max_annual_premium=100_000,
            ),
            ReinsuranceTreaty(
                treaty_id="treaty-xs-001",
                treaty_name="Per-Risk Excess — $1M xs $2M",
                treaty_type=TreatyType.PER_RISK_EXCESS,
                cession_pct=1.0,
                cession_limit=1_000_000,
                cession_attachment=2_000_000,
                aggregate_limit=25_000_000,
                aggregate_used=8_500_000,
                eligible_states=["FL", "TX", "LA", "CA", "NY", "IL", "GA"],
                max_single_risk_tiv=25_000_000,
            ),
            ReinsuranceTreaty(
                treaty_id="treaty-cat-001",
                treaty_name="Catastrophe Excess — $5M xs $10M",
                treaty_type=TreatyType.CATASTROPHE_EXCESS,
                cession_pct=1.0,
                cession_limit=5_000_000,
                cession_attachment=10_000_000,
                aggregate_limit=50_000_000,
                aggregate_used=12_000_000,
                eligible_states=["FL", "TX", "LA", "CA"],
                max_single_risk_tiv=30_000_000,
                excluded_occupancies=["offshore_drilling", "nuclear"],
            ),
        ]
        for t in treaties:
            self._treaties[t.treaty_id] = t

    def get_treaty(self, treaty_id: str) -> Optional[ReinsuranceTreaty]:
        return self._treaties.get(treaty_id)

    def list_treaties(self, active_only: bool = True) -> list[ReinsuranceTreaty]:
        if active_only:
            return [t for t in self._treaties.values() if t.is_active]
        return list(self._treaties.values())

    def apply_treaties(
        self,
        tiv: float,
        premium: float,
        state: str,
        naics_code: str,
        occupancy_type: str = "",
    ) -> list[TreatyAllocation]:
        allocations: list[TreatyAllocation] = []
        for treaty in self.list_treaties(active_only=True):
            result = self._evaluate_treaty(treaty, tiv, premium, state, naics_code, occupancy_type)
            allocations.append(result)
        return allocations

    def check_attachment(
        self,
        treaty: ReinsuranceTreaty,
        tiv: float,
    ) -> TreatyAttachmentResult:
        result = TreatyAttachmentResult(
            treaty_id=treaty.treaty_id,
            treaty_name=treaty.treaty_name,
            treaty_type=treaty.treaty_type,
        )
        if treaty.treaty_type == TreatyType.QUOTA_SHARE:
            result.attaches = tiv > 0
            result.cession_limit = treaty.cession_limit
            result.ceded_amount = min(tiv * treaty.cession_pct, treaty.cession_limit)
            result.retained_amount = tiv - result.ceded_amount
        elif treaty.treaty_type in (TreatyType.PER_RISK_EXCESS, TreatyType.CATASTROPHE_EXCESS):
            if tiv > treaty.cession_attachment:
                result.attaches = True
                result.attachment_point = treaty.cession_attachment
                result.cession_limit = treaty.cession_limit
                excess = tiv - treaty.cession_attachment
                result.ceded_amount = min(excess, treaty.cession_limit)
                result.retained_amount = tiv - result.ceded_amount
        elif treaty.treaty_type == TreatyType.SURPLUS_SHARE:
            result.attaches = tiv > 0
            result.cession_limit = treaty.cession_limit
            result.ceded_amount = min(tiv * treaty.cession_pct, treaty.cession_limit)
            result.retained_amount = tiv - result.ceded_amount
        elif treaty.treaty_type == TreatyType.FACULTATIVE:
            result.attaches = tiv > treaty.cession_attachment
            result.attachment_point = treaty.cession_attachment
            result.cession_limit = treaty.cession_limit
            excess = max(0.0, tiv - treaty.cession_attachment)
            result.ceded_amount = min(excess, treaty.cession_limit)
            result.retained_amount = tiv - result.ceded_amount
        return result

    def consume_aggregate(self, treaty_id: str, amount: float) -> bool:
        treaty = self._treaties.get(treaty_id)
        if not treaty or not treaty.is_active:
            return False
        if treaty.aggregate_used + amount > treaty.aggregate_limit:
            return False
        treaty.aggregate_used += amount
        return True

    def _evaluate_treaty(
        self,
        treaty: ReinsuranceTreaty,
        tiv: float,
        premium: float,
        state: str,
        naics_code: str,
        occupancy_type: str,
    ) -> TreatyAllocation:
        # Eligibility checks
        if treaty.eligible_states and state not in treaty.eligible_states:
            return TreatyAllocation(
                treaty_id=treaty.treaty_id,
                treaty_name=treaty.treaty_name,
                treaty_type=treaty.treaty_type,
                ceded_pct=0.0,
                ceded_amount=0.0,
                is_applicable=False,
                exclusion_reason=f"State '{state}' not in eligible list",
            )
        if treaty.eligible_naics_prefixes and naics_code[:2] not in treaty.eligible_naics_prefixes:
            return TreatyAllocation(
                treaty_id=treaty.treaty_id,
                treaty_name=treaty.treaty_name,
                treaty_type=treaty.treaty_type,
                ceded_pct=0.0,
                ceded_amount=0.0,
                is_applicable=False,
                exclusion_reason=f"NAICS '{naics_code}' not eligible",
            )
        if occupancy_type in treaty.excluded_occupancies:
            return TreatyAllocation(
                treaty_id=treaty.treaty_id,
                treaty_name=treaty.treaty_name,
                treaty_type=treaty.treaty_type,
                ceded_pct=0.0,
                ceded_amount=0.0,
                is_applicable=False,
                exclusion_reason=f"Occupancy '{occupancy_type}' excluded",
            )
        if treaty.max_single_risk_tiv > 0 and tiv > treaty.max_single_risk_tiv:
            return TreatyAllocation(
                treaty_id=treaty.treaty_id,
                treaty_name=treaty.treaty_name,
                treaty_type=treaty.treaty_type,
                ceded_pct=0.0,
                ceded_amount=0.0,
                is_applicable=False,
                exclusion_reason=f"TIV ${tiv:,.0f} exceeds treaty max of ${treaty.max_single_risk_tiv:,.0f}",
            )
        if treaty.max_annual_premium > 0 and premium > treaty.max_annual_premium:
            return TreatyAllocation(
                treaty_id=treaty.treaty_id,
                treaty_name=treaty.treaty_name,
                treaty_type=treaty.treaty_type,
                ceded_pct=0.0,
                ceded_amount=0.0,
                is_applicable=False,
                exclusion_reason=f"Premium ${premium:,.0f} exceeds treaty max of ${treaty.max_annual_premium:,.0f}",
            )
        if treaty.aggregate_remaining <= 0:
            return TreatyAllocation(
                treaty_id=treaty.treaty_id,
                treaty_name=treaty.treaty_name,
                treaty_type=treaty.treaty_type,
                ceded_pct=0.0,
                ceded_amount=0.0,
                is_applicable=False,
                exclusion_reason="Aggregate limit exhausted",
            )

        # Apply treaty
        attachment = self.check_attachment(treaty, tiv)
        return TreatyAllocation(
            treaty_id=treaty.treaty_id,
            treaty_name=treaty.treaty_name,
            treaty_type=treaty.treaty_type,
            ceded_pct=attachment.ceded_amount / tiv if tiv > 0 else 0.0,
            ceded_amount=attachment.ceded_amount,
            is_applicable=True,
        )


# Singleton
_treaty_store: TreatyStore | None = None


def get_treaty_store() -> TreatyStore:
    global _treaty_store
    if _treaty_store is None:
        _treaty_store = TreatyStore()
    return _treaty_store
