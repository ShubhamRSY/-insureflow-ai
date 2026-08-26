"""MIB ordering workflow — request, track, and process MIB bureau reports.

Extends the existing MIB report module to support ordering reports from the
bureau (not just reading uploaded documents) and tracking order status.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.mib import MibReport


class MibOrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MibOrderPriority(str, Enum):
    ROUTINE = "routine"
    EXPEDITED = "expedited"
    URGENT = "urgent"


@dataclass
class MibOrderRequest:
    order_id: str = Field(default_factory=lambda: f"mib-{uuid.uuid4().hex[:12]}")
    applicant_name: str = ""
    applicant_dob: Optional[date] = None
    applicant_ssn_last4: str = ""
    applicant_gender: str = ""
    applicant_state: str = ""
    priority: MibOrderPriority = MibOrderPriority.ROUTINE
    requesting_agent: str = "system"
    request_reason: str = "routine_underwriting"
    bundle_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: MibOrderStatus = MibOrderStatus.PENDING
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "applicant_name": self.applicant_name,
            "applicant_dob": self.applicant_dob.isoformat() if self.applicant_dob else None,
            "applicant_ssn_last4": self.applicant_ssn_last4,
            "applicant_gender": self.applicant_gender,
            "applicant_state": self.applicant_state,
            "priority": self.priority.value,
            "requesting_agent": self.requesting_agent,
            "request_reason": self.request_reason,
            "bundle_id": self.bundle_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "error_message": self.error_message,
        }


@dataclass
class MibOrderResult:
    order: MibOrderRequest
    report: Optional[MibReport] = None
    findings: list[Finding] = field(default_factory=list)
    discrepancy_count: int = 0
    codes_found: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order.to_dict(),
            "report": self.report.model_dump() if self.report else None,
            "discrepancy_count": self.discrepancy_count,
            "codes_found": self.codes_found,
            "findings_count": len(self.findings),
        }


def create_mib_order(
    bundle: SubmissionBundle,
    *,
    priority: MibOrderPriority = MibOrderPriority.ROUTINE,
    requesting_agent: str = "system",
) -> MibOrderRequest:
    structured = bundle.structured
    named = structured.named_insured if structured else None
    return MibOrderRequest(
        applicant_name=(named.legal_name if named else "") or "",
        applicant_dob=named.dob if named and hasattr(named, "dob") else None,
        applicant_gender=(named.gender if named and hasattr(named, "gender") else "") or "",
        applicant_state=(named.state if named and hasattr(named, "state") else "") or "",
        priority=priority,
        requesting_agent=requesting_agent,
        bundle_id=bundle.bundle_id or "",
    )


def process_mib_order(order: MibOrderRequest, report: MibReport) -> MibOrderResult:
    order.status = MibOrderStatus.COMPLETED
    order.updated_at = datetime.now()

    findings: list[Finding] = []
    if report.no_hit:
        findings.append(
            Finding(
                title="MIB no-hit",
                description="No MIB records found for this applicant — does not confirm clean bill of health.",
                severity=RiskSeverity.LOW,
                category="mib_order",
            )
        )
    if report.discrepancies:
        for disc in report.discrepancies:
            findings.append(
                Finding(
                    title=f"MIB discrepancy: {disc.description}",
                    description=disc.reason,
                    severity=disc.severity,
                    category="mib_order",
                )
            )

    return MibOrderResult(
        order=order,
        report=report,
        findings=findings,
        discrepancy_count=len(report.discrepancies),
        codes_found=len(report.codes),
    )


def build_mib_order_from_bundle(
    bundle: SubmissionBundle,
    *,
    priority: MibOrderPriority = MibOrderPriority.ROUTINE,
    requesting_agent: str = "system",
) -> MibOrderResult:
    order = create_mib_order(bundle, priority=priority, requesting_agent=requesting_agent)
    from insureflow.underwriting.mib import request_mib_report

    report = request_mib_report(bundle)
    return process_mib_order(order, report)


_MIB_ORDER_STORE: dict[str, MibOrderRequest] = {}


def persist_mib_order(order: MibOrderRequest) -> None:
    _MIB_ORDER_STORE[order.order_id] = order


def get_mib_order(order_id: str) -> Optional[MibOrderRequest]:
    return _MIB_ORDER_STORE.get(order_id)


def list_mib_orders(bundle_id: str = "") -> list[MibOrderRequest]:
    orders = list(_MIB_ORDER_STORE.values())
    if bundle_id:
        orders = [o for o in orders if o.bundle_id == bundle_id]
    return sorted(orders, key=lambda o: o.created_at, reverse=True)
