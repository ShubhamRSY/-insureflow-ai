"""Behavioral scoring — broker/submission quality, consistency, accuracy, timeliness."""

from __future__ import annotations

from typing import Any

import numpy as np

from insureflow.ml.models import BehavioralScore, ModelType


class BehavioralScoringModel:
    """Broker and submission quality scoring engine."""

    model_type = ModelType.BEHAVIORAL_SCORING
    model_name = "Behavioral Scoring"
    version: str = "1.0.0"

    def __init__(self) -> None:
        self.is_trained = True

    def score_broker(
        self,
        broker_id: str,
        submission_count: int = 0,
        avg_data_completeness: float = 0.0,
        override_rate: float = 0.0,
        avg_loss_ratio: float = 0.0,
        on_time_rate: float = 0.0,
        accuracy_rate: float = 0.0,
        loss_ratio_history: list[float] | None = None,
        prior_submissions: list[dict[str, Any]] | None = None,
    ) -> BehavioralScore:
        """Score a broker's behavioral quality."""
        experience_factor = min(submission_count / 50, 1.0)

        completeness = min(avg_data_completeness, 1.0) if avg_data_completeness > 0 else 0.5
        quality_score = completeness * 30 + (1 - min(override_rate, 1.0)) * 25 + min(accuracy_rate, 1.0) * 25 + experience_factor * 20

        consistency_vals = []
        if loss_ratio_history and len(loss_ratio_history) > 1:
            std_lr = np.std(loss_ratio_history)
            consistency_vals.append(max(0, 100 - std_lr * 100))
        consistency_score = np.mean(consistency_vals) if consistency_vals else 50.0

        accuracy_score = min(accuracy_rate * 100, 100) if accuracy_rate > 0 else 50.0
        timeliness_score = min(on_time_rate * 100, 100) if on_time_rate > 0 else 50.0

        overall = quality_score * 0.4 + consistency_score * 0.25 + accuracy_score * 0.2 + timeliness_score * 0.15
        grade = "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 55 else "D" if overall >= 40 else "F"

        trend = "stable"
        if len(loss_ratio_history or []) >= 3:
            recent = np.mean(loss_ratio_history[-3:])
            earlier = np.mean(loss_ratio_history[:-3]) if len(loss_ratio_history) > 3 else recent
            if recent < earlier * 0.9:
                trend = "improving"
            elif recent > earlier * 1.1:
                trend = "declining"

        return BehavioralScore(
            entity_id=broker_id,
            entity_type="broker",
            quality_score=round(quality_score, 1),
            consistency_score=round(consistency_score, 1),
            accuracy_score=round(accuracy_score, 1),
            timeliness_score=round(timeliness_score, 1),
            overall_grade=grade,
            trend=trend,
            data_completeness=round(completeness, 3),
            override_rate=round(override_rate, 3),
            loss_ratio_history=loss_ratio_history or [],
            model_version=self.version,
        )

    def score_submission(
        self,
        submission_id: str,
        data_fields_present: int = 0,
        total_fields_expected: int = 20,
        has_acord: bool = False,
        has_loss_run: bool = False,
        has_inspection: bool = False,
        has_sov: bool = False,
        prior_claims_documented: bool = True,
    ) -> BehavioralScore:
        """Score a submission's data quality."""
        completeness = data_fields_present / max(total_fields_expected, 1)
        doc_score = sum([has_acord * 30, has_loss_run * 25, has_inspection * 25, has_sov * 20])
        quality_score = completeness * 60 + doc_score * 0.4

        grade = "A" if quality_score >= 85 else "B" if quality_score >= 70 else "C" if quality_score >= 55 else "D" if quality_score >= 40 else "F"

        return BehavioralScore(
            entity_id=submission_id,
            entity_type="submission",
            quality_score=round(quality_score, 1),
            consistency_score=0.0,
            accuracy_score=round(completeness * 100, 1),
            timeliness_score=0.0,
            overall_grade=grade,
            trend="stable",
            data_completeness=round(completeness, 3),
            override_rate=0.0,
            model_version=self.version,
        )
