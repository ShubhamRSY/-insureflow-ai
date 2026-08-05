"""Feature engineering for ML models — transforms FeatureVector into model-ready arrays."""

from __future__ import annotations

import numpy as np

from insureflow.ml.models import FeatureVector

__all__ = ["FeatureVector", "extract_features", "extract_lending_features", "extract_mortgage_features", "generate_synthetic_dataset"]
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

MORTGAGE_FEATURE_NAMES = [
    "credit_score",
    "dti_ratio",
    "ltv_ratio",
    "loan_amount",
    "annual_income",
    "reserves",
    "employment_years",
    "self_employment_income",
    "utilization_rate",
    "derogatory_marks",
    "property_age",
    "bankruptcies",
    "foreclosures",
    "prior_cancellations",
    "loan_to_income",
    "reserves_to_loan",
    "utilization_norm",
    "income_stability",
]

LENDING_FEATURE_NAMES = [
    "loan_segment_business",
    "credit_score",
    "dti_ratio",
    "annual_income",
    "loan_amount",
    "years_in_business",
    "employment_years",
    "dscr",
    "current_ratio",
    "leverage_ratio",
    "profit_margin",
    "debt_service",
    "ebitda",
    "total_assets",
    "total_liabilities",
    "bankruptcies",
    "foreclosures",
    "loan_to_income",
]

MODEL_FEATURE_NAMES: dict[str, list[str]] = {
    "loss_prediction": DEFAULT_FEATURE_NAMES,
    "fraud_detection": DEFAULT_FEATURE_NAMES,
    "premium_optimizer": DEFAULT_FEATURE_NAMES,
    "churn_prediction": DEFAULT_FEATURE_NAMES,
    "mortgage_default_risk": MORTGAGE_FEATURE_NAMES,
    "lending_default_risk": LENDING_FEATURE_NAMES,
}


def get_model_feature_names(model_type: str) -> list[str]:
    """Return the feature column order for a given model type."""
    return MODEL_FEATURE_NAMES.get(model_type, DEFAULT_FEATURE_NAMES)


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


def extract_mortgage_features(fv: FeatureVector) -> np.ndarray:
    """Transform a FeatureVector into the mortgage default-risk feature array."""
    annual_income = fv.revenue
    loan_to_income = fv.loan_amount / max(annual_income, 1)
    reserves_to_loan = fv.reserves / max(fv.loan_amount, 1)
    utilization_norm = min(max(fv.utilization_rate, 0), 100) / 100.0
    income_stability = min(max(fv.employment_years, 0), 10) / 10.0

    return np.array(
        [
            fv.credit_score,
            fv.dti_ratio,
            fv.ltv_ratio,
            fv.loan_amount,
            annual_income,
            fv.reserves,
            fv.employment_years,
            fv.self_employment_income,
            fv.utilization_rate,
            fv.derogatory_marks,
            fv.property_age,
            fv.bankruptcies,
            fv.foreclosures,
            fv.prior_cancellations,
            loan_to_income,
            reserves_to_loan,
            utilization_norm,
            income_stability,
        ],
        dtype=np.float64,
    )


def get_mortgage_feature_names() -> list[str]:
    """Return ordered feature names matching extract_mortgage_features output."""
    return MORTGAGE_FEATURE_NAMES


def extract_lending_features(fv: FeatureVector) -> np.ndarray:
    """Transform a FeatureVector into the lending default-risk feature array."""
    annual_income = fv.revenue
    loan_to_income = fv.loan_amount / max(annual_income, 1)
    segment_business = 1.0 if (fv.loan_segment or "").lower() in ("business", "b2b") else 0.0

    return np.array(
        [
            segment_business,
            fv.credit_score,
            fv.dti_ratio,
            annual_income,
            fv.loan_amount,
            fv.years_in_business,
            fv.employment_years,
            fv.dscr,
            fv.current_ratio,
            fv.leverage_ratio,
            fv.profit_margin,
            fv.debt_service,
            fv.ebitda,
            fv.total_assets,
            fv.total_liabilities,
            fv.bankruptcies,
            fv.foreclosures,
            loan_to_income,
        ],
        dtype=np.float64,
    )


