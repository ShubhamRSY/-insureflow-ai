from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class OutcomeStatus(str, Enum):
    QUOTED = "quoted"
    BOUND = "bound"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class BindOutcome(BaseModel):
    outcome_id: str
    bundle_id: str
    org_id: str = "default"
    status: OutcomeStatus = OutcomeStatus.QUOTED
    policy_number: str = ""
    quoted_premium: float = 0.0
    bound_premium: float = 0.0
    ai_decision: str = ""
    uw_decision: str = ""
    bound_at: Optional[datetime] = None
    bound_by: str = ""
    policy_admin_reference: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class LossExperience(BaseModel):
    experience_id: str
    policy_number: str
    bundle_id: str = ""
    org_id: str = "default"
    policy_year: int = 0
    earned_premium: float = 0.0
    incurred_losses: float = 0.0
    paid_losses: float = 0.0
    claim_count: int = 0
    loss_ratio: float = 0.0
    reported_at: date = Field(default_factory=date.today)


class PredictionRecord(BaseModel):
    prediction_id: str
    bundle_id: str
    predicted_decision: str
    predicted_premium: float
    predicted_loss_ratio: float = 0.0
    actual_decision: str = ""
    actual_premium: float = 0.0
    actual_loss_ratio: float = 0.0
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
