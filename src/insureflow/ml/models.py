"""Pydantic models for ML predictions and training."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    LOSS_PREDICTION = "loss_prediction"
    FRAUD_DETECTION = "fraud_detection"
    PREMIUM_OPTIMIZER = "premium_optimizer"
    PORTFOLIO_RISK = "portfolio_risk"
    BEHAVIORAL_SCORING = "behavioral_scoring"
    CHURN_PREDICTION = "churn_prediction"


class ModelStatus(str, Enum):
    DRAFT = "draft"
    TRAINING = "training"
    READY = "ready"
    CHAMPION = "champion"
    CHALLENGER = "challenger"
    RETIRED = "retired"


class FeatureVector(BaseModel):
    """Input features for ML prediction."""

    submission_id: str = ""
    naics_code: str = ""
    state: str = ""
    revenue: float = 0.0
    employees: int = 0
    years_in_business: float = 0.0
    prior_claims_count: int = 0
    prior_claims_total: float = 0.0
    tiv: float = 0.0
    requested_premium: float = 0.0
    loss_ratio: float = 0.0
    credit_score: float = 0.0
    dti_ratio: float = 0.0
    ltv_ratio: float = 0.0
    property_age: float = 0.0
    construction_type: str = ""
    occupancy_type: str = ""
    protection_class: str = ""
    roof_type: str = ""
    year_built: int = 0
    square_footage: float = 0.0
    num_stories: int = 0
    sprinkler_system: bool = False
    alarm_system: bool = False
    prior_cancellations: int = 0
    broker_id: str = ""
    carrier: str = ""
    product_line: str = ""
    month_of_binding: int = 0
    quarter: int = 0
    custom_features: dict[str, Any] = Field(default_factory=dict)


class LossPrediction(BaseModel):
    """Loss frequency and severity prediction."""

    expected_frequency: float = Field(description="Predicted claims per year")
    expected_severity: float = Field(description="Predicted average claim amount")
    expected_loss: float = Field(description="Frequency × Severity")
    loss_range_low: float = Field(description="5th percentile loss")
    loss_range_high: float = Field(description="95th percentile loss")
    confidence: float = Field(ge=0, le=1, description="Model confidence")
    top_risk_factors: list[str] = Field(default_factory=list)
    model_version: str = ""


class FraudScore(BaseModel):
    """Fraud anomaly detection result."""

    fraud_probability: float = Field(ge=0, le=1)
    anomaly_score: float = Field(description="Isolation forest anomaly score")
    risk_level: str = Field(description="low / medium / high / critical")
    flagged_patterns: list[str] = Field(default_factory=list)
    similar_claims: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    model_version: str = ""


class PremiumRecommendation(BaseModel):
    """ML-optimized premium recommendation."""

    recommended_premium: float
    base_rate: float
    risk_adjustment: float
    market_adjustment: float
    margin_target: float
    elasticity_impact: float = Field(description="Price elasticity effect on retention")
    competitive_position: str = Field(description="below_market / at_market / above_market")
    retention_probability: float = Field(ge=0, le=1, description="Predicted retention at this price")
    margin_at_price: float = Field(description="Expected margin at recommended price")
    model_version: str = ""


class PortfolioRiskResult(BaseModel):
    """Portfolio-level risk modeling result."""

    total_exposure: float
    expected_loss: float
    var_95: float = Field(description="Value at Risk (95th percentile)")
    var_99: float = Field(description="Value at Risk (99th percentile)")
    tail_var: float = Field(description="Tail VaR (99.5th percentile)")
    cat_contribution: float = Field(description="Catastrophe risk as % of total")
    concentration_index: float = Field(ge=0, le=1, description="HHI concentration")
    diversification_benefit: float = Field(description="Diversification ratio")
    scenarios_tested: int = 0
    model_version: str = ""


class BehavioralScore(BaseModel):
    """Broker/submission behavioral scoring."""

    entity_id: str
    entity_type: str = Field(description="broker / carrier / submission")
    quality_score: float = Field(ge=0, le=100)
    consistency_score: float = Field(ge=0, le=100)
    accuracy_score: float = Field(ge=0, le=100)
    timeliness_score: float = Field(ge=0, le=100)
    overall_grade: str = Field(description="A / B / C / D / F")
    trend: str = Field(description="improving / stable / declining")
    data_completeness: float = Field(ge=0, le=1)
    override_rate: float = Field(ge=0, le=1)
    loss_ratio_history: list[float] = Field(default_factory=list)
    model_version: str = ""


class ChurnPrediction(BaseModel):
    """Policy non-renewal risk prediction."""

    churn_probability: float = Field(ge=0, le=1)
    risk_factors: list[str] = Field(default_factory=list)
    retention_actions: list[str] = Field(default_factory=list)
    lifetime_value: float = Field(description="Predicted LTV if retained")
    churn_cost: float = Field(description="Estimated cost of losing this policy")
    renewal_premium_suggestion: float = 0.0
    model_version: str = ""


class TrainingResult(BaseModel):
    """Result of model training."""

    model_type: ModelType
    model_version: str
    metrics: dict[str, float]
    feature_importance: dict[str, float]
    training_samples: int
    validation_samples: int
    trained_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0


class PredictionRequest(BaseModel):
    """Generic prediction request."""

    model_type: ModelType
    features: FeatureVector
    return_explanation: bool = True


class PredictionResponse(BaseModel):
    """Generic prediction response."""

    model_type: ModelType
    prediction: dict[str, Any]
    explanation: dict[str, Any] = Field(default_factory=dict)
    model_version: str = ""
    latency_ms: float = 0.0
