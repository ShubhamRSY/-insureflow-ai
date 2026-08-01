"""Lending default-risk model — predicts default probability for business and consumer loans."""

from __future__ import annotations

from typing import Any

import numpy as np

from insureflow.ml.base import BaseMLModel
from insureflow.ml.features import extract_lending_features, get_lending_feature_names
from insureflow.ml.models import FeatureVector, LendingDefaultScore, ModelType


class LendingDefaultRiskModel(BaseMLModel):
    model_type = ModelType.LENDING_DEFAULT_RISK
    model_name = "Lending Default Risk"

    def __init__(self) -> None:
        super().__init__()
        self.classifier: Any = None

    def _build_model(self) -> Any:
        from sklearn.ensemble import GradientBoostingClassifier

        self.classifier = GradientBoostingClassifier(
            n_estimators=180,
            max_depth=4,
            learning_rate=0.1,
            min_samples_split=10,
            random_state=42,
        )
        return self.classifier

    def _get_feature_names(self) -> list[str]:
        return get_lending_feature_names()

    def _estimator_attributes(self) -> list[str]:
        return ["classifier"]

    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        return extract_lending_features(fv)

    def _metric_predictions(self, X: np.ndarray) -> np.ndarray:
        if self.classifier is not None and hasattr(self.classifier, "predict_proba"):
            return np.asarray(self.classifier.predict_proba(X))[:, 1]
        return np.asarray(self.model.predict(X))

    def _fit_model(self, X: np.ndarray, y: np.ndarray, **kwargs: Any) -> None:
        self.classifier.fit(X, y.astype(int))
        self.model = self.classifier

    def _compute_metrics(
        self,
        y_train: np.ndarray,
        train_pred: np.ndarray,
        y_val: np.ndarray,
        val_pred: np.ndarray,
    ) -> dict[str, float]:
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

        def _binary(pred: np.ndarray) -> np.ndarray:
            return (np.asarray(pred) > 0.5).astype(int)

        y_train_b, y_val_b = y_train.astype(int), y_val.astype(int)
        return {
            "train_accuracy": float(accuracy_score(y_train_b, _binary(train_pred))),
            "val_accuracy": float(accuracy_score(y_val_b, _binary(val_pred))),
            "val_precision": float(precision_score(y_val_b, _binary(val_pred), zero_division=0)),
            "val_recall": float(recall_score(y_val_b, _binary(val_pred), zero_division=0)),
            "val_f1": float(f1_score(y_val_b, _binary(val_pred), zero_division=0)),
            "val_roc_auc": float(roc_auc_score(y_val_b, val_pred)) if len(set(y_val_b)) > 1 else 0.5,
        }

    def _compute_feature_importance(self) -> dict[str, float]:
        importance = {}
        if self.classifier is not None and hasattr(self.classifier, "feature_importances_"):
            for i, name in enumerate(self.feature_names):
                if i < len(self.classifier.feature_importances_):
                    importance[name] = round(float(self.classifier.feature_importances_[i]), 4)
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def _fallback_prediction(self, fv: FeatureVector) -> dict[str, Any]:
        """Rule-based lending default scoring when no model is trained."""
        score = 0.0
        factors: list[str] = []
        is_business = (fv.loan_segment or "").lower() in ("business", "b2b")

        if is_business:
            if fv.dscr > 0 and fv.dscr < 1.15:
                score += 0.25
                factors.append(f"DSCR {fv.dscr:.2f}x below 1.15x")
            if fv.leverage_ratio > 4.0:
                score += 0.15
                factors.append(f"Leverage {fv.leverage_ratio:.2f}x above 4.0x")
            if 0 < fv.current_ratio < 1.0:
                score += 0.12
                factors.append(f"Current ratio {fv.current_ratio:.2f}x below 1.0x")
            if fv.profit_margin > 0 and fv.profit_margin < 5:
                score += 0.1
                factors.append(f"Thin profit margin {fv.profit_margin:.1f}%")
            if 0 < fv.years_in_business < 2:
                score += 0.1
                factors.append(f"Business only {fv.years_in_business:.0f} years old")
        else:
            if fv.credit_score > 0 and fv.credit_score < 620:
                score += 0.28
                factors.append(f"Credit score {fv.credit_score:.0f} below 620")
            if fv.dti_ratio > 43:
                score += 0.22
                factors.append(f"DTI {fv.dti_ratio:.1f}% exceeds 43%")
            if 0 < fv.employment_years < 1:
                score += 0.1
                factors.append("Less than 1 year at current employer")

        if fv.credit_score > 0 and fv.credit_score < 580:
            score += 0.12
            factors.append(f"Credit score {fv.credit_score:.0f} below 580")
        score += min(fv.bankruptcies, 3) * 0.2
        score += min(fv.foreclosures, 3) * 0.18
        if fv.bankruptcies > 0 or fv.foreclosures > 0:
            factors.append("Bankruptcy/foreclosure in recent history")

        score = min(max(score, 0.01), 1.0)
        risk_level = "critical" if score > 0.7 else "high" if score > 0.5 else "medium" if score > 0.3 else "low"
        structure = "secured_with_guarantor" if risk_level in ("high", "critical") else "guarantor_required" if risk_level == "medium" else "standard_terms"

        return LendingDefaultScore(
            default_probability=round(score, 4),
            risk_level=risk_level,
            top_factors=factors,
            recommended_structure=structure,
            model_version="fallback",
        ).model_dump()

    def _format_prediction(self, fv: FeatureVector, raw_prediction: Any) -> dict[str, Any]:
        features = self._extract_features(fv).reshape(1, -1)
        if self.classifier is not None and hasattr(self.classifier, "predict_proba"):
            prob = float(self.classifier.predict_proba(features)[0, 1])
        else:
            prob = float(raw_prediction)

        risk_level = "critical" if prob > 0.7 else "high" if prob > 0.5 else "medium" if prob > 0.3 else "low"
        structure = "secured_with_guarantor" if risk_level in ("high", "critical") else "guarantor_required" if risk_level == "medium" else "standard_terms"

        return LendingDefaultScore(
            default_probability=round(max(0.0, min(1.0, prob)), 4),
            risk_level=risk_level,
            top_factors=[],
            recommended_structure=structure,
            model_version=self.version,
        ).model_dump()
