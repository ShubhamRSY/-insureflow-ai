from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkflowState(str, Enum):
    RECEIVED = "received"
    ANALYZING = "analyzing"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    DECLINED = "declined"
    BOUND = "bound"
    EXPIRED = "expired"


class SignOffAction(str, Enum):
    APPROVE = "approve"
    DECLINE = "decline"
    REFER = "refer"
    REQUEST_INFO = "request_info"


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


class WorkflowRecord(BaseModel):
    bundle_id: str
    org_id: str = "default"
    state: WorkflowState = WorkflowState.RECEIVED
    ai_decision: str = ""
    final_decision: str = ""
    assigned_to: str = ""
    sign_offs: list[SignOffRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
