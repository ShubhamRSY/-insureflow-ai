"""Fraud anomaly detection — isolation forest + supervised ensemble for suspicious claims."""

from __future__ import annotations

from typing import Any

import numpy as np

from insureflow.ml.base import BaseMLModel
from insureflow.ml.features import extract_features, get_feature_names
from insureflow.ml.models import FeatureVector, FraudScore, ModelType


class FraudDetectionModel(BaseMLModel):
    model_type = ModelType.FRAUD_DETECTION
    model_name = "Fraud Anomaly Detection"

    def __init__(self) -> None:
        super().__init__()
        self.isolation_forest: Any = None
        self.classifier: Any = None

    def _build_model(self) -> Any:
        from sklearn.ensemble import GradientBoostingClassifier, IsolationForest

        self.isolation_forest = IsolationForest(
            n_estimators=200,
            contamination=0.08,
            random_state=42,
            n_jobs=-1,
        )
        self.classifier = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )
        return self.isolation_forest

    def _get_feature_names(self) -> list[str]:
        return get_feature_names()

    def _estimator_attributes(self) -> list[str]:
        return ["isolation_forest", "classifier"]

    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        return extract_features(fv)

    def _metric_predictions(self, X: np.ndarray) -> np.ndarray:
        if self.classifier is not None and hasattr(self.classifier, "predict_proba"):
            return np.asarray(self.classifier.predict_proba(X))[:, 1]
        return np.asarray(self.model.predict(X))

    def _fit_model(self, X: np.ndarray, y: np.ndarray, **kwargs: Any) -> None:
        self.isolation_forest.fit(X)
        self.classifier.fit(X, y.astype(int))
        self.model = self.isolation_forest

    def _compute_metrics(
        self,
        y_train: np.ndarray,
        train_pred: np.ndarray,
        y_val: np.ndarray,
        val_pred: np.ndarray,
    ) -> dict[str, float]:
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

        train_binary = (np.asarray(train_pred) > 0.5).astype(int)
        val_binary = (np.asarray(val_pred) > 0.5).astype(int)
        y_train_binary = np.asarray(y_train).astype(int)
        y_val_binary = np.asarray(y_val).astype(int)

        return {
            "train_accuracy": float(accuracy_score(y_train_binary, train_binary)),
            "val_accuracy": float(accuracy_score(y_val_binary, val_binary)),
            "val_precision": float(precision_score(y_val_binary, val_binary, zero_division=0)),
            "val_recall": float(recall_score(y_val_binary, val_binary, zero_division=0)),
            "val_f1": float(f1_score(y_val_binary, val_binary, zero_division=0)),
            "val_roc_auc": float(roc_auc_score(y_val_binary, val_pred)) if len(set(y_val_binary)) > 1 else 0.5,
        }

    def _compute_feature_importance(self) -> dict[str, float]:
        importance = {}
        if self.classifier is not None and hasattr(self.classifier, "feature_importances_"):
            for i, name in enumerate(self.feature_names):
                if i < len(self.classifier.feature_importances_):
                    importance[name] = round(float(self.classifier.feature_importances_[i]), 4)
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def _fallback_prediction(self, fv: FeatureVector) -> dict[str, Any]:
        """Rule-based fraud flagging."""
        score = 0.0
        patterns = []

        if fv.loss_ratio > 1.5:
            score += 0.3
            patterns.append(f"Extreme loss ratio: {fv.loss_ratio:.1%}")
        if fv.prior_claims_count > 5:
            score += 0.2
            patterns.append(f"High claim frequency: {fv.prior_claims_count} claims")
        if fv.credit_score < 550:
            score += 0.15
            patterns.append(f"Very low credit score: {fv.credit_score:.0f}")
        if fv.prior_cancellations > 2:
            score += 0.15
            patterns.append(f"Multiple prior cancellations: {fv.prior_cancellations}")
        if fv.requested_premium > 0 and fv.tiv > 0:
            ratio = fv.requested_premium / fv.tiv
            if ratio > 0.05:
                score += 0.1
                patterns.append(f"High premium-to-TIV ratio: {ratio:.1%}")
        if fv.years_in_business < 1:
            score += 0.1
            patterns.append("New business (< 1 year)")

        score = min(score, 1.0)
        risk_level = "critical" if score > 0.7 else "high" if score > 0.5 else "medium" if score > 0.3 else "low"
        action = "escalate_to_fraud_unit" if risk_level == "critical" else "enhanced_review" if risk_level == "high" else "standard_processing"

        return FraudScore(
            fraud_probability=round(score, 4),
            anomaly_score=round(score * 2 - 1, 4),
            risk_level=risk_level,
            flagged_patterns=patterns,
            similar_claims=[],
            recommended_action=action,
            model_version="fallback",
        ).model_dump()

    def _format_prediction(self, fv: FeatureVector, raw_prediction: Any) -> dict[str, Any]:
        features = self._extract_features(fv).reshape(1, -1)
        anomaly_score = float(self.isolation_forest.decision_function(features)[0])
        fraud_prob = float(self.classifier.predict_proba(features)[0, 1]) if self.classifier else max(0, -anomaly_score)

        risk_level = "critical" if fraud_prob > 0.8 else "high" if fraud_prob > 0.6 else "medium" if fraud_prob > 0.3 else "low"

        return FraudScore(
            fraud_probability=round(fraud_prob, 4),
            anomaly_score=round(anomaly_score, 4),
            risk_level=risk_level,
            flagged_patterns=[],
            similar_claims=[],
            recommended_action="escalate_to_fraud_unit" if risk_level == "critical" else "enhanced_review" if risk_level == "high" else "standard_processing",
            model_version=self.version,
        ).model_dump()
