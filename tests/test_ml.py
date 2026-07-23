"""Tests for ML predictive analytics module — models, training, registry, features, endpoints."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from insureflow.ml.behavioral import BehavioralScoringModel
from insureflow.ml.churn import ChurnPredictionModel
from insureflow.ml.features import (
    CONSTRUCTION_MAP,
    OCCUPANCY_MAP,
    PROTECTION_MAP,
    ROOF_MAP,
    encode_categorical,
    extract_features,
    generate_synthetic_dataset,
    get_feature_names,
)
from insureflow.ml.fraud_detection import FraudDetectionModel
from insureflow.ml.loss_prediction import LossPredictionModel
from insureflow.ml.models import (
    ChurnPrediction,
    FeatureVector,
    FraudScore,
    LossPrediction,
    ModelStatus,
    ModelType,
    PortfolioRiskResult,
    PremiumRecommendation,
    TrainingResult,
)
from insureflow.ml.portfolio_risk import PortfolioRiskModel
from insureflow.ml.premium_optimizer import PremiumOptimizerModel
from insureflow.ml.registry import get_ml_registry
from insureflow.ml.training import (
    TRAINING_CONFIGS,
    get_training_status,
    retrain_model,
    train_all_models,
)

# ===========================================================================
# 1. MODELS — Pydantic schema validation
# ===========================================================================


class TestMLModels:
    """Validate Pydantic models for ML predictions."""

    def test_feature_vector_defaults(self) -> None:
        fv = FeatureVector()
        assert fv.revenue == 0.0
        assert fv.employees == 0
        assert fv.credit_score == 0.0
        assert fv.custom_features == {}

    def test_feature_vector_with_data(self) -> None:
        fv = FeatureVector(
            revenue=5_000_000,
            employees=100,
            years_in_business=10,
            prior_claims_count=2,
            tiv=10_000_000,
            credit_score=720,
            loss_ratio=0.65,
        )
        assert fv.revenue == 5_000_000
        assert fv.employees == 100

    def test_loss_prediction_validates(self) -> None:
        lp = LossPrediction(
            expected_frequency=0.15,
            expected_severity=50000,
            expected_loss=7500,
            loss_range_low=3750,
            loss_range_high=15000,
            confidence=0.82,
        )
        assert lp.confidence >= 0 and lp.confidence <= 1
        assert lp.expected_loss == lp.expected_frequency * lp.expected_severity

    def test_fraud_score_validates(self) -> None:
        fs = FraudScore(
            fraud_probability=0.75,
            anomaly_score=0.5,
            risk_level="high",
            flagged_patterns=["Extreme loss ratio: 150%"],
        )
        assert fs.fraud_probability >= 0 and fs.fraud_probability <= 1
        assert fs.risk_level in ("low", "medium", "high", "critical")

    def test_premium_recommendation_validates(self) -> None:
        pr = PremiumRecommendation(
            recommended_premium=25000,
            base_rate=20000,
            risk_adjustment=3000,
            market_adjustment=2000,
            margin_target=0.18,
            elasticity_impact=-0.5,
            competitive_position="at_market",
            retention_probability=0.85,
            margin_at_price=4500,
        )
        assert pr.retention_probability >= 0 and pr.retention_probability <= 1
        assert pr.recommended_premium > 0

    def test_portfolio_risk_result_validates(self) -> None:
        prr = PortfolioRiskResult(
            total_exposure=1e9,
            expected_loss=15_000_000,
            var_95=25_000_000,
            var_99=40_000_000,
            tail_var=55_000_000,
            cat_contribution=0.12,
            concentration_index=0.25,
            diversification_benefit=0.35,
            scenarios_tested=10000,
        )
        assert prr.var_99 >= prr.expected_loss
        assert prr.tail_var >= prr.var_99

    def test_churn_prediction_validates(self) -> None:
        cp = ChurnPrediction(
            churn_probability=0.45,
            risk_factors=["High loss ratio"],
            retention_actions=["Offer discount"],
            lifetime_value=50000,
            churn_cost=15000,
        )
        assert cp.churn_probability >= 0 and cp.churn_probability <= 1
        assert cp.lifetime_value > 0

    def test_model_type_enum(self) -> None:
        assert ModelType.LOSS_PREDICTION.value == "loss_prediction"
        assert ModelType.FRAUD_DETECTION.value == "fraud_detection"
        assert len(ModelType) == 6

    def test_model_status_enum(self) -> None:
        assert ModelStatus.DRAFT.value == "draft"
        assert ModelStatus.CHAMPION.value == "champion"
        assert len(ModelStatus) == 6

    def test_training_result_validates(self) -> None:
        tr = TrainingResult(
            model_type=ModelType.LOSS_PREDICTION,
            model_version="0.1.1",
            metrics={"val_r2": 0.85},
            feature_importance={"revenue": 0.3},
            training_samples=1600,
            validation_samples=400,
            duration_seconds=5.2,
        )
        assert tr.training_samples + tr.validation_samples == 2000


# ===========================================================================
# 2. FEATURES — Feature engineering
# ===========================================================================


class TestFeatureEngineering:
    """Test feature extraction, encoding, and synthetic data generation."""

    def test_extract_features_shape(self) -> None:
        fv = FeatureVector(revenue=1e6, employees=50, tiv=5e6, credit_score=700)
        features = extract_features(fv)
        assert features.shape == (29,)

    def test_extract_features_dtype(self) -> None:
        fv = FeatureVector()
        features = extract_features(fv)
        assert features.dtype == np.float64

    def test_extract_features_values(self) -> None:
        fv = FeatureVector(
            revenue=1_000_000,
            employees=100,
            years_in_business=10,
            prior_claims_count=2,
            tiv=5_000_000,
            requested_premium=25_000,
            loss_ratio=0.5,
            credit_score=750,
        )
        features = extract_features(fv)
        assert features[0] == 1_000_000  # revenue
        assert features[1] == 100  # employees
        assert features[24] == 1_000_000 / 100  # revenue_per_employee

    def test_extract_features_safety(self) -> None:
        fv = FeatureVector(employees=0, revenue=0, years_in_business=0)
        features = extract_features(fv)
        assert np.all(np.isfinite(features))

    def test_encode_categorical_known(self) -> None:
        assert encode_categorical("frame", CONSTRUCTION_MAP) == 0
        assert encode_categorical("masonry", CONSTRUCTION_MAP) == 1
        assert encode_categorical("office", OCCUPANCY_MAP) == 0
        assert encode_categorical("1", PROTECTION_MAP) == 0
        assert encode_categorical("flat", ROOF_MAP) == 0

    def test_encode_categorical_unknown(self) -> None:
        result = encode_categorical("nonexistent", CONSTRUCTION_MAP)
        assert result == 8  # default empty string mapping

    def test_get_feature_names_length(self) -> None:
        names = get_feature_names()
        assert len(names) == 29

    def test_generate_synthetic_dataset_shapes(self) -> None:
        for model_type in ["loss_prediction", "fraud_detection", "premium_optimizer", "churn_prediction"]:
            X, y = generate_synthetic_dataset(n_samples=100, model_type=model_type, seed=42)
            assert X.shape == (100, 29)
            assert y.shape == (100,)

    def test_generate_synthetic_dataset_deterministic(self) -> None:
        X1, y1 = generate_synthetic_dataset(n_samples=50, model_type="loss_prediction", seed=99)
        X2, y2 = generate_synthetic_dataset(n_samples=50, model_type="loss_prediction", seed=99)
        np.testing.assert_array_equal(X1, X2)
        np.testing.assert_array_equal(y1, y2)

    def test_generate_synthetic_dataset_different_seeds(self) -> None:
        X1, _ = generate_synthetic_dataset(n_samples=50, seed=1)
        X2, _ = generate_synthetic_dataset(n_samples=50, seed=2)
        assert not np.array_equal(X1, X2)

    def test_synthetic_loss_target_positive(self) -> None:
        X, y = generate_synthetic_dataset(n_samples=200, model_type="loss_prediction")
        assert np.all(y >= 0)

    def test_synthetic_fraud_target_binary(self) -> None:
        _, y = generate_synthetic_dataset(n_samples=500, model_type="fraud_detection")
        assert set(np.unique(y)).issubset({0.0, 1.0})
        fraud_rate = y.mean()
        assert 0.01 < fraud_rate < 0.20  # Reasonable fraud rate

    def test_synthetic_premium_target_positive(self) -> None:
        _, y = generate_synthetic_dataset(n_samples=200, model_type="premium_optimizer")
        assert np.all(y > 0)

    def test_synthetic_churn_target_binary(self) -> None:
        _, y = generate_synthetic_dataset(n_samples=500, model_type="churn_prediction")
        assert set(np.unique(y)).issubset({0.0, 1.0})


# ===========================================================================
# 3. INDIVIDUAL MODELS — Training, prediction, fallback
# ===========================================================================


class TestLossPredictionModel:
    """Test LossPredictionModel training, prediction, fallback."""

    def test_init(self) -> None:
        model = LossPredictionModel()
        assert model.model_type == ModelType.LOSS_PREDICTION
        assert model.status == ModelStatus.DRAFT
        assert not model.is_trained

    def test_train(self) -> None:
        model = LossPredictionModel()
        X, y = generate_synthetic_dataset(500, "loss_prediction", seed=42)
        result = model.train(X, y)
        assert model.is_trained
        assert model.status == ModelStatus.READY
        assert "val_r2" in result.metrics
        assert result.training_samples == 400
        assert result.validation_samples == 100

    def test_predict_trained(self) -> None:
        model = LossPredictionModel()
        X, y = generate_synthetic_dataset(500, "loss_prediction", seed=42)
        model.train(X, y)
        fv = FeatureVector(tiv=5_000_000, loss_ratio=0.7, credit_score=700)
        pred = model.predict(fv)
        assert "expected_frequency" in pred
        assert "expected_severity" in pred
        assert "expected_loss" in pred
        assert pred["expected_loss"] >= 0

    def test_predict_untrained_fallback(self) -> None:
        model = LossPredictionModel()
        fv = FeatureVector(tiv=10_000_000, loss_ratio=1.2, prior_claims_count=5)
        pred = model.predict(fv)
        assert pred["model_version"] == "fallback"
        assert "expected_loss" in pred
        assert len(pred["top_risk_factors"]) > 0

    def test_fallback_risk_factors(self) -> None:
        model = LossPredictionModel()
        fv = FeatureVector(
            tiv=1e8,
            loss_ratio=1.5,
            prior_claims_count=10,
            credit_score=500,
            years_in_business=0.5,
        )
        pred = model.predict(fv)
        assert len(pred["top_risk_factors"]) >= 3

    def test_explain_trained(self) -> None:
        model = LossPredictionModel()
        X, y = generate_synthetic_dataset(500, "loss_prediction", seed=42)
        model.train(X, y)
        fv = FeatureVector(tiv=5_000_000)
        explanation = model.explain(fv)
        assert "top_factors" in explanation
        assert explanation["method"] == "feature_contribution"

    def test_explain_untrained(self) -> None:
        model = LossPredictionModel()
        fv = FeatureVector()
        explanation = model.explain(fv)
        assert explanation["method"] == "fallback"


class TestFraudDetectionModel:
    """Test FraudDetectionModel training, prediction, fallback."""

    def test_init(self) -> None:
        model = FraudDetectionModel()
        assert model.model_type == ModelType.FRAUD_DETECTION

    def test_train(self) -> None:
        model = FraudDetectionModel()
        X, y = generate_synthetic_dataset(500, "fraud_detection", seed=42)
        result = model.train(X, y)
        assert model.is_trained
        assert "val_accuracy" in result.metrics

    def test_predict_trained(self) -> None:
        model = FraudDetectionModel()
        X, y = generate_synthetic_dataset(500, "fraud_detection", seed=42)
        model.train(X, y)
        fv = FeatureVector(loss_ratio=0.5, credit_score=700, prior_claims_count=1)
        pred = model.predict(fv)
        assert "fraud_probability" in pred
        assert "risk_level" in pred
        assert 0 <= pred["fraud_probability"] <= 1

    def test_predict_untrained_fallback(self) -> None:
        model = FraudDetectionModel()
        fv = FeatureVector(loss_ratio=2.0, credit_score=400, prior_claims_count=10, prior_cancellations=5)
        pred = model.predict(fv)
        assert pred["model_version"] == "fallback"
        assert pred["risk_level"] in ("low", "medium", "high", "critical")

    def test_fallback_suspicious_input_high_risk(self) -> None:
        model = FraudDetectionModel()
        fv = FeatureVector(
            loss_ratio=2.0,
            prior_claims_count=10,
            credit_score=400,
            prior_cancellations=5,
            years_in_business=0.5,
        )
        pred = model.predict(fv)
        assert pred["fraud_probability"] >= 0.5
        assert pred["risk_level"] in ("high", "critical")

    def test_fallback_clean_input_low_risk(self) -> None:
        model = FraudDetectionModel()
        fv = FeatureVector(
            loss_ratio=0.3,
            prior_claims_count=0,
            credit_score=800,
            prior_cancellations=0,
            years_in_business=20,
        )
        pred = model.predict(fv)
        assert pred["fraud_probability"] < 0.3
        assert pred["risk_level"] == "low"


class TestPremiumOptimizerModel:
    """Test PremiumOptimizerModel training, prediction, fallback."""

    def test_init(self) -> None:
        model = PremiumOptimizerModel()
        assert model.model_type == ModelType.PREMIUM_OPTIMIZER

    def test_train(self) -> None:
        model = PremiumOptimizerModel()
        X, y = generate_synthetic_dataset(500, "premium_optimizer", seed=42)
        result = model.train(X, y)
        assert model.is_trained
        assert "val_r2" in result.metrics

    def test_predict_untrained_fallback(self) -> None:
        model = PremiumOptimizerModel()
        fv = FeatureVector(tiv=10_000_000, loss_ratio=0.5, credit_score=700, prior_claims_count=1)
        pred = model.predict(fv)
        assert pred["model_version"] == "fallback"
        assert pred["recommended_premium"] > 0
        assert pred["retention_probability"] >= 0

    def test_fallback_high_risk_premium(self) -> None:
        model = PremiumOptimizerModel()
        fv = FeatureVector(tiv=50_000_000, loss_ratio=1.5, credit_score=500, prior_claims_count=8)
        pred = model.predict(fv)
        assert pred["recommended_premium"] > pred["base_rate"]


class TestChurnPredictionModel:
    """Test ChurnPredictionModel training, prediction, fallback."""

    def test_init(self) -> None:
        model = ChurnPredictionModel()
        assert model.model_type == ModelType.CHURN_PREDICTION

    def test_train(self) -> None:
        model = ChurnPredictionModel()
        X, y = generate_synthetic_dataset(500, "churn_prediction", seed=42)
        model.train(X, y)
        assert model.is_trained

    def test_predict_untrained_fallback(self) -> None:
        model = ChurnPredictionModel()
        fv = FeatureVector(loss_ratio=1.5, credit_score=500, years_in_business=1)
        pred = model.predict(fv)
        assert pred["model_version"] == "fallback"
        assert 0 <= pred["churn_probability"] <= 1


class TestBehavioralScoringModel:
    """Test BehavioralScoringModel — no sklearn training needed."""

    def test_score_broker(self) -> None:
        model = BehavioralScoringModel()
        score = model.score_broker(
            broker_id="B001",
            avg_data_completeness=0.95,
            override_rate=0.05,
            loss_ratio_history=[0.4, 0.5, 0.45, 0.48],
            on_time_rate=0.9,
            submission_count=50,
        )
        assert score.entity_id == "B001"
        assert score.quality_score >= 0
        assert score.quality_score <= 100
        assert score.overall_grade in ("A", "B", "C", "D", "F")


class TestPortfolioRiskModel:
    """Test PortfolioRiskModel — Monte Carlo simulation."""

    def test_simulate_basic(self) -> None:
        model = PortfolioRiskModel(n_simulations=1000, seed=42)
        result = model.simulate(
            exposures=[1e6, 2e6, 3e6],
            loss_probabilities=[0.02, 0.05, 0.01],
            severity_means=[50000, 100000, 200000],
        )
        assert result.total_exposure == 6_000_000
        assert result.expected_loss > 0
        assert result.var_95 >= result.expected_loss
        assert result.var_99 >= result.var_95
        assert result.tail_var >= result.var_99
        assert result.scenarios_tested == 1000

    def test_simulate_empty_portfolio(self) -> None:
        model = PortfolioRiskModel()
        result = model.simulate(exposures=[], loss_probabilities=[], severity_means=[])
        assert result.total_exposure == 0
        assert result.expected_loss == 0

    def test_stress_test(self) -> None:
        model = PortfolioRiskModel(n_simulations=500, seed=42)
        results = model.stress_test(
            exposures=[1e6, 2e6],
            loss_probabilities=[0.03, 0.02],
            severity_means=[50000, 80000],
        )
        assert len(results) == 5  # base, mild, severe, catastrophe, pandemic
        # Losses should increase with stress severity
        base_loss = results[0]["expected_loss"]
        severe_loss = results[2]["expected_loss"]
        assert severe_loss >= base_loss

    def test_simulate_concentration_index(self) -> None:
        model = PortfolioRiskModel(n_simulations=500, seed=42)
        result = model.simulate(
            exposures=[1e6, 1e6, 1e6],
            loss_probabilities=[0.02, 0.02, 0.02],
            severity_means=[50000, 50000, 50000],
            concentration_weights=[0.5, 0.25, 0.25],
        )
        assert 0 <= result.concentration_index <= 1


# ===========================================================================
# 4. REGISTRY — Model lifecycle management
# ===========================================================================


class TestMLModelRegistry:
    """Test the MLModelRegistry singleton and model lifecycle."""

    def test_get_registry_singleton(self) -> None:
        r1 = get_ml_registry()
        r2 = get_ml_registry()
        assert r1 is r2

    def test_registry_has_all_models(self) -> None:
        registry = get_ml_registry()
        for mt in ModelType:
            model = registry.get(mt)
            assert model is not None, f"Missing model for {mt.value}"

    def test_registry_status(self) -> None:
        registry = get_ml_registry()
        statuses = registry.get_status()
        assert len(statuses) == 6
        types_found = {s["model_type"] for s in statuses}
        for mt in ModelType:
            assert mt.value in types_found

    def test_registry_train_and_promote(self) -> None:
        registry = get_ml_registry()
        X, y = generate_synthetic_dataset(300, "loss_prediction", seed=99)
        result = registry.train_model(ModelType.LOSS_PREDICTION, X, y)
        assert result is not None
        assert "val_r2" in result.metrics

        promoted = registry.promote_to_champion(ModelType.LOSS_PREDICTION)
        assert promoted

        model = registry.get(ModelType.LOSS_PREDICTION)
        assert model is not None
        assert model.status == ModelStatus.CHAMPION

    def test_registry_history(self) -> None:
        registry = get_ml_registry()
        registry.history.clear()
        X, y = generate_synthetic_dataset(200, "fraud_detection", seed=100)
        registry.train_model(ModelType.FRAUD_DETECTION, X, y)
        assert len(registry.history) >= 1
        assert registry.history[-1]["model_type"] == "fraud_detection"


# ===========================================================================
# 5. TRAINING PIPELINE — Bootstrap and retrain
# ===========================================================================


class TestTrainingPipeline:
    """Test training pipeline functions."""

    def test_train_all_models(self) -> None:
        results = train_all_models(force=True)
        assert len(results) >= 4  # loss, fraud, premium, churn

        for r in results:
            assert r.training_samples > 0
            assert r.validation_samples > 0
            assert r.duration_seconds >= 0

    def test_retrain_single_model(self) -> None:
        result = retrain_model(ModelType.LOSS_PREDICTION, n_samples=300, seed=42)
        assert result is not None
        assert result.model_type == ModelType.LOSS_PREDICTION

    def test_get_training_status(self) -> None:
        status = get_training_status()
        assert "models" in status
        assert "history" in status
        assert "training_configs" in status
        assert len(status["models"]) == 6

    def test_training_configs_cover_all_types(self) -> None:
        for mt in ModelType:
            if mt not in (ModelType.PORTFOLIO_RISK, ModelType.BEHAVIORAL_SCORING):
                assert mt in TRAINING_CONFIGS


# ===========================================================================
# 6. MODEL SAVE / LOAD — Persistence
# ===========================================================================


class TestModelPersistence:
    """Test model save and load from disk."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        model = LossPredictionModel()
        X, y = generate_synthetic_dataset(300, "loss_prediction", seed=42)
        model.train(X, y)

        save_path = tmp_path / "test_model"
        model.save(save_path)
        assert (save_path / "latest.json").exists()

        model2 = LossPredictionModel()
        loaded = model2.load(save_path)
        assert loaded
        assert model2.version == model.version
        assert model2.is_trained

    def test_load_nonexistent_returns_false(self, tmp_path: Path) -> None:
        model = LossPredictionModel()
        assert not model.load(tmp_path / "nonexistent")


