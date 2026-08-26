"""Renewal and convertibility tracking for life insurance policies.

Tracks policy renewal dates, conversion windows, premium guarantees,
and lapse risk to ensure timely action on expiring/renewing coverage.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from insureflow.models.agents import Finding, RiskSeverity


class RenewalStatus(str, Enum):
    ACTIVE = "active"
    RENEWAL_DUE = "renewal_due"
    RENEWAL_OVERDUE = "renewal_overdue"
    CONVERTIBLE = "convertible"
    CONVERSION_WINDOW_OPEN = "conversion_window_open"
    CONVERSION_WINDOW_CLOSED = "conversion_window_closed"
    LAPSED = "lapsed"
    SURRENDERED = "surrendered"
    CLAIMED = "claimed"


class RenewalType(str, Enum):
    ANNUAL_RENEWAL = "annual_renewal"
    GUARANTEED_PERIOD = "guaranteed_period"
    CONVERTIBLE_TERM = "convertible_term"
    NON_RENEWABLE = "non_renewable"


@dataclass
class PolicyRenewalRecord:
    record_id: str = Field(default_factory=lambda: f"renew-{uuid.uuid4().hex[:12]}")
    bundle_id: str = ""
    policy_number: str = ""
    insured_name: str = ""
    product_type: str = ""
    face_amount: float = 0.0
    current_annual_premium: float = 0.0
    renewal_type: RenewalType = RenewalType.ANNUAL_RENEWAL
    status: RenewalStatus = RenewalStatus.ACTIVE

    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    renewal_date: Optional[date] = None
    premium_guarantee_end: Optional[date] = None
    conversion_window_end: Optional[date] = None

    renewal_premium_quoted: Optional[float] = None
    renewal_premium_change_pct: Optional[float] = None
    conversion_eligible: bool = False
    conversion_face_amount: float = 0.0
    conversion_product_options: list[str] = field(default_factory=list)

    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "bundle_id": self.bundle_id,
            "policy_number": self.policy_number,
            "insured_name": self.insured_name,
            "product_type": self.product_type,
            "face_amount": self.face_amount,
            "current_annual_premium": self.current_annual_premium,
            "renewal_type": self.renewal_type.value,
            "status": self.status.value,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "renewal_date": self.renewal_date.isoformat() if self.renewal_date else None,
            "premium_guarantee_end": self.premium_guarantee_end.isoformat() if self.premium_guarantee_end else None,
            "conversion_window_end": self.conversion_window_end.isoformat() if self.conversion_window_end else None,
            "renewal_premium_quoted": self.renewal_premium_quoted,
            "renewal_premium_change_pct": self.renewal_premium_change_pct,
            "conversion_eligible": self.conversion_eligible,
            "conversion_face_amount": self.conversion_face_amount,
            "conversion_product_options": list(self.conversion_product_options),
            "notes": self.notes,
        }


@dataclass
class RenewalCheckResult:
    record: PolicyRenewalRecord
    findings: list[Finding] = field(default_factory=list)
    days_until_renewal: Optional[int] = None
    days_until_conversion_close: Optional[int] = None
    premium_change_flag: bool = False
    action_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "days_until_renewal": self.days_until_renewal,
            "days_until_conversion_close": self.days_until_conversion_close,
            "premium_change_flag": self.premium_change_flag,
            "action_items": self.action_items,
            "findings_count": len(self.findings),
        }


def check_renewal(record: PolicyRenewalRecord) -> RenewalCheckResult:
    today = date.today()
    findings: list[Finding] = []
    action_items: list[str] = []
    days_renewal: Optional[int] = None
    days_conversion: Optional[int] = None
    premium_flag = False

    if record.renewal_date:
        delta = (record.renewal_date - today).days
        days_renewal = delta
        if delta < 0:
            record.status = RenewalStatus.RENEWAL_OVERDUE
            findings.append(
                Finding(
                    title="Renewal overdue",
                    description=f"Renewal was due {record.renewal_date.isoformat()} ({abs(delta)} days ago).",
                    severity=RiskSeverity.CRITICAL,
                    category="renewal",
                )
            )
            action_items.append("Contact insured immediately to renew policy")
        elif delta <= 30:
            record.status = RenewalStatus.RENEWAL_DUE
            findings.append(
                Finding(
                    title="Renewal approaching",
                    description=f"Renewal due in {delta} days ({record.renewal_date.isoformat()}).",
                    severity=RiskSeverity.HIGH,
                    category="renewal",
                )
            )
            action_items.append("Send renewal notice and confirm premium")
        elif delta <= 90:
            findings.append(
                Finding(
                    title="Renewal within 90 days",
                    description=f"Renewal due {record.renewal_date.isoformat()} ({delta} days).",
                    severity=RiskSeverity.MODERATE,
                    category="renewal",
                )
            )
            action_items.append("Begin renewal review process")

    if record.conversion_window_end:
        delta_c = (record.conversion_window_end - today).days
        days_conversion = delta_c
        if delta_c < 0:
            record.conversion_eligible = False
            record.status = RenewalStatus.CONVERSION_WINDOW_CLOSED
            findings.append(
                Finding(
                    title="Conversion window closed",
                    description=f"Conversion right expired {record.conversion_window_end.isoformat()}.",
                    severity=RiskSeverity.MODERATE,
                    category="renewal",
                )
            )
        elif delta_c <= 30:
            record.status = RenewalStatus.CONVERSION_WINDOW_OPEN
            findings.append(
                Finding(
                    title="Conversion window closing soon",
                    description=f"Convert to permanent coverage within {delta_c} days.",
                    severity=RiskSeverity.HIGH,
                    category="renewal",
                )
            )
            action_items.append("Notify insured of conversion deadline")
        elif delta_c <= 90:
            record.conversion_eligible = True
            findings.append(
                Finding(
                    title="Conversion window open",
                    description=f"Convertible for {delta_c} more days — discuss with insured.",
                    severity=RiskSeverity.LOW,
                    category="renewal",
                )
            )
            action_items.append("Discuss conversion options with insured")

    if record.renewal_premium_change_pct is not None and abs(record.renewal_premium_change_pct) > 15:
        premium_flag = True
        pct = record.renewal_premium_change_pct
        findings.append(
            Finding(
                title=f"Premium increase {pct:+.1f}%",
                description=f"Renewal premium {pct:+.1f}% vs current — review insured's ability to continue.",
                severity=RiskSeverity.HIGH if pct > 0 else RiskSeverity.LOW,
                category="renewal",
            )
        )
        action_items.append("Discuss premium change and options with insured")

    if record.premium_guarantee_end and record.premium_guarantee_end <= today:
        findings.append(
            Finding(
                title="Premium guarantee expired",
                description=f"Guaranteed period ended {record.premium_guarantee_end.isoformat()} — renewal premium may increase.",
                severity=RiskSeverity.MODERATE,
                category="renewal",
            )
        )

    return RenewalCheckResult(
        record=record,
        findings=findings,
        days_until_renewal=days_renewal,
        days_until_conversion_close=days_conversion,
        premium_change_flag=premium_flag,
        action_items=action_items,
    )


_RENEWAL_STORE: dict[str, PolicyRenewalRecord] = {}


def persist_renewal(record: PolicyRenewalRecord) -> None:
    _RENEWAL_STORE[record.record_id] = record


def get_renewal(record_id: str) -> Optional[PolicyRenewalRecord]:
    return _RENEWAL_STORE.get(record_id)


def list_renewals(bundle_id: str = "") -> list[PolicyRenewalRecord]:
    records = list(_RENEWAL_STORE.values())
    if bundle_id:
        records = [r for r in records if r.bundle_id == bundle_id]
    return sorted(records, key=lambda r: r.renewal_date or date.max)
