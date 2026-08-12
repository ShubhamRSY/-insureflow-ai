"""Loss prediction model — predicts claim frequency and severity from submission features."""

from __future__ import annotations

from typing import Any

import numpy as np

from insureflow.ml.base import BaseMLModel
from insureflow.ml.features import extract_features, get_feature_names
from insureflow.ml.models import FeatureVector, LossPrediction, ModelType


class LossPredictionModel(BaseMLModel):
    model_type = ModelType.LOSS_PREDICTION
    model_name = "Loss Prediction (Frequency × Severity)"

    def __init__(self) -> None:
        super().__init__()
        self.loss_model: Any = None
        self.severity_model: Any = None

    def _build_model(self) -> Any:
        from sklearn.ensemble import GradientBoostingRegressor

        self.loss_model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            min_samples_split=10,
            random_state=42,
        )
        self.severity_model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            min_samples_split=10,
            random_state=42,
        )
        return self.loss_model

    def _get_feature_names(self) -> list[str]:
        return get_feature_names()

    def _estimator_attributes(self) -> list[str]:
        return ["loss_model", "severity_model"]

    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        return extract_features(fv)

    def _fit_model(self, X: np.ndarray, y: np.ndarray, **kwargs: Any) -> None:
        """Train the expected-loss regressor and a severity model for the decomposition."""
        loss_target = np.maximum(y, 0)
        severity_target = np.where(y > 0, y, np.median(y[y > 0]) if np.any(y > 0) else 0)

        self.loss_model.fit(X, loss_target)
        self.severity_model.fit(X, severity_target)
        self.model = self.loss_model

    def _compute_metrics(
        self,
        y_train: np.ndarray,
        train_pred: np.ndarray,
        y_val: np.ndarray,
        val_pred: np.ndarray,
    ) -> dict[str, float]:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        return {
            "train_mae": float(mean_absolute_error(y_train, train_pred)),
            "val_mae": float(mean_absolute_error(y_val, val_pred)),
            "train_rmse": float(np.sqrt(mean_squared_error(y_train, train_pred))),
            "val_rmse": float(np.sqrt(mean_squared_error(y_val, val_pred))),
            "train_r2": float(r2_score(y_train, train_pred)),
            "val_r2": float(r2_score(y_val, val_pred)),
        }

    def _compute_feature_importance(self) -> dict[str, float]:
        importance = {}
        if self.loss_model is not None and hasattr(self.loss_model, "feature_importances_"):
            for i, name in enumerate(self.feature_names):
                if i < len(self.loss_model.feature_importances_):
                    importance[name] = round(float(self.loss_model.feature_importances_[i]), 4)
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def _fallback_prediction(self, fv: FeatureVector) -> dict[str, Any]:
        """Rule-based fallback when no model is trained — LOB-adjusted when product_line set."""
        from insureflow.ml.lob_profiles import lob_loss_fallback, lob_risk_factors

        line = fv.product_line or (fv.custom_features or {}).get("insurance_line", "")
        if line:
            base_frequency, base_severity, expected_loss = lob_loss_fallback(line, fv)
            risk_factors = lob_risk_factors(line, fv)
            model_version = f"lob-fallback:{line}"
        else:
            base_frequency = 0.05 + (fv.prior_claims_count / max(fv.years_in_business, 1)) * 0.1
            base_severity = fv.tiv * 0.005 * fv.loss_ratio if fv.loss_ratio > 0 else fv.tiv * 0.01
            expected_loss = base_frequency * base_severity
            risk_factors = []
            if fv.loss_ratio > 1.0:
                risk_factors.append(f"Historical loss ratio {fv.loss_ratio:.1%} exceeds 100%")
            if fv.prior_claims_count > 3:
                risk_factors.append(f"{fv.prior_claims_count} prior claims in {fv.years_in_business:.0f} years")
            if fv.credit_score < 600:
                risk_factors.append(f"Low credit score: {fv.credit_score:.0f}")
            if fv.tiv > 1e8:
                risk_factors.append(f"High TIV: ${fv.tiv / 1e6:.0f}M")
            model_version = "fallback"

        return LossPrediction(
            expected_frequency=round(base_frequency, 4),
            expected_severity=round(base_severity, 2),
            expected_loss=round(expected_loss, 2),
            loss_range_low=round(expected_loss * 0.5, 2),
            loss_range_high=round(expected_loss * 2.0, 2),
            confidence=0.65,
            top_risk_factors=risk_factors,
            model_version=model_version,
        ).model_dump()

    def _format_prediction(self, fv: FeatureVector, raw_prediction: Any) -> dict[str, Any]:
        expected_loss = max(float(raw_prediction), 0)
        severity = float(self.severity_model.predict(self._extract_features(fv).reshape(1, -1))[0]) if self.severity_model else 0
        severity = max(severity, 1)
        frequency = expected_loss / severity

        return LossPrediction(
            expected_frequency=round(frequency, 4),
            expected_severity=round(severity, 2),
            expected_loss=round(expected_loss, 2),
            loss_range_low=round(expected_loss * 0.5, 2),
            loss_range_high=round(expected_loss * 2.0, 2),
            confidence=round(max(0.0, min(0.95, self.metrics.get("val_r2", 0.5) + 0.3)), 2),
            top_risk_factors=[],
            model_version=self.version,
        ).model_dump()
