from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class OverrideReasonCategory(str, Enum):
    PRICING = "pricing"
    COVERAGE = "coverage"
    TERMS = "terms"
    APPETITE = "appetite"
    COMPLIANCE = "compliance"
    DATA_QUALITY = "data_quality"
    MARKET_CONDITIONS = "market_conditions"
    CLIENT_RELATIONSHIP = "client_relationship"
    BROKER_RELATIONSHIP = "broker_relationship"
    ERRONEOUS_AI = "erroneous_ai"
    OTHER = "other"


class PremiumDelta(BaseModel):
    ai_premium: float
    uw_premium: float
    delta: float
    delta_pct: float
    reason: str = ""


class CoverageDelta(BaseModel):
    coverage_type: str
    field: str
    ai_value: Any = None
    uw_value: Any = None
    delta_description: str = ""


class OverrideDetail(BaseModel):
    """Structured record of a single UW override of the AI recommendation."""

    override_id: str
    sign_off_id: str
    bundle_id: str
    org_id: str = "default"

    ai_decision: str
    uw_decision: str
    decision_changed: bool = False

    premium_delta: Optional[PremiumDelta] = None
    coverage_changes: list[CoverageDelta] = Field(default_factory=list)

    reason_category: OverrideReasonCategory = OverrideReasonCategory.OTHER
    reason_freeform: str = ""

    uw_confidence: str = ""
    post_bind_verdict: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class OverridePattern(BaseModel):
    """An aggregated pattern detected across multiple UW overrides."""

    pattern_id: str
    description: str
    reason_categories: list[OverrideReasonCategory] = Field(default_factory=list)
    trigger_count: int = 0
    avg_premium_delta_pct: float = 0.0
    common_decision_shift: str = ""
    suggested_rule_update: str = ""
    rule_priority: int = 0
    first_seen: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    active: bool = True


class OverrideAnalyticsQuery(BaseModel):
    org_id: str = "default"
    limit: int = 100
    offset: int = 0
    reason_category: Optional[OverrideReasonCategory] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    decision_changed_only: bool = False


class OverrideAnalyticsSummary(BaseModel):
    total_overrides: int = 0
    total_decision_changes: int = 0
    decision_change_rate: float = 0.0
    avg_premium_delta_pct: float = 0.0
    by_category: dict[str, int] = Field(default_factory=dict)
    top_patterns: list[OverridePattern] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
