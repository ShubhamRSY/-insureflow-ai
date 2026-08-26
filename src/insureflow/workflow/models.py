from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    RECEIVED = "received"
    ANALYZING = "analyzing"
    PENDING_REVIEW = "pending_review"
    PENDING_CO_SIGN = "pending_co_sign"
    APPROVED = "approved"
    QUOTED = "quoted"
    DECLINED = "declined"
    NO_QUOTE = "no_quote"
    BOUND = "bound"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class SignOffAction(str, Enum):
    APPROVE = "approve"
    QUOTE = "quote"
    NO_QUOTE = "no_quote"
    DECLINE = "decline"
    REFER = "refer"
    REQUEST_INFO = "request_info"


class ReviewPriority(str, Enum):
    """SLA-driven priority tiers for human review queue."""
    CRITICAL = "critical"    # 4-hour SLA — critical findings, fraud flags
    URGENT = "urgent"        # 8-hour SLA — high-severity, large premium
    NORMAL = "normal"        # 24-hour SLA — standard refer/conditional
    LOW = "low"              # 72-hour SLA — low-risk conditional accepts


# SLA windows in hours per priority tier
SLA_HOURS: dict[ReviewPriority, float] = {
    ReviewPriority.CRITICAL: 4.0,
    ReviewPriority.URGENT: 8.0,
    ReviewPriority.NORMAL: 24.0,
    ReviewPriority.LOW: 72.0,
}


BINDABLE_STATES = frozenset({WorkflowState.APPROVED, WorkflowState.QUOTED})


def allows_bind(state: WorkflowState | str) -> bool:
    value = state if isinstance(state, WorkflowState) else WorkflowState(str(state))
    return value in BINDABLE_STATES


class SignOffRecord(BaseModel):
    sign_off_id: str
    bundle_id: str
    org_id: str = "default"
    action: SignOffAction
    signed_by: str
    license_number: str = ""
    notes: str = ""
    signed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    ai_decision: str = ""
    override_reason: str = ""


class EscalationRecord(BaseModel):
    escalation_id: str = ""
    bundle_id: str = ""
    org_id: str = "default"
    escalated_from: str = ""  # previous assignee
    escalated_to: str = ""    # new assignee (supervisor / senior UW)
    reason: str = ""
    escalated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    sla_breach_hours: float = 0.0


class WorkflowRecord(BaseModel):
    bundle_id: str
    org_id: str = "default"
    state: WorkflowState = WorkflowState.RECEIVED
    ai_decision: str = ""
    final_decision: str = ""
    assigned_to: str = ""
    assigned_at: Optional[datetime] = None
    priority: ReviewPriority = ReviewPriority.NORMAL
    sla_deadline: Optional[datetime] = None
    escalations: list[EscalationRecord] = Field(default_factory=list)
    sign_offs: list[SignOffRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compute_sla_deadline(self) -> None:
        """Set the SLA deadline based on priority tier."""
        hours = SLA_HOURS.get(self.priority, 24.0)
        ref_time = self.assigned_at or self.created_at
        self.sla_deadline = ref_time + timedelta(hours=hours)

    def is_overdue(self) -> bool:
        """Check if the case has breached its SLA."""
        if self.sla_deadline is None:
            return False
        return datetime.now(tz=timezone.utc) > self.sla_deadline

    def hours_overdue(self) -> float:
        """Return hours past SLA, or 0 if not overdue."""
        if not self.is_overdue():
            return 0.0
        delta = datetime.now(tz=timezone.utc) - self.sla_deadline  # type: ignore[operator]
        return delta.total_seconds() / 3600.0
