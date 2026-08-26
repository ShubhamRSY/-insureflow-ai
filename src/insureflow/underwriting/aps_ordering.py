"""APS (Attending Physician Statement) ordering workflow.

Models the request, tracking, and fulfillment of APS orders — the
medical records retrieval process that is central to life underwriting.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle


class ApsOrderStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    SUBMITTED_TO_VENDOR = "submitted_to_vendor"
    VENDOR_PROCESSING = "vendor_processing"
    RECEIVED = "received"
    REVIEWED = "reviewed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApsOrderPriority(str, Enum):
    ROUTINE = "routine"
    EXPEDITED = "expedited"
    RUSH = "rush"


@dataclass
class ApsPhysicianInfo:
    name: str = ""
    specialty: str = ""
    practice_name: str = ""
    address: str = ""
    phone: str = ""
    fax: str = ""
    npi: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "specialty": self.specialty,
            "practice_name": self.practice_name,
            "address": self.address,
            "phone": self.phone,
            "fax": self.fax,
            "npi": self.npi,
        }


@dataclass
class ApsOrderRequest:
    order_id: str = Field(default_factory=lambda: f"aps-{uuid.uuid4().hex[:12]}")
    applicant_name: str = ""
    applicant_dob: Optional[date] = None
    physician: ApsPhysicianInfo = Field(default_factory=ApsPhysicianInfo)
    reason_for_aps: str = "routine_underwriting"
    priority: ApsOrderPriority = ApsOrderPriority.ROUTINE
    hipaa_authorization_on_file: bool = False
    requesting_agent: str = "system"
    bundle_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: ApsOrderStatus = ApsOrderStatus.NOT_REQUESTED
    vendor_reference: str = ""
    estimated_completion: Optional[date] = None
    error_message: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "applicant_name": self.applicant_name,
            "applicant_dob": self.applicant_dob.isoformat() if self.applicant_dob else None,
            "physician": self.physician.to_dict(),
            "reason_for_aps": self.reason_for_aps,
            "priority": self.priority.value,
            "hipaa_authorization_on_file": self.hipaa_authorization_on_file,
            "requesting_agent": self.requesting_agent,
            "bundle_id": self.bundle_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "vendor_reference": self.vendor_reference,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "error_message": self.error_message,
            "notes": self.notes,
        }


@dataclass
class ApsOrderResult:
    order: ApsOrderRequest
    findings: list[Finding] = field(default_factory=list)
    records_received: int = 0
    pages_received: int = 0
    conditions_disclosed: list[str] = field(default_factory=list)
    medications_disclosed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order.to_dict(),
            "records_received": self.records_received,
            "pages_received": self.pages_received,
            "conditions_disclosed": self.conditions_disclosed,
            "medications_disclosed": self.medications_disclosed,
            "findings_count": len(self.findings),
        }


def create_aps_order(
    bundle: SubmissionBundle,
    *,
    physician: Optional[ApsPhysicianInfo] = None,
    priority: ApsOrderPriority = ApsOrderPriority.ROUTINE,
    requesting_agent: str = "system",
) -> ApsOrderRequest:
    structured = bundle.structured
    named = structured.named_insured if structured else None
    hipaa = False
    blob_lower = " ".join(
        doc.raw_text for doc in (bundle.unstructured or []) if doc.raw_text
    ).lower() if bundle.unstructured else ""
    if "hipaa" in blob_lower or "authorization" in blob_lower:
        hipaa = True

    return ApsOrderRequest(
        applicant_name=(named.legal_name if named else "") or "",
        physician=physician or ApsPhysicianInfo(),
        hipaa_authorization_on_file=hipaa,
        priority=priority,
        requesting_agent=requesting_agent,
        bundle_id=bundle.bundle_id or "",
    )


def process_aps_order(order: ApsOrderRequest) -> ApsOrderResult:
    order.status = ApsOrderStatus.RECEIVED
    order.updated_at = datetime.now()

    findings: list[Finding] = []

    if not order.hipaa_authorization_on_file:
        findings.append(
            Finding(
                title="HIPAA authorization missing",
                description="APS cannot be ordered without a signed HIPAA authorization on file.",
                severity=RiskSeverity.CRITICAL,
                category="aps_order",
            )
        )

    if not order.physician.name:
        findings.append(
            Finding(
                title="Physician not identified",
                description="Attending physician name required before APS can be ordered.",
                severity=RiskSeverity.HIGH,
                category="aps_order",
            )
        )

    if order.priority == ApsOrderPriority.RUSH:
        findings.append(
            Finding(
                title="Rush APS ordered",
                description="Expedited APS retrieval — expect higher vendor cost.",
                severity=RiskSeverity.LOW,
                category="aps_order",
            )
        )

    return ApsOrderResult(
        order=order,
        findings=findings,
    )


_APS_ORDER_STORE: dict[str, ApsOrderRequest] = {}


def persist_aps_order(order: ApsOrderRequest) -> None:
    _APS_ORDER_STORE[order.order_id] = order


def get_aps_order(order_id: str) -> Optional[ApsOrderRequest]:
    return _APS_ORDER_STORE.get(order_id)


def list_aps_orders(bundle_id: str = "") -> list[ApsOrderRequest]:
    orders = list(_APS_ORDER_STORE.values())
    if bundle_id:
        orders = [o for o in orders if o.bundle_id == bundle_id]
    return sorted(orders, key=lambda o: o.created_at, reverse=True)