def get_lending_feature_names() -> list[str]:
    """Return ordered feature names matching extract_lending_features output."""
    return LENDING_FEATURE_NAMES


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

    revenue = X[:, 0]
    employees = X[:, 1]
    years = X[:, 2]
    claims_count = X[:, 3]
    tiv = X[:, 5]
    premium = X[:, 6]
    loss_ratio = X[:, 7]
    credit_score = X[:, 8]
    cancellations = X[:, 21]

    revenue_per_emp = revenue / np.maximum(employees, 1)
    claims_per_yr = claims_count / np.maximum(years, 1)
    tiv_to_rev = tiv / np.maximum(revenue, 1)
    prem_to_tiv = premium / np.maximum(tiv, 1)
    risk_score = (
        loss_ratio * 0.3 + (1 - np.clip(credit_score / 850, 0, 1)) * 0.2 + np.clip(claims_count / 10, 0, 1) * 0.2 + np.clip(cancellations / 5, 0, 1) * 0.15 + (1 - np.clip(years / 30, 0, 1)) * 0.15
    )

    X = np.column_stack([X, revenue_per_emp, claims_per_yr, tiv_to_rev, prem_to_tiv, risk_score])

    if model_type == "loss_prediction":
        y = _generate_loss_target(X, rng)
    elif model_type == "fraud_detection":
        y = _generate_fraud_target(X, rng)
    elif model_type == "premium_optimizer":
        y = _generate_premium_target(X, rng)
    elif model_type == "churn_prediction":
        y = _generate_churn_target(X, rng)
    elif model_type == "mortgage_default_risk":
        return _generate_mortgage_synthetic_dataset(n_samples, seed)
    elif model_type == "lending_default_risk":
        return _generate_lending_synthetic_dataset(n_samples, seed)
    else:
        y = rng.uniform(0, 1, n_samples)

    return X.astype(np.float64), y.astype(np.float64)


