"""Churn prediction — policy non-renewal risk scoring + retention recommendations."""

from __future__ import annotations

from typing import Any

import numpy as np

from insureflow.ml.base import BaseMLModel
from insureflow.ml.features import extract_features, get_feature_names
from insureflow.ml.models import ChurnPrediction, FeatureVector, ModelType


class ChurnPredictionModel(BaseMLModel):
    model_type = ModelType.CHURN_PREDICTION
    model_name = "Churn Prediction (Non-Renewal Risk)"

    def __init__(self) -> None:
        super().__init__()

    def _build_model(self) -> Any:
        from sklearn.ensemble import GradientBoostingClassifier

        return GradientBoostingClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )

    def _get_feature_names(self) -> list[str]:
        return get_feature_names()

    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        return extract_features(fv)

    def _compute_metrics(
        self,
        y_train: np.ndarray,
        train_pred: np.ndarray,
        y_val: np.ndarray,
        val_pred: np.ndarray,
    ) -> dict[str, float]:
        from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

        return {
            "train_accuracy": float(accuracy_score(y_train.astype(int), train_pred.astype(int))),
            "val_accuracy": float(accuracy_score(y_val.astype(int), val_pred.astype(int))),
            "val_f1": float(f1_score(y_val.astype(int), val_pred.astype(int), zero_division=0)),
            "val_roc_auc": float(roc_auc_score(y_val, val_pred)) if len(set(y_val.astype(int))) > 1 else 0.5,
        }

    def _compute_feature_importance(self) -> dict[str, float]:
        importance = {}
        if self.model is not None and hasattr(self.model, "feature_importances_"):
            for i, name in enumerate(self.feature_names):
                if i < len(self.model.feature_importances_):
                    importance[name] = round(float(self.model.feature_importances_[i]), 4)
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def _fallback_prediction(self, fv: FeatureVector) -> dict[str, Any]:
        """Rule-based churn estimation."""
        churn_prob = 0.1
        risk_factors = []
        actions = []

        if fv.loss_ratio > 1.0:
            churn_prob += 0.25
            risk_factors.append(f"High loss ratio: {fv.loss_ratio:.1%}")
            actions.append("Offer loss mitigation consultation")
        if fv.credit_score < 600:
            churn_prob += 0.15
            risk_factors.append(f"Low credit score: {fv.credit_score:.0f}")
        if fv.years_in_business < 2:
            churn_prob += 0.15
            risk_factors.append("New business (< 2 years)")
            actions.append("Offer new-business incentive program")
        if fv.prior_cancellations > 1:
            churn_prob += 0.1
            risk_factors.append(f"{fv.prior_cancellations} prior cancellations")
        if fv.requested_premium > fv.tiv * 0.04:
            churn_prob += 0.1
            risk_factors.append("Premium above market average")
            actions.append("Review pricing competitiveness")

        churn_prob = min(churn_prob, 0.95)
        ltv = fv.requested_premium * max(fv.years_in_business, 1) * 0.8
        churn_cost = ltv * churn_prob

        if not actions:
            actions = ["Standard renewal outreach", "Annual coverage review"]

        return ChurnPrediction(
            churn_probability=round(churn_prob, 4),
            risk_factors=risk_factors,
            retention_actions=actions,
            lifetime_value=round(ltv, 2),
            churn_cost=round(churn_cost, 2),
            renewal_premium_suggestion=round(fv.requested_premium * 0.95, 2),
            model_version="fallback",
        ).model_dump()

    def _format_prediction(self, fv: FeatureVector, raw_prediction: Any) -> dict[str, Any]:
        features = self._extract_features(fv).reshape(1, -1)
        churn_prob = float(self.model.predict_proba(features)[0, 1])
        ltv = fv.requested_premium * max(fv.years_in_business, 1) * 0.8
        churn_cost = ltv * churn_prob

        return ChurnPrediction(
            churn_probability=round(churn_prob, 4),
            risk_factors=[],
            retention_actions=[],
            lifetime_value=round(ltv, 2),
            churn_cost=round(churn_cost, 2),
            renewal_premium_suggestion=round(fv.requested_premium * (1 - churn_prob * 0.1), 2),
            model_version=self.version,
        ).model_dump()
