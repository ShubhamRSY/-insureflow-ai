"""Mortgage default-risk model — predicts delinquency/default probability from borrower + property features."""

from __future__ import annotations

from typing import Any

import numpy as np

from insureflow.ml.base import BaseMLModel
from insureflow.ml.features import extract_mortgage_features, get_mortgage_feature_names
from insureflow.ml.models import FeatureVector, ModelType, MortgageDefaultScore


class MortgageDefaultRiskModel(BaseMLModel):
    model_type = ModelType.MORTGAGE_DEFAULT_RISK
    model_name = "Mortgage Default Risk"

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
        return get_mortgage_feature_names()

    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        return extract_mortgage_features(fv)

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
            "val_roc_auc": float(roc_auc_score(y_val_b, _binary(val_pred))) if len(set(y_val_b)) > 1 else 0.5,
        }

    def _compute_feature_importance(self) -> dict[str, float]:
        importance = {}
        if self.classifier is not None and hasattr(self.classifier, "feature_importances_"):
            for i, name in enumerate(self.feature_names):
                if i < len(self.classifier.feature_importances_):
                    importance[name] = round(float(self.classifier.feature_importances_[i]), 4)
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def _fallback_prediction(self, fv: FeatureVector) -> dict[str, Any]:
        """Rule-based mortgage default scoring when no model is trained."""
        score = 0.0
        factors: list[str] = []

        if fv.credit_score > 0:
            if fv.credit_score < 580:
                score += 0.35
                factors.append(f"Credit score {fv.credit_score:.0f} below 580")
            elif fv.credit_score < 620:
                score += 0.2
                factors.append(f"Credit score {fv.credit_score:.0f} below 620")
            elif fv.credit_score < 680:
                score += 0.08
                factors.append(f"Credit score {fv.credit_score:.0f} in 620-680 band")
        if fv.dti_ratio > 43:
            score += 0.22
            factors.append(f"DTI {fv.dti_ratio:.1f}% exceeds 43%")
        if fv.ltv_ratio > 80:
            score += 0.18
            factors.append(f"LTV {fv.ltv_ratio:.1f}% above 80%")
        if 0 < fv.reserves < 10000:
            score += 0.12
            factors.append(f"Low liquid reserves ${fv.reserves:,.0f}")
        if fv.self_employment_income > 0:
            score += 0.08
            factors.append("Self-employment income requires 2-year averaging")
        if fv.utilization_rate > 50:
            score += 0.1
            factors.append(f"Revolving utilization {fv.utilization_rate:.0f}%")
        score += min(fv.bankruptcies, 3) * 0.2
        score += min(fv.foreclosures, 3) * 0.18
        if fv.derogatory_marks > 0:
            score += min(fv.derogatory_marks, 4) * 0.04
            factors.append(f"{fv.derogatory_marks} derogatory mark(s)")
        if fv.prior_cancellations > 0:
            score += min(fv.prior_cancellations, 3) * 0.03
            factors.append(f"{fv.prior_cancellations} prior cancellation(s)")

        score = min(max(score, 0.01), 1.0)
        risk_level = "critical" if score > 0.7 else "high" if score > 0.5 else "medium" if score > 0.3 else "low"
        band = "90+" if score > 0.7 else "60-90" if score > 0.5 else "30-60" if score > 0.3 else "0-30"
        action = "manual_underwriting_review" if risk_level in ("high", "critical") else "standard_processing"

        return MortgageDefaultScore(
            default_probability=round(score, 4),
            risk_level=risk_level,
            delinquency_band=band,
            top_risk_factors=factors,
            recommended_action=action,
            model_version="fallback",
        ).model_dump()

    def _format_prediction(self, fv: FeatureVector, raw_prediction: Any) -> dict[str, Any]:
        features = self._extract_features(fv).reshape(1, -1)
        if self.classifier is not None and hasattr(self.classifier, "predict_proba"):
            prob = float(self.classifier.predict_proba(features)[0, 1])
        else:
            prob = float(raw_prediction)

        risk_level = "critical" if prob > 0.7 else "high" if prob > 0.5 else "medium" if prob > 0.3 else "low"
        band = "90+" if prob > 0.7 else "60-90" if prob > 0.5 else "30-60" if prob > 0.3 else "0-30"
        action = "manual_underwriting_review" if risk_level in ("high", "critical") else "standard_processing"

        return MortgageDefaultScore(
            default_probability=round(max(0.0, min(1.0, prob)), 4),
            risk_level=risk_level,
            delinquency_band=band,
            top_risk_factors=[],
            recommended_action=action,
            model_version=self.version,
        ).model_dump()