def _generate_mortgage_synthetic_dataset(n_samples: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic mortgage default training data (feature-order == MORTGAGE_FEATURE_NAMES)."""
    rng = np.random.RandomState(seed)

    credit_score = rng.normal(720, 80, n_samples).clip(500, 850)
    dti = rng.uniform(20, 55, n_samples)
    ltv = rng.uniform(60, 98, n_samples)
    annual_income = rng.uniform(4e4, 5e6, n_samples)
    loan_amount = annual_income * rng.uniform(1.5, 6.0, n_samples)
    reserves = rng.uniform(0, 2e5, n_samples)
    employment_years = rng.uniform(0, 40, n_samples)
    self_employment_income = np.where(rng.random(n_samples) < 0.2, annual_income * rng.uniform(0.1, 1.0, n_samples), 0.0)
    utilization = rng.uniform(0, 100, n_samples)
    derogatory_marks = rng.poisson(0.6, n_samples)
    property_age = rng.uniform(0, 100, n_samples)
    bankruptcies = rng.binomial(1, 0.03, n_samples)
    foreclosures = rng.binomial(1, 0.02, n_samples)
    prior_cancellations = rng.poisson(0.3, n_samples)

    loan_to_income = loan_amount / np.maximum(annual_income, 1)
    reserves_to_loan = reserves / np.maximum(loan_amount, 1)
    utilization_norm = utilization / 100.0
    income_stability = np.clip(employment_years, 0, 10) / 10.0

    X = np.column_stack(
        [
            credit_score,
            dti,
            ltv,
            loan_amount,
            annual_income,
            reserves,
            employment_years,
            self_employment_income,
            utilization,
            derogatory_marks,
            property_age,
            bankruptcies,
            foreclosures,
            prior_cancellations,
            loan_to_income,
            reserves_to_loan,
            utilization_norm,
            income_stability,
        ]
    )

    default_prob = (
        0.02
        + np.where(credit_score < 600, 0.45, np.where(credit_score < 640, 0.25, np.where(credit_score < 680, 0.10, 0.0)))
        + np.where(dti > 45, 0.20, np.where(dti > 40, 0.08, 0.0))
        + np.where(ltv > 95, 0.18, np.where(ltv > 85, 0.08, 0.0))
        + np.where(reserves < 5000, 0.12, 0.0)
        + 0.15 * bankruptcies
        + 0.12 * foreclosures
        + 0.03 * np.minimum(derogatory_marks, 4)
        + rng.normal(0, 0.02, n_samples)
    )
    default_prob = np.clip(default_prob, 0.01, 0.95)
    y = (rng.random(n_samples) < default_prob).astype(float)

    return X.astype(np.float64), y.astype(np.float64)


def _generate_lending_synthetic_dataset(n_samples: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic lending default training data (feature-order == LENDING_FEATURE_NAMES)."""
    rng = np.random.RandomState(seed)
    n_business = int(n_samples * 0.6)

    seg = np.zeros(n_samples)
    seg[:n_business] = 1.0

    credit_score = rng.normal(700, 85, n_samples).clip(480, 850)
    dti = rng.uniform(20, 60, n_samples)
    annual_income = rng.uniform(3e4, 5e6, n_samples)
    loan_amount = annual_income * rng.uniform(1.0, 5.0, n_samples)
    years_in_business = np.where(seg == 1, rng.uniform(0.5, 30, n_samples), 0.0)
    employment_years = np.where(seg == 1, 0.0, rng.uniform(0, 40, n_samples))
    dscr = np.where(seg == 1, rng.uniform(0.8, 2.2, n_samples), 0.0)
    current_ratio = np.where(seg == 1, rng.uniform(0.5, 3.0, n_samples), 0.0)
    leverage_ratio = np.where(seg == 1, rng.uniform(0.5, 7.0, n_samples), 0.0)
    profit_margin = np.where(seg == 1, rng.uniform(-5, 30, n_samples), 0.0)
    debt_service = np.where(seg == 1, rng.uniform(5e3, 5e6, n_samples), 0.0)
    ebitda = np.where(seg == 1, rng.uniform(1e4, 5e6, n_samples), 0.0)
    total_assets = np.where(seg == 1, rng.uniform(1e5, 5e7, n_samples), 0.0)
    total_liabilities = np.where(seg == 1, rng.uniform(0, 4e7, n_samples), 0.0)
    bankruptcies = rng.binomial(1, 0.04, n_samples)
    foreclosures = rng.binomial(1, 0.03, n_samples)
    loan_to_income = loan_amount / np.maximum(annual_income, 1)

    X = np.column_stack(
        [
            seg,
            credit_score,
            dti,
            annual_income,
            loan_amount,
            years_in_business,
            employment_years,
            dscr,
            current_ratio,
            leverage_ratio,
            profit_margin,
            debt_service,
            ebitda,
            total_assets,
            total_liabilities,
            bankruptcies,
            foreclosures,
            loan_to_income,
        ]
    )

    default_prob = (
        0.03
        + np.where(credit_score < 600, 0.42, np.where(credit_score < 640, 0.22, np.where(credit_score < 680, 0.08, 0.0)))
        + np.where(dti > 45, 0.15, np.where(dti > 40, 0.06, 0.0))
        + np.where(seg == 1, np.where(dscr < 1.1, 0.20, np.where(dscr < 1.25, 0.08, 0.0)), 0.0)
        + np.where(seg == 1, np.where(leverage_ratio > 4.5, 0.12, 0.0), 0.0)
        + np.where(seg == 1, np.where(current_ratio < 0.9, 0.08, 0.0), 0.0)
        + np.where(seg == 1, np.where(years_in_business < 2, 0.08, 0.0), 0.0)
        + 0.12 * bankruptcies
        + 0.10 * foreclosures
        + rng.normal(0, 0.02, n_samples)
    )
    default_prob = np.clip(default_prob, 0.01, 0.95)
    y = (rng.random(n_samples) < default_prob).astype(float)

    return X.astype(np.float64), y.astype(np.float64)


def _generate_loss_target(X: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Generate synthetic loss amounts based on features."""
    loss_ratio = X[:, 7]
    tiv = X[:, 5]
    claims_count = X[:, 3]
    base_loss = tiv * loss_ratio * 0.01
    noise = rng.normal(0, base_loss * 0.2)
    return np.maximum(base_loss + noise + claims_count * 5000, 0)  # type: ignore[no-any-return]


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
    loss_ratio = X[:, 7]
    credit = X[:, 8]
    claims = X[:, 3]
    cancellations = X[:, 21]
    years = X[:, 2]
    risk_score = loss_ratio * 0.3 + (1 - np.clip(credit / 850, 0, 1)) * 0.2 + np.clip(claims / 10, 0, 1) * 0.2 + np.clip(cancellations / 5, 0, 1) * 0.15 + (1 - np.clip(years / 30, 0, 1)) * 0.15
    base = tiv * 0.005
    risk_adj = base * risk_score
    margin = rng.uniform(0.1, 0.3, len(X))
    return base + risk_adj + margin * base


def _generate_churn_target(X: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
    """Generate churn labels (0=renew, 1=churn) based on risk factors."""
    loss_ratio = X[:, 7]
    credit = X[:, 8]
    years = X[:, 2]
    churn_base: np.ndarray = np.full(len(X), 0.1)
    churn_base = churn_base + np.where(loss_ratio > 1.2, 0.3, 0)
    churn_base = churn_base + np.where(credit < 600, 0.15, 0)
    churn_base = churn_base + np.where(years < 2, 0.2, 0)
    churn_base = churn_base + rng.normal(0, 0.05, len(X))
    churn_prob = np.clip(churn_base, 0, 1)
    return (rng.random(len(X)) < churn_prob).astype(float)  # type: ignore[no-any-return]
