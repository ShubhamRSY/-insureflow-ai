"""Edge case detector — flags unusual risk combinations based on historical data."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Optional

from insureflow.knowledge.tacit_store import KnowledgeType, TacitKnowledgeStore, get_tacit_store

logger = logging.getLogger(__name__)


class EdgeCaseSignal:
    """A signal that a submission contains unusual characteristics."""

    __slots__ = ("signal_type", "field", "value", "expected_range", "anomaly_score", "reason")

    def __init__(
        self,
        signal_type: str,
        field: str,
        value: Any,
        expected_range: str,
        anomaly_score: float,
        reason: str,
    ) -> None:
        self.signal_type = signal_type
        self.field = field
        self.value = value
        self.expected_range = expected_range
        self.anomaly_score = anomaly_score
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "field": self.field,
            "value": self.value,
            "expected_range": self.expected_range,
            "anomaly_score": round(self.anomaly_score, 3),
            "reason": self.reason,
        }


class EdgeCaseDetector:
    """Detects unusual risk combinations by comparing against historical norms."""

    def __init__(self, store: Optional[TacitKnowledgeStore] = None) -> None:
        self.store = store or get_tacit_store()
        self._submissions: list[dict[str, Any]] = []
        self._field_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"values": [], "sum": 0, "count": 0})

    def learn_from_submission(self, submission: dict[str, Any]) -> None:
        self._submissions.append(submission)
        self._update_stats(submission)

    def _update_stats(self, submission: dict[str, Any]) -> None:
        numeric_fields = ["tiv", "total_claims", "total_incurred", "risk_score", "year_built", "square_footage"]
        for field in numeric_fields:
            value = submission.get(field)
            if value is not None and isinstance(value, (int, float)):
                stats = self._field_stats[field]
                stats["values"].append(value)
                stats["sum"] += value
                stats["count"] = len(stats["values"])

        categorical_fields = ["naics_code", "state", "construction_type", "occupancy_type", "coverage_type"]
        for field in categorical_fields:
            value = submission.get(field)
            if value:
                stats = self._field_stats[field]
                if "frequency" not in stats:
                    stats["frequency"] = defaultdict(int)
                stats["frequency"][str(value)] += 1

    def detect_edge_cases(self, submission: dict[str, Any]) -> list[EdgeCaseSignal]:
        signals: list[EdgeCaseSignal] = []
        signals.extend(self._check_numeric_outliers(submission))
        signals.extend(self._check_rare_combinations(submission))
        signals.extend(self._check_known_edge_cases(submission))
        signals.extend(self._check_risk_score_anomalies(submission))
        return sorted(signals, key=lambda s: -s.anomaly_score)

    def _check_numeric_outliers(self, submission: dict[str, Any]) -> list[EdgeCaseSignal]:
        signals: list[EdgeCaseSignal] = []
        numeric_fields = ["tiv", "total_claims", "total_incurred", "square_footage"]

        for field in numeric_fields:
            value = submission.get(field)
            if value is None or not isinstance(value, (int, float)):
                continue
            stats = self._field_stats.get(field)
            if stats is None or stats["count"] < 10:
                continue

            values = stats["values"]
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std_dev = variance**0.5

            if std_dev == 0:
                continue

            z_score = abs(value - mean) / std_dev
            if z_score > 2.5:
                signals.append(
                    EdgeCaseSignal(
                        signal_type="numeric_outlier",
                        field=field,
                        value=value,
                        expected_range=f"{mean - 2 * std_dev:.0f} - {mean + 2 * std_dev:.0f}",
                        anomaly_score=min(1.0, z_score / 5.0),
                        reason=f"{field}={value} is {z_score:.1f} standard deviations from mean ({mean:.0f})",
                    )
                )

        return signals

    def _check_rare_combinations(self, submission: dict[str, Any]) -> list[EdgeCaseSignal]:
        signals: list[EdgeCaseSignal] = []
        combos = [
            ("construction_type", "occupancy_type"),
            ("state", "naics_code"),
            ("construction_type", "state"),
        ]

        for field_a, field_b in combos:
            val_a = str(submission.get(field_a, ""))
            val_b = str(submission.get(field_b, ""))
            if not val_a or not val_b:
                continue

            combo_key = f"{val_a}:{val_b}"
            total = len(self._submissions)
            if total < 20:
                continue

            combo_count = sum(1 for s in self._submissions if str(s.get(field_a, "")) == val_a and str(s.get(field_b, "")) == val_b)
            combo_pct = combo_count / total

            if combo_pct < 0.02 and combo_count <= 2:
                signals.append(
                    EdgeCaseSignal(
                        signal_type="rare_combination",
                        field=f"{field_a}+{field_b}",
                        value=combo_key,
                        expected_range=f"Seen in >2% of submissions (only {combo_count}/{total})",
                        anomaly_score=min(1.0, (1 - combo_pct) * 0.8),
                        reason=f"Combination {combo_key} appears only {combo_count} times in {total} submissions",
                    )
                )

        return signals

    def _check_known_edge_cases(self, submission: dict[str, Any]) -> list[EdgeCaseSignal]:
        signals: list[EdgeCaseSignal] = []
        known_edge_cases = self.store.query(rule_type=KnowledgeType.EDGE_CASE, min_confidence=0.3)

        for rule in known_edge_cases:
            score = rule.matches_submission(submission)
            if score > 0.5:
                signals.append(
                    EdgeCaseSignal(
                        signal_type="known_edge_case",
                        field="multi_factor",
                        value=rule.title,
                        expected_range=rule.description,
                        anomaly_score=score * rule.confidence,
                        reason=f"Matches known edge case: {rule.title} (confidence={rule.confidence:.2f})",
                    )
                )

        return signals

    def _check_risk_score_anomalies(self, submission: dict[str, Any]) -> list[EdgeCaseSignal]:
        signals: list[EdgeCaseSignal] = []
        risk_score = submission.get("risk_score")
        if risk_score is None:
            return signals

        naics = submission.get("naics_code", "")
        if not naics:
            return signals

        naics_scores = [s.get("risk_score", 0.5) for s in self._submissions if s.get("naics_code") == naics and s.get("risk_score") is not None]

        if len(naics_scores) < 5:
            return signals

        mean_score = sum(naics_scores) / len(naics_scores)
        if abs(risk_score - mean_score) > 0.3:
            direction = "higher" if risk_score > mean_score else "lower"
            signals.append(
                EdgeCaseSignal(
                    signal_type="risk_score_anomaly",
                    field="risk_score",
                    value=risk_score,
                    expected_range=f"Mean for NAICS {naics}: {mean_score:.2f}",
                    anomaly_score=min(1.0, abs(risk_score - mean_score)),
                    reason=f"Risk score {risk_score:.2f} is significantly {direction} than typical for NAICS {naics} (mean={mean_score:.2f})",
                )
            )

        return signals

    def get_stats(self) -> dict[str, Any]:
        return {
            "submissions_learned": len(self._submissions),
            "tracked_fields": len(self._field_stats),
            "field_summary": {
                field: {
                    "count": stats.get("count", 0),
                    "unique_values": len(stats.get("frequency", {})),
                }
                for field, stats in self._field_stats.items()
            },
        }
