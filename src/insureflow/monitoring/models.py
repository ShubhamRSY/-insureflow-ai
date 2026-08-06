"""Ongoing policy monitoring models (Step 6 of the underwriting process).

After an underwriting decision has been made on a new business submission
or a renewal, the underwriter must monitor activity on the individual
policies to ensure that satisfactory results are achieved. These models
carry UW memo monitoring items forward, track loss development, and
surface monitoring alerts between bind and renewal.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MonitoringSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class MonitoringSource(str, Enum):
    UW_MEMO = "uw_memo"
    LOSS_DEVELOPMENT = "loss_development"
    EXPIRY = "expiry"
    RENEWAL = "renewal"
    MANUAL = "manual"


class MonitoringItemStatus(str, Enum):
    OPEN = "open"
    MONITORING = "monitoring"
    CLEARED = "cleared"
    WAIVED = "waived"


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    MONITORED = "monitored"
    WATCH = "watch"
    CLOSED = "closed"


class MonitoringItem(BaseModel):
    item_id: str
    policy_id: str
    bundle_id: str = ""
    org_id: str = "default"
    title: str
    description: str = ""
    severity: MonitoringSeverity = MonitoringSeverity.MODERATE
    source: MonitoringSource = MonitoringSource.MANUAL
    status: MonitoringItemStatus = MonitoringItemStatus.OPEN
    due_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    resolved_at: str = ""
    resolved_by: str = ""
    notes: list[str] = Field(default_factory=list)


class MonitoringAlert(BaseModel):
    alert_id: str
    policy_id: str
    bundle_id: str = ""
    org_id: str = "default"
    severity: MonitoringSeverity = MonitoringSeverity.MODERATE
    title: str
    message: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    resolved: bool = False
    resolved_at: str = ""


class LossDevelopmentEntry(BaseModel):
    entry_id: str
    policy_id: str
    org_id: str = "default"
    policy_year: int = 0
    earned_premium: float = 0.0
    incurred_losses: float = 0.0
    paid_losses: float = 0.0
    claim_count: int = 0
    loss_ratio: float = 0.0
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    recorded_by: str = "system"


class PolicyMonitoringRecord(BaseModel):
    """One in-force policy under ongoing monitoring."""

    policy_id: str
    bundle_id: str
    org_id: str = "default"
    policy_number: str = ""
    insured_name: str = ""
    line_of_business: str = ""
    premium: float = 0.0
    tiv: float = 0.0
    effective_date: str = ""
    expiry_date: str = ""
    status: PolicyStatus = PolicyStatus.ACTIVE
    items: list[MonitoringItem] = Field(default_factory=list)
    alerts: list[MonitoringAlert] = Field(default_factory=list)
    loss_development: list[LossDevelopmentEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    last_reviewed_at: str = ""
    last_reviewed_by: str = ""

    @property
    def open_item_count(self) -> int:
        return len([i for i in self.items if i.status in (MonitoringItemStatus.OPEN, MonitoringItemStatus.MONITORING)])

    @property
    def open_alert_count(self) -> int:
        return len([a for a in self.alerts if not a.resolved])

    @property
    def latest_loss_ratio(self) -> float:
        if not self.loss_development:
            return 0.0
        return self.loss_development[-1].loss_ratio

    @property
    def days_to_expiry(self) -> int:
        if not self.expiry_date:
            return 0
        try:
            exp = datetime.fromisoformat(self.expiry_date).date()
            return (exp - date.today()).days
        except (ValueError, TypeError):
            return 0

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "bundle_id": self.bundle_id,
            "policy_number": self.policy_number,
            "insured_name": self.insured_name,
            "line_of_business": self.line_of_business,
            "premium": self.premium,
            "tiv": self.tiv,
            "effective_date": self.effective_date,
            "expiry_date": self.expiry_date,
            "days_to_expiry": self.days_to_expiry,
            "status": self.status.value,
            "open_item_count": self.open_item_count,
            "open_alert_count": self.open_alert_count,
            "latest_loss_ratio": self.latest_loss_ratio,
            "last_reviewed_at": self.last_reviewed_at,
        }
