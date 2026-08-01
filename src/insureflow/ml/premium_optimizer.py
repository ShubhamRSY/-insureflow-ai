"""Premium optimization — price elasticity modeling + margin optimization."""

from __future__ import annotations

from typing import Any

import numpy as np

from insureflow.ml.base import BaseMLModel
from insureflow.ml.features import extract_features, get_feature_names
from insureflow.ml.models import FeatureVector, ModelType, PremiumRecommendation


class PremiumOptimizerModel(BaseMLModel):
    model_type = ModelType.PREMIUM_OPTIMIZER
    model_name = "Premium Optimization (Elasticity + Margin)"

    def __init__(self) -> None:
        super().__init__()
        self.price_model: Any = None
        self.retention_model: Any = None

    def _build_model(self) -> Any:
        from sklearn.ensemble import GradientBoostingRegressor

        self.price_model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )
        self.retention_model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )
        return self.price_model

    def _get_feature_names(self) -> list[str]:
        return get_feature_names()

    def _estimator_attributes(self) -> list[str]:
        return ["price_model", "retention_model"]

    def _extract_features(self, fv: FeatureVector) -> np.ndarray:
        return extract_features(fv)

    def _fit_model(self, X: np.ndarray, y: np.ndarray, **kwargs: Any) -> None:
        """Train the premium-price regressor on the labeled quoted premium target."""
        price_target = np.maximum(y, 0)
        loss_ratio = X[:, 7]
        credit = X[:, 8]
        claims = X[:, 3]
        cancellations = X[:, 21]
        years = X[:, 2]
        risk_score = (
            loss_ratio * 0.3
            + (1 - np.clip(credit / 850, 0, 1)) * 0.2
            + np.clip(claims / 10, 0, 1) * 0.2
            + np.clip(cancellations / 5, 0, 1) * 0.15
            + (1 - np.clip(years / 30, 0, 1)) * 0.15
        )
        retention_target = np.clip(1.0 - risk_score * 0.5, 0.05, 1.0)

        self.price_model.fit(X, price_target)
        self.retention_model.fit(X, retention_target)
        self.model = self.price_model

    def _compute_metrics(
        self,
        y_train: np.ndarray,
        train_pred: np.ndarray,
        y_val: np.ndarray,
        val_pred: np.ndarray,
    ) -> dict[str, float]:
        from sklearn.metrics import mean_absolute_error, r2_score

        return {
            "train_r2": float(r2_score(y_train, train_pred)),
            "val_r2": float(r2_score(y_val, val_pred)),
            "val_mae": float(mean_absolute_error(y_val, val_pred)),
        }

    def _compute_feature_importance(self) -> dict[str, float]:
        importance = {}
        if self.price_model is not None and hasattr(self.price_model, "feature_importances_"):
            for i, name in enumerate(self.feature_names):
                if i < len(self.price_model.feature_importances_):
                    importance[name] = round(float(self.price_model.feature_importances_[i]), 4)
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def _fallback_prediction(self, fv: FeatureVector) -> dict[str, Any]:
        base_premium = fv.tiv * 0.005
        risk_score = (
            fv.loss_ratio * 0.3
            + (1 - min(fv.credit_score / 850, 1.0)) * 0.2
            + min(fv.prior_claims_count / 10, 1.0) * 0.2
            + min(fv.prior_cancellations / 5, 1.0) * 0.15
            + (1 - min(fv.years_in_business / 30, 1.0)) * 0.15
        )
        risk_adjusted = base_premium * (0.8 + risk_score * 0.8)
        margin_target = 0.18
        recommended = risk_adjusted * (1 + margin_target)

        return PremiumRecommendation(
            recommended_premium=round(recommended, 2),
            base_rate=round(base_premium, 2),
            risk_adjustment=round(risk_adjusted - base_premium, 2),
            market_adjustment=0.0,
            margin_target=margin_target,
            elasticity_impact=0.0,
            competitive_position="at_market",
            retention_probability=round(max(0.5, 1.0 - risk_score * 0.3), 2),
            margin_at_price=round(recommended - risk_adjusted, 2),
            model_version="fallback",
        ).model_dump()

    def _format_prediction(self, fv: FeatureVector, raw_prediction: Any) -> dict[str, Any]:
        features = self._extract_features(fv).reshape(1, -1)
        price = float(self.price_model.predict(features)[0])
        retention = float(self.retention_model.predict(features)[0])

        base_premium = fv.tiv * 0.005
        margin_target = 0.18
        recommended = max(price, base_premium * 0.5)
        margin = recommended - base_premium
        elasticity_impact = round((recommended - base_premium) / max(base_premium, 1), 4)

        return PremiumRecommendation(
            recommended_premium=round(recommended, 2),
            base_rate=round(base_premium, 2),
            risk_adjustment=round(recommended - base_premium, 2),
            market_adjustment=0.0,
            margin_target=margin_target,
            elasticity_impact=elasticity_impact,
            competitive_position="below_market" if recommended < base_premium else "above_market" if recommended > base_premium * 1.2 else "at_market",
            retention_probability=round(max(0, min(1, retention)), 2),
            margin_at_price=round(max(0, margin), 2),
            model_version=self.version,
        ).model_dump()
