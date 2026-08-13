"""AML models — OFAC-style hits and FinCEN SAR drafts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SanctionsHit(BaseModel):
    list_name: str
    matched_name: str
    query: str
    score: float = Field(ge=0, le=1)
    aliases: list[str] = Field(default_factory=list)
    program: str = ""
    entity_type: str = "individual"


class SanctionsResult(BaseModel):
    query: str
    cleared: bool = True
    hits: list[SanctionsHit] = Field(default_factory=list)
    recommended_action: str = "clear"
    screened_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class SarFiling(BaseModel):
    sar_id: str
    org_id: str = "default"
    filer_org: str = ""
    subject_name: str
    subject_tin: str = ""
    subject_type: str = "individual"  # individual | business
    activity_type: str = "fraud"  # structuring | fraud | money_laundering | terrorist_financing | cyber | other
    amount: float = 0.0
    narrative: str = ""
    suspicious_period_start: str = ""
    suspicious_period_end: str = ""
    status: str = "draft"  # draft | filed | acknowledged
    related_bundle_id: str = ""
    filed_by: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
