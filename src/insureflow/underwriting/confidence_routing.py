"""Confidence-based routing — match decision complexity to UW authority tier.

Routes low-confidence or high-complexity submissions to senior underwriters and
CUOs, while allowing high-confidence STP decisions to flow to junior tiers or
fully automated processing.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RoutingTier(str, Enum):
    STP = "stp"
    JUNIOR = "junior"
    SENIOR = "senior"
    CUO = "cuo"
    ESCALATE = "escalate"


class RoutingDecision(BaseModel):
    tier: RoutingTier = RoutingTier.SENIOR
    confidence_score: float = 0.0
    complexity_score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    requires_co_sign: bool = False
    routed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class ComplexityIndicator(str, Enum):
    HIGH_PREMIUM = "high_premium"
    HIGH_TIV = "high_tiv"
    UNUSUAL_OCCUPANCY = "unusual_occupancy"
    MULTI_STATE = "multi_state"
    LOSS_RUN_FLAGS = "loss_run_flags"
    EXCLUDED_CLASS = "excluded_class"
    LOW_FIELD_COVERAGE = "low_field_coverage"
    CONFLICTING_DATA = "conflicting_data"


_PREMIUM_STP_MAX = float(os.getenv("CONFIDENCE_ROUTING_STP_PREMIUM_MAX", "0"))
_PREMIUM_SENIOR_MIN = float(os.getenv("CONFIDENCE_ROUTING_SENIOR_PREMIUM_MIN", "0"))
_TIV_CUO_MIN = float(os.getenv("CONFIDENCE_ROUTING_CUO_TIV_MIN", "0"))


def _resolve_thresholds() -> tuple[float, float, float]:
    stp_max = _PREMIUM_STP_MAX if _PREMIUM_STP_MAX > 0 else 25_000.0
    senior_min = _PREMIUM_SENIOR_MIN if _PREMIUM_SENIOR_MIN > 0 else 150_000.0
    cuo_min = _TIV_CUO_MIN if _TIV_CUO_MIN > 0 else 10_000_000.0
    return stp_max, senior_min, cuo_min


def _compute_complexity(
    fields: dict[str, Any],
    field_confidences: list[float] | None = None,
) -> tuple[float, list[ComplexityIndicator], list[str]]:
    indicators: list[ComplexityIndicator] = []
    reasons: list[str] = []
    score = 0.0

    premium = 0.0
    for k, v in fields.items():
        if "premium" in k.lower() and v is not None:
            try:
                premium = float(str(v).replace(",", "").replace("$", ""))
            except (ValueError, TypeError):
                pass

    tiv = 0.0
    for k, v in fields.items():
        if "total_insured" in k.lower() or k.lower() == "tiv":
            try:
                tiv = float(str(v).replace(",", "").replace("$", ""))
            except (ValueError, TypeError):
                pass

    stp_max, senior_min, cuo_min = _resolve_thresholds()
    if premium > stp_max:
        score += 0.2
        if premium > senior_min:
            indicators.append(ComplexityIndicator.HIGH_PREMIUM)
            reasons.append(f"Premium ${premium:,.0f} exceeds senior threshold ${senior_min:,.0f}")
            score += 0.3
        if tiv > cuo_min:
            indicators.append(ComplexityIndicator.HIGH_TIV)
            reasons.append(f"TIV ${tiv:,.0f} exceeds CUO threshold ${cuo_min:,.0f}")
            score += 0.3

    if field_confidences:
        avg_conf = sum(field_confidences) / len(field_confidences) if field_confidences else 1.0
        low_conf_count = sum(1 for c in field_confidences if c < 0.5)
        if avg_conf < 0.6:
            score += 0.3
            reasons.append(f"Average field confidence {avg_conf:.2f} is low")
        if low_conf_count > len(field_confidences) * 0.3:
            score += 0.2
            reasons.append(f"{low_conf_count}/{len(field_confidences)} fields below 50% confidence")

    field_count = len(fields)
    if field_count < 5:
        indicators.append(ComplexityIndicator.LOW_FIELD_COVERAGE)
        reasons.append(f"Only {field_count} fields extracted — limited evidence")
        score += 0.2

    return min(1.0, score), indicators, reasons


def route_decision(
    fields: dict[str, Any],
    verification_report: Any = None,
    *,
    field_confidences: list[float] | None = None,
    premium_override: float | None = None,
) -> RoutingDecision:
    complexity_score, indicators, reasons = _compute_complexity(fields, field_confidences)

    confidences = field_confidences or []
    confidence_score = sum(confidences) / len(confidences) if confidences else 0.5

    requires_co_sign = False
    tier: RoutingTier

    if confidence_score >= 0.95 and complexity_score < 0.2:
        tier = RoutingTier.STP
        reasons.append("High confidence + low complexity — eligible for straight-through processing")
    elif complexity_score >= 0.8 or confidence_score < 0.3:
        tier = RoutingTier.CUO
        requires_co_sign = True
        reasons.append("Very high complexity or very low confidence — routed to CUO with co-sign required")
    elif complexity_score >= 0.5 or confidence_score < 0.5:
        tier = RoutingTier.SENIOR
        reasons.append("Moderate complexity — routed to senior underwriter")
    elif complexity_score >= 0.2:
        tier = RoutingTier.JUNIOR
        reasons.append("Low-moderate complexity — routed to junior underwriter")
    else:
        tier = RoutingTier.STP
        reasons.append("Low complexity — eligible for straight-through processing")

    if any(i in indicators for i in (ComplexityIndicator.HIGH_PREMIUM, ComplexityIndicator.HIGH_TIV)):
        if tier in (RoutingTier.STP, RoutingTier.JUNIOR):
            tier = RoutingTier.SENIOR
            reasons.append("Premium/TIV thresholds require senior review")

    decision = RoutingDecision(
        tier=tier,
        confidence_score=confidence_score,
        complexity_score=complexity_score,
        reasons=reasons,
        requires_co_sign=requires_co_sign,
    )
    logger.info(
        "confidence_routing tier=%s confidence=%.2f complexity=%.2f co_sign=%s",
        tier.value,
        confidence_score,
        complexity_score,
        requires_co_sign,
    )
    return decision
