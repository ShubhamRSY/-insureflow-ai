"""Active learning loop — close the override-to-model feedback cycle.

Captures human corrections from overrides, identifies recurring patterns,
and produces structured training signals that can be fed back into extraction
models and appetite filters.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_MIN_SAMPLES_FOR_PATTERN = 3


class CorrectionSignal(BaseModel):
    signal_id: str
    bundle_id: str
    field_name: str
    ai_value: str = ""
    human_value: str = ""
    correction_type: str = "value_override"
    confidence_at_override: float = 0.0
    override_reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class LearningPattern(BaseModel):
    pattern_id: str
    field_name: str
    description: str = ""
    sample_count: int = 0
    common_correction: str = ""
    avg_confidence_when_overridden: float = 0.0
    suggested_action: str = ""
    first_seen: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class CalibrationAdjustment(BaseModel):
    field_name: str
    current_confidence_offset: float = 0.0
    recommended_adjustment: float = 0.0
    sample_size: int = 0
    reasoning: str = ""


class ActiveLearningEngine:
    def __init__(self, org_id: str = "default") -> None:
        self.org_id = org_id
        self._signals: list[CorrectionSignal] = []
        self._patterns: list[LearningPattern] = []

    def record_correction(
        self,
        bundle_id: str,
        field_name: str,
        ai_value: str,
        human_value: str,
        confidence: float = 0.0,
        override_reason: str = "",
        correction_type: str = "value_override",
    ) -> CorrectionSignal:
        signal = CorrectionSignal(
            signal_id=f"cl-{len(self._signals) + 1:06d}",
            bundle_id=bundle_id,
            field_name=field_name,
            ai_value=ai_value,
            human_value=human_value,
            correction_type=correction_type,
            confidence_at_override=confidence,
            override_reason=override_reason,
        )
        self._signals.append(signal)
        return signal

    def signals_for_field(self, field_name: str) -> list[CorrectionSignal]:
        return [s for s in self._signals if s.field_name == field_name]

    def detect_patterns(self) -> list[LearningPattern]:
        field_groups: dict[str, list[CorrectionSignal]] = {}
        for signal in self._signals:
            field_groups.setdefault(signal.field_name, []).append(signal)

        patterns: list[LearningPattern] = []
        for field_name, signals in field_groups.items():
            if len(signals) < _MIN_SAMPLES_FOR_PATTERN:
                continue

            values = [s.human_value for s in signals]
            from collections import Counter

            value_counts = Counter(values)
            common_value = value_counts.most_common(1)[0][0] if value_counts else ""

            avg_conf = sum(s.confidence_at_override for s in signals) / len(signals) if signals else 0.0

            action = "retrain_extractor"
            if avg_conf > 0.8:
                action = "verify_source_data_quality"
            elif len(signals) > 10:
                action = "add_hard_rule"

            pattern = LearningPattern(
                pattern_id=f"lp-{field_name}-{len(self._patterns) + 1:04d}",
                field_name=field_name,
                description=f"{len(signals)} overrides on {field_name}, most common correction: {common_value!r}",
                sample_count=len(signals),
                common_correction=common_value,
                avg_confidence_when_overridden=avg_conf,
                suggested_action=action,
            )
            patterns.append(pattern)

        self._patterns = patterns
        return patterns

    def calibration_adjustments(self) -> list[CalibrationAdjustment]:
        adjustments: list[CalibrationAdjustment] = []
        field_groups: dict[str, list[CorrectionSignal]] = {}
        for signal in self._signals:
            field_groups.setdefault(signal.field_name, []).append(signal)

        for field_name, signals in field_groups.items():
            if len(signals) < _MIN_SAMPLES_FOR_PATTERN:
                continue
            avg_conf = sum(s.confidence_at_override for s in signals) / len(signals)
            adjustment = 0.0
            if avg_conf > 0.7 and len(signals) > 5:
                adjustment = -0.1
            elif avg_conf < 0.4:
                adjustment = 0.05

            adjustments.append(
                CalibrationAdjustment(
                    field_name=field_name,
                    recommended_adjustment=adjustment,
                    sample_size=len(signals),
                    reasoning=(
                        f"Field {field_name} overridden {len(signals)} times with "
                        f"avg confidence {avg_conf:.2f}. "
                        f"{'Consider lowering confidence offset.' if adjustment < 0 else 'Confidence calibration appears stable.'}"
                    ),
                )
            )
        return adjustments

    def summary(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "total_corrections": len(self._signals),
            "unique_fields": len({s.field_name for s in self._signals}),
            "patterns_detected": len(self._patterns),
            "fields_with_signals": list({s.field_name for s in self._signals}),
        }
