"""Decision abstention — explicit 'I don't know' path.

When the evidence quality is too low or the verification report indicates
widespread uncertainty, the system abstains from making a recommendation and
escalates to a human underwriter rather than hallucinating a decision.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_MIN_FIELDS_FOR_DECISION = 3
_MIN_OVERALL_CONFIDENCE = 0.3
_MAX_ERROR_RATIO = 0.5


class AbstentionReason(str, Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    LOW_CONFIDENCE = "low_confidence"
    HIGH_ERROR_RATIO = "high_error_ratio"
    CONFLICTING_SOURCES = "conflicting_sources"
    MISSING_CRITICAL_FIELDS = "missing_critical_fields"
    VERIFICATION_FAILED = "verification_failed"


class AbstentionVerdict(BaseModel):
    abstain: bool = False
    reasons: list[AbstentionReason] = Field(default_factory=list)
    evidence_score: float = 0.0
    field_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    missing_critical: list[str] = Field(default_factory=list)
    message: str = ""
    decided_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


_CRITICAL_FIELD_PATTERNS = (
    "total",
    "premium",
    "limit",
    "deductible",
    "named_insured",
    "policy_period",
    "effective_date",
    "expiration_date",
    "coverage",
)

_OPTIONAL_ABSTENTION_THRESHOLD = float(os.getenv("ABSTENTION_CONFIDENCE_THRESHOLD", "0"))


def _confidence_score(field_confidences: list[float]) -> float:
    if not field_confidences:
        return 0.0
    return sum(field_confidences) / len(field_confidences)


def _critical_fields_present(field_keys: list[str]) -> list[str]:
    missing: list[str] = []
    for pattern in _CRITICAL_FIELD_PATTERNS:
        if not any(pattern in k.lower() for k in field_keys):
            missing.append(pattern)
    return missing


def evaluate_abstention(
    fields: dict[str, Any],
    verification_report: Any = None,
    *,
    field_confidences: list[float] | None = None,
) -> AbstentionVerdict:
    reasons: list[AbstentionReason] = []
    all_field_keys = list(fields.keys()) if isinstance(fields, dict) else []
    field_count = len(all_field_keys)

    if field_count < _MIN_FIELDS_FOR_DECISION:
        reasons.append(AbstentionReason.INSUFFICIENT_DATA)

    confidences = field_confidences or []
    if hasattr(verification_report, "issues"):
        issues = verification_report.issues
        error_count = sum(1 for i in issues if getattr(i, "severity", "") == "error")
        warning_count = sum(1 for i in issues if getattr(i, "severity", "") == "warning")
    else:
        error_count = 0
        warning_count = 0

    total_flagged = error_count + warning_count
    if field_count > 0 and total_flagged / field_count > _MAX_ERROR_RATIO:
        reasons.append(AbstentionReason.HIGH_ERROR_RATIO)

    avg_confidence = _confidence_score(confidences) if confidences else 1.0
    if confidences and avg_confidence < _MIN_OVERALL_CONFIDENCE:
        reasons.append(AbstentionReason.LOW_CONFIDENCE)

    if hasattr(verification_report, "passed") and not verification_report.passed:
        reasons.append(AbstentionReason.VERIFICATION_FAILED)

    missing_critical = _critical_fields_present(all_field_keys)
    if len(missing_critical) >= 3:
        reasons.append(AbstentionReason.MISSING_CRITICAL_FIELDS)

    if not reasons:
        return AbstentionVerdict(
            abstain=False,
            field_count=field_count,
            error_count=error_count,
            warning_count=warning_count,
            evidence_score=avg_confidence,
        )

    messages = {
        AbstentionReason.INSUFFICIENT_DATA: f"Only {field_count} fields extracted (minimum {_MIN_FIELDS_FOR_DECISION} required)",
        AbstentionReason.LOW_CONFIDENCE: f"Average field confidence {avg_confidence:.2f} below {_MIN_OVERALL_CONFIDENCE}",
        AbstentionReason.HIGH_ERROR_RATIO: f"{error_count} errors + {warning_count} warnings across {field_count} fields exceeds {_MAX_ERROR_RATIO:.0%} threshold",
        AbstentionReason.MISSING_CRITICAL_FIELDS: f"Missing critical fields: {', '.join(missing_critical[:3])}",
        AbstentionReason.VERIFICATION_FAILED: "Verification report indicates failed checks",
        AbstentionReason.CONFLICTING_SOURCES: "Multiple extraction sources disagree",
    }
    primary = reasons[0]
    detail = messages.get(primary, "Evidence quality insufficient for automated decision")

    logger.info("abstention triggered bundle reasons=%s detail=%s", [r.value for r in reasons], detail)

    return AbstentionVerdict(
        abstain=True,
        reasons=reasons,
        evidence_score=avg_confidence,
        field_count=field_count,
        error_count=error_count,
        warning_count=warning_count,
        missing_critical=missing_critical,
        message=detail,
    )
