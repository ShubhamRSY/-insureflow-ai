"""Policy issuance handoff — binder, policy worksheet, and certificate generation.

Manages the transition from approved UW decision to policy issuance,
including binder creation, policy data validation, and carrier handoff.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from insureflow.models.agents import Finding, RiskSeverity, UWDecision


class IssuanceStatus(str, Enum):
    NOT_READY = "not_ready"
    PENDING_UW_APPROVAL = "pending_uw_approval"
    BINDER_ISSUED = "binder_issued"
    POLICY_REQUESTED = "policy_requested"
    POLICY_ISSUED = "policy_issued"
    POLICY_DELIVERED = "policy_delivered"
    FAILED = "failed"


class PolicyType(str, Enum):
    TERM_LIFE = "term_life"
    WHOLE_LIFE = "whole_life"
    UNIVERSAL_LIFE = "universal_life"
    VARIABLE_UL = "variable_ul"
    ENDOWMENT = "endowment"
    ANNUITY = "annuity"


@dataclass
class PolicyIssuanceData:
    policy_number: str = ""
    policy_type: PolicyType = PolicyType.TERM_LIFE
    face_amount: float = 0.0
    annual_premium: float = 0.0
    monthly_premium: float = 0.0
    premium_mode: str = "annual"
    underwriting_class: str = "standard"
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    insured_name: str = ""
    beneficiary_name: str = ""
    beneficiary_relationship: str = ""
    owner_name: str = ""
    owner_relationship: str = ""
    agent_of_record: str = ""
    carrier: str = ""
    state: str = ""
    product_id: str = ""
    product_name: str = ""
    riders: list[str] = field(default_factory=list)
    rider_premiums: dict[str, float] = field(default_factory=dict)
    conditions: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_number": self.policy_number,
            "policy_type": self.policy_type.value,
            "face_amount": self.face_amount,
            "annual_premium": self.annual_premium,
            "monthly_premium": self.monthly_premium,
            "premium_mode": self.premium_mode,
            "underwriting_class": self.underwriting_class,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "insured_name": self.insured_name,
            "beneficiary_name": self.beneficiary_name,
            "beneficiary_relationship": self.beneficiary_relationship,
            "owner_name": self.owner_name,
            "owner_relationship": self.owner_relationship,
            "agent_of_record": self.agent_of_record,
            "carrier": self.carrier,
            "state": self.state,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "riders": list(self.riders),
            "rider_premiums": dict(self.rider_premiums),
            "conditions": list(self.conditions),
            "notes": self.notes,
        }


@dataclass
class BinderRecord:
    binder_id: str = Field(default_factory=lambda: f"binder-{uuid.uuid4().hex[:12]}")
    bundle_id: str = ""
    policy_data: PolicyIssuanceData = Field(default_factory=PolicyIssuanceData)
    issued_at: datetime = Field(default_factory=datetime.now)
    issued_by: str = ""
    expires_at: Optional[datetime] = None
    status: IssuanceStatus = IssuanceStatus.BINDER_ISSUED

    def to_dict(self) -> dict[str, Any]:
        return {
            "binder_id": self.binder_id,
            "bundle_id": self.bundle_id,
            "policy_data": self.policy_data.to_dict(),
            "issued_at": self.issued_at.isoformat(),
            "issued_by": self.issued_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
        }


@dataclass
class PolicyIssuanceResult:
    binder: Optional[BinderRecord] = None
    status: IssuanceStatus = IssuanceStatus.NOT_READY
    findings: list[Finding] = field(default_factory=list)
    ready_checklist: dict[str, bool] = field(default_factory=dict)
    blocking_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "binder": self.binder.to_dict() if self.binder else None,
            "status": self.status.value,
            "ready_checklist": self.ready_checklist,
            "blocking_items": self.blocking_items,
            "findings_count": len(self.findings),
        }


def check_issuance_readiness(
    *,
    decision: UWDecision,
    has_aps: bool,
    aps_reviewed: bool,
    has_mib: bool,
    has_hipaa: bool,
    has_beneficiary: bool,
    has_financial_uw: bool,
    reinsured: bool,
    reinsured_placed: bool,
    premium_calculated: bool,
    reinsurance_fac_required: bool,
    reinsurance_placed: bool,
    human_review_cleared: bool,
    all_conditions_met: bool,
) -> PolicyIssuanceResult:
    checklist: dict[str, bool] = {
        "uw_decision_approved": decision in (UWDecision.ACCEPT, UWDecision.CONDITIONAL_ACCEPT),
        "aps_on_file": has_aps,
        "aps_reviewed": aps_reviewed,
        "mib_cleared": has_mib,
        "hipaa_on_file": has_hipaa,
        "beneficiary_designated": has_beneficiary,
        "financial_uw_complete": has_financial_uw,
        "reinsurance_ceded": not reinsured or reinsured_placed,
        "premium_calculated": premium_calculated,
        "facultative_placed": not reinsurance_fac_required or reinsurance_placed,
        "human_review_cleared": human_review_cleared,
        "all_conditions_met": all_conditions_met,
    }

    blocking: list[str] = []
    findings: list[Finding] = []

    for item, met in checklist.items():
        if not met:
            label = item.replace("_", " ").title()
            blocking.append(label)
            findings.append(
                Finding(
                    title=f"Issuance blocked: {label}",
                    description=f"{label} must be completed before policy can be issued.",
                    severity=RiskSeverity.HIGH,
                    category="policy_issuance",
                )
            )

    status = IssuanceStatus.NOT_READY
    if decision in (UWDecision.ACCEPT, UWDecision.CONDITIONAL_ACCEPT):
        if not blocking:
            status = IssuanceStatus.PENDING_UW_APPROVAL
        else:
            status = IssuanceStatus.NOT_READY

    return PolicyIssuanceResult(
        status=status,
        findings=findings,
        ready_checklist=checklist,
        blocking_items=blocking,
    )


def create_binder(
    bundle_id: str,
    policy_data: PolicyIssuanceData,
    *,
    issued_by: str = "",
) -> BinderRecord:
    binder = BinderRecord(
        bundle_id=bundle_id,
        policy_data=policy_data,
        issued_by=issued_by,
    )
    return binder


_ISSUANCE_STORE: dict[str, BinderRecord] = {}


def persist_binder(binder: BinderRecord) -> None:
    _ISSUANCE_STORE[binder.bundle_id] = binder


def get_binder(bundle_id: str) -> Optional[BinderRecord]:
    return _ISSUANCE_STORE.get(bundle_id)


def list_binders() -> list[BinderRecord]:
    return sorted(_ISSUANCE_STORE.values(), key=lambda b: b.issued_at, reverse=True)