# ===========================================================================
# 7. API ENDPOINTS — ML route integration
# ===========================================================================


class TestMLEndpoints:
    """Test ML API endpoints via FastAPI test client."""

    @pytest.fixture(autouse=True)
    def _setup_client(self) -> None:
        from fastapi.testclient import TestClient

        from insureflow.api import app

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_ml_status(self) -> None:
        resp = self.client.get("/ml/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert len(data["models"]) == 6

    def test_ml_models_list(self) -> None:
        resp = self.client.get("/ml/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data

    def test_ml_train_all(self) -> None:
        resp = self.client.post("/ml/train")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert data["trained"] >= 4

    def test_ml_train_single_invalid_type(self) -> None:
        resp = self.client.post("/ml/train/invalid_model_type")
        assert resp.status_code == 400

    def test_ml_train_single_loss(self) -> None:
        resp = self.client.post("/ml/train/loss_prediction")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_type"] == "loss_prediction"

    def test_ml_predict_loss(self) -> None:
        resp = self.client.post(
            "/ml/predict/loss",
            json={
                "tiv": 5_000_000,
                "loss_ratio": 0.65,
                "prior_claims_count": 2,
                "credit_score": 720,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "expected_frequency" in data
        assert "expected_loss" in data

    def test_ml_predict_fraud(self) -> None:
        resp = self.client.post(
            "/ml/predict/fraud",
            json={
                "loss_ratio": 1.5,
                "credit_score": 450,
                "prior_claims_count": 8,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "fraud_probability" in data
        assert "risk_level" in data

    def test_ml_predict_premium(self) -> None:
        self.client.post("/ml/train/premium_optimizer")
        resp = self.client.post(
            "/ml/predict/premium",
            json={
                "tiv": 10_000_000,
                "loss_ratio": 0.5,
                "credit_score": 750,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_premium" in data

    def test_ml_predict_churn(self) -> None:
        self.client.post("/ml/train/churn_prediction")
        resp = self.client.post(
            "/ml/predict/churn",
            json={
                "loss_ratio": 1.2,
                "credit_score": 600,
                "years_in_business": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "churn_probability" in data

    def test_ml_predict_portfolio_risk(self) -> None:
        resp = self.client.post(
            "/ml/predict/portfolio-risk",
            json={
                "exposures": [1e6, 2e6, 3e6],
                "loss_probabilities": [0.02, 0.05, 0.01],
                "severity_means": [50000, 100000, 200000],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_exposure" in data
        assert "var_95" in data

    def test_ml_predict_portfolio_stress(self) -> None:
        resp = self.client.post(
            "/ml/predict/portfolio-stress",
            json={
                "exposures": [1e6, 2e6],
                "loss_probabilities": [0.03, 0.02],
                "severity_means": [50000, 80000],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "scenarios" in data

    def test_ml_score_broker(self) -> None:
        resp = self.client.post(
            "/ml/score/broker",
            json={
                "broker_id": "B001",
                "avg_data_completeness": 0.95,
                "override_rate": 0.05,
                "submission_count": 50,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "quality_score" in data

    def test_ml_score_submission(self) -> None:
        resp = self.client.post(
            "/ml/score/submission",
            json={
                "submission_id": "SUB001",
                "data_fields_present": 15,
                "total_fields_expected": 20,
                "has_acord": True,
                "has_loss_run": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "quality_score" in data

    def test_ml_explain_invalid_type(self) -> None:
        resp = self.client.request("GET", "/ml/explain/invalid_model_type", json={})
        assert resp.status_code in (400, 404)

    def test_ml_explain_loss(self) -> None:
        resp = self.client.request("GET", "/ml/explain/loss_prediction", json={"tiv": 5_000_000})
        assert resp.status_code == 200
        data = resp.json()
        assert "method" in data
        assert "top_factors" in data
