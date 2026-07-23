"""Feature engineering for ML models — transforms FeatureVector into model-ready arrays."""

from __future__ import annotations

import numpy as np

from insureflow.ml.models import FeatureVector

# Categorical mappings for encoding
CONSTRUCTION_MAP = {
    "frame": 0,
    "masonry": 1,
    "steel_frame": 2,
    "reinforced_concrete": 3,
    "fire_resistive": 4,
    "noncombustible": 5,
    "modular": 6,
    "manufactured": 7,
    "": 8,
}

OCCUPANCY_MAP = {
    "office": 0,
    "retail": 1,
    "manufacturing": 2,
    "warehouse": 3,
    "residential": 4,
    "institutional": 5,
    "mixed_use": 6,
    "agricultural": 7,
    "": 8,
}

PROTECTION_MAP = {"1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "": 6}

ROOF_MAP = {"flat": 0, "gable": 1, "hip": 2, "mansard": 3, "shed": 4, "": 5}

PRODUCT_LINES = {
    "commercial_property": 0,
    "general_liability": 1,
    "workers_comp": 2,
    "commercial_auto": 3,
    "professional_liability": 4,
    "umbrella": 5,
    "residential": 6,
    "": 7,
}

DEFAULT_FEATURE_NAMES = [
    "revenue",
    "employees",
    "years_in_business",
    "prior_claims_count",
    "prior_claims_total",
    "tiv",
    "requested_premium",
    "loss_ratio",
    "credit_score",
    "dti_ratio",
    "ltv_ratio",
    "property_age",
    "construction_type",
    "occupancy_type",
    "protection_class",
    "roof_type",
    "year_built",
    "square_footage",
    "num_stories",
    "sprinkler_system",
    "alarm_system",
    "prior_cancellations",
    "month_of_binding",
    "quarter",
    "revenue_per_employee",
    "claims_per_year",
    "tiv_to_revenue",
    "premium_to_tiv",
    "risk_score_raw",
]


def encode_categorical(value: str, mapping: dict[str, int]) -> int:
    """Encode a categorical string to an integer."""
    return mapping.get(value.lower().strip(), mapping.get("", 99))


def extract_features(fv: FeatureVector) -> np.ndarray:
    """Transform a FeatureVector into a numeric feature array."""
    revenue_per_employee = fv.revenue / max(fv.employees, 1)
    claims_per_year = fv.prior_claims_count / max(fv.years_in_business, 1)
    tiv_to_revenue = fv.tiv / max(fv.revenue, 1)
    premium_to_tiv = fv.requested_premium / max(fv.tiv, 1)
    risk_score_raw = (
        fv.loss_ratio * 0.3
        + (1 - min(fv.credit_score / 850, 1.0)) * 0.2
        + min(fv.prior_claims_count / 10, 1.0) * 0.2
        + min(fv.prior_cancellations / 5, 1.0) * 0.15
        + (1 - min(fv.years_in_business / 30, 1.0)) * 0.15
    )

    features = [
        fv.revenue,
        fv.employees,
        fv.years_in_business,
        fv.prior_claims_count,
        fv.prior_claims_total,
        fv.tiv,
        fv.requested_premium,
        fv.loss_ratio,
        fv.credit_score,
        fv.dti_ratio,
        fv.ltv_ratio,
        fv.property_age,
        encode_categorical(fv.construction_type, CONSTRUCTION_MAP),
        encode_categorical(fv.occupancy_type, OCCUPANCY_MAP),
        encode_categorical(fv.protection_class, PROTECTION_MAP),
        encode_categorical(fv.roof_type, ROOF_MAP),
        fv.year_built,
        fv.square_footage,
        fv.num_stories,
        int(fv.sprinkler_system),
        int(fv.alarm_system),
        fv.prior_cancellations,
        fv.month_of_binding,
        fv.quarter,
        revenue_per_employee,
        claims_per_year,
        tiv_to_revenue,
        premium_to_tiv,
        risk_score_raw,
    ]
    return np.array(features, dtype=np.float64)


def get_feature_names() -> list[str]:
    """Return ordered feature names matching extract_features output."""
    return DEFAULT_FEATURE_NAMES


def generate_synthetic_dataset(
    n_samples: int = 1000,
    model_type: str = "loss_prediction",
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic training data for bootstrapping models.

    Returns (X, y) arrays suitable for model training.
    """
    rng = np.random.RandomState(seed)

    X = np.column_stack(
        [
            rng.uniform(1e5, 1e8, n_samples),  # revenue
            rng.randint(5, 500, n_samples),  # employees
            rng.uniform(0.5, 50, n_samples),  # years_in_business
            rng.poisson(2, n_samples),  # prior_claims_count
            rng.exponential(50000, n_samples),  # prior_claims_total
            rng.uniform(1e6, 5e8, n_samples),  # tiv
            rng.uniform(5000, 500000, n_samples),  # requested_premium
            rng.uniform(0.1, 2.0, n_samples),  # loss_ratio
            rng.normal(720, 80, n_samples).clip(300, 850),  # credit_score
            rng.uniform(0.15, 0.65, n_samples),  # dti_ratio
            rng.uniform(0.5, 0.95, n_samples),  # ltv_ratio
            rng.uniform(0, 100, n_samples),  # property_age
            rng.randint(0, 8, n_samples),  # construction_type
            rng.randint(0, 8, n_samples),  # occupancy_type
            rng.randint(0, 6, n_samples),  # protection_class
            rng.randint(0, 5, n_samples),  # roof_type
            rng.randint(1950, 2024, n_samples),  # year_built
            rng.uniform(1000, 100000, n_samples),  # square_footage
            rng.randint(1, 10, n_samples),  # num_stories
            rng.binomial(1, 0.4, n_samples),  # sprinkler_system
            rng.binomial(1, 0.6, n_samples),  # alarm_system
            rng.poisson(0.5, n_samples),  # prior_cancellations
            rng.randint(1, 13, n_samples),  # month_of_binding
            rng.randint(1, 5, n_samples),  # quarter
        ]
    )

    if model_type == "loss_prediction":
        y = _generate_loss_target(X, rng)
    elif model_type == "fraud_detection":
        y = _generate_fraud_target(X, rng)
    elif model_type == "premium_optimizer":
        y = _generate_premium_target(X, rng)
    elif model_type == "churn_prediction":
        y = _generate_churn_target(X, rng)
    else:
        y = rng.uniform(0, 1, n_samples)

    return X.astype(np.float64), y.astype(np.float64)


def _generate_loss_target(X: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Generate synthetic loss amounts based on features."""
    loss_ratio = X[:, 7]
    tiv = X[:, 5]
    claims_count = X[:, 3]
    base_loss = tiv * loss_ratio * 0.01
    noise = rng.normal(0, base_loss * 0.2)
    return np.maximum(base_loss + noise + claims_count * 5000, 0)


def _generate_fraud_target(X: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Generate synthetic fraud labels (0=legit, 1=fraud)."""
    n = len(X)
    fraud_rate = 0.05
    y = np.zeros(n)
    high_loss = X[:, 7] > 1.5
    many_claims = X[:, 3] > 4
    low_credit = X[:, 8] < 550
    suspicious = high_loss | many_claims | low_credit
    fraud_candidates = np.where(suspicious)[0]
    n_fraud = min(int(n * fraud_rate * 3), len(fraud_candidates))
    if n_fraud > 0:
        fraud_idx = rng.choice(fraud_candidates, n_fraud, replace=False)
        y[fraud_idx] = 1
    extra = rng.choice(n, max(0, int(n * fraud_rate) - n_fraud), replace=False)
    y[extra] = 1
    return y


def _generate_premium_target(X: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Generate optimal premium targets."""
    tiv = X[:, 5]
    risk_score = X[:, 28]
    base = tiv * 0.005
    risk_adj = base * risk_score
    margin = rng.uniform(0.1, 0.3, len(X))
    return base + risk_adj + margin * base


def _generate_churn_target(X: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Generate churn probability targets."""
    loss_ratio = X[:, 7]
    credit = X[:, 8]
    years = X[:, 2]
    churn_base = 0.1
    churn_base += np.where(loss_ratio > 1.2, 0.3, 0)
    churn_base += np.where(credit < 600, 0.15, 0)
    churn_base += np.where(years < 2, 0.2, 0)
    churn_base += rng.normal(0, 0.05, len(X))
    return np.clip(churn_base, 0, 1)
