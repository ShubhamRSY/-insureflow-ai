"""Per-LOB underwriting profiles — training priors, fallback heuristics, and UW perspective."""

from __future__ import annotations

from typing import Any

from insureflow.insurance.commercial_lobs import COMMERCIAL_LINES, get_commercial_line
from insureflow.ml.models import FeatureVector

# Category-level priors shape how each LOB's models learn and fall back.
CATEGORY_PROFILES: dict[str, dict[str, float]] = {
    "property": {
        "loss_severity_mult": 1.35,
        "loss_frequency_mult": 0.85,
        "fraud_prior": 0.06,
        "churn_prior": 0.10,
        "premium_load": 1.05,
        "tiv_scale": 1.4,
    },
    "liability": {
        "loss_severity_mult": 1.15,
        "loss_frequency_mult": 1.20,
        "fraud_prior": 0.09,
        "churn_prior": 0.14,
        "premium_load": 1.12,
        "tiv_scale": 0.6,
    },
    "workforce": {
        "loss_severity_mult": 0.95,
        "loss_frequency_mult": 1.30,
        "fraud_prior": 0.07,
        "churn_prior": 0.11,
        "premium_load": 1.08,
        "tiv_scale": 0.4,
    },
    "auto": {
        "loss_severity_mult": 1.05,
        "loss_frequency_mult": 1.25,
        "fraud_prior": 0.11,
        "churn_prior": 0.16,
        "premium_load": 1.10,
        "tiv_scale": 0.5,
    },
    "financial": {
        "loss_severity_mult": 1.25,
        "loss_frequency_mult": 0.90,
        "fraud_prior": 0.10,
        "churn_prior": 0.12,
        "premium_load": 1.15,
        "tiv_scale": 0.3,
    },
    "specialty": {
        "loss_severity_mult": 1.50,
        "loss_frequency_mult": 0.75,
        "fraud_prior": 0.08,
        "churn_prior": 0.13,
        "premium_load": 1.20,
        "tiv_scale": 1.0,
    },
    "alternative": {
        "loss_severity_mult": 1.40,
        "loss_frequency_mult": 0.80,
        "fraud_prior": 0.05,
        "churn_prior": 0.08,
        "premium_load": 1.18,
        "tiv_scale": 1.2,
    },
    "package": {
        "loss_severity_mult": 1.10,
        "loss_frequency_mult": 1.05,
        "fraud_prior": 0.07,
        "churn_prior": 0.12,
        "premium_load": 1.06,
        "tiv_scale": 1.0,
    },
}

DEFAULT_PROFILE = CATEGORY_PROFILES["package"]

INSURANCE_LOB_MODEL_TYPES = (
    "loss_prediction",
    "fraud_detection",
    "premium_optimizer",
    "churn_prediction",
)


def _line_by_insurance_line(insurance_line: str) -> dict[str, Any] | None:
    raw = (insurance_line or "").strip().lower()
    if not raw:
        return None
    for line in COMMERCIAL_LINES:
        if line["insurance_line"].lower() == raw:
            return line
        if line["checklist_lob"].lower() == raw:
            return line
        if line["id"].lower() == raw:
            return line
    return get_commercial_line(raw)


def category_profile(category_id: str) -> dict[str, float]:
    return dict(CATEGORY_PROFILES.get(category_id, DEFAULT_PROFILE))


def lob_profile(insurance_line: str) -> dict[str, Any]:
    """Resolved LOB metadata + category priors for ML and UW."""
    line = _line_by_insurance_line(insurance_line)
    if not line:
        return {"insurance_line": insurance_line, "category_id": "package", **DEFAULT_PROFILE}
    cat = str(line.get("category_id") or "package")
    prof = category_profile(cat)
    return {
        "insurance_line": line["insurance_line"],
        "category_id": cat,
        "name": line["name"],
        "uw_focus": line.get("uw_focus") or "",
        "checklist_lob": line.get("checklist_lob") or "",
        **prof,
    }


def lob_training_seed(insurance_line: str) -> int:
    """Stable per-LOB RNG seed."""
    return abs(hash(insurance_line)) % (2**31 - 1)


def lob_risk_factors(insurance_line: str, fv: FeatureVector) -> list[str]:
    """Line-specific risk factors for ML fallbacks and agent context."""
    prof = lob_profile(insurance_line)
    factors: list[str] = []
    uw = prof.get("uw_focus") or ""
    if uw:
        factors.append(f"LOB focus ({prof.get('name', insurance_line)}): {uw[:180]}")

    cat = prof.get("category_id", "")
    if cat == "property" and fv.tiv > 5e7:
        factors.append(f"Large property TIV ${fv.tiv / 1e6:.0f}M — verify COPE and SOV adequacy")
    if cat == "liability" and fv.prior_claims_count >= 2:
        factors.append(f"{fv.prior_claims_count} prior liability claims — review loss development")
    if cat == "workforce" and fv.employees > 500:
        factors.append(f"Large payroll exposure ({fv.employees} employees) — review experience mod")
    if cat == "auto" and fv.prior_claims_count >= 3:
        factors.append("Fleet loss frequency elevated — review MVR and fleet safety program")
    if cat == "financial" and fv.loss_ratio > 0.8:
        factors.append(f"Credit/financial line loss ratio {fv.loss_ratio:.1%} — review counterparty quality")
    if fv.loss_ratio > 1.0:
        factors.append(f"Historical loss ratio {fv.loss_ratio:.1%} exceeds 100%")
    if fv.prior_claims_count > 3:
        factors.append(f"{fv.prior_claims_count} prior claims in {fv.years_in_business:.0f} years")
    if fv.credit_score < 600:
        factors.append(f"Low credit score: {fv.credit_score:.0f}")
    return factors[:8]


def lob_loss_fallback(insurance_line: str, fv: FeatureVector) -> tuple[float, float, float]:
    """LOB-adjusted (frequency, severity, expected_loss) for deterministic fallback."""
    prof = lob_profile(insurance_line)
    freq_mult = float(prof.get("loss_frequency_mult", 1.0))
    sev_mult = float(prof.get("loss_severity_mult", 1.0))
    tiv_scale = float(prof.get("tiv_scale", 1.0))

    base_frequency = (0.05 + (fv.prior_claims_count / max(fv.years_in_business, 1)) * 0.1) * freq_mult
    effective_tiv = fv.tiv * tiv_scale if fv.tiv > 0 else 1_000_000.0 * tiv_scale
    base_severity = effective_tiv * 0.005 * fv.loss_ratio if fv.loss_ratio > 0 else effective_tiv * 0.01
    base_severity *= sev_mult
    expected_loss = base_frequency * base_severity
    return base_frequency, base_severity, expected_loss
