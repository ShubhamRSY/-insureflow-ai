"""Policy architecture effects — limits, SIR, coinsurance penalty, elimination.

Complements the structured fields on :class:`CoverageDetail` with the actuarial
mechanics behind them: the property coinsurance penalty clause, the SIR credit,
per-occurrence vs aggregate limit adequacy, and lifetime/annual maximum
compliance. Each helper is additive — it never invents premium where inputs are
missing.
"""

from __future__ import annotations

from typing import Any

from insureflow.models.submissions import CoverageDetail


def coinsurance_penalty(
    *,
    insured_limit: float,
    coinsurance_pct: float,
    property_value: float,
) -> dict[str, Any]:
    """Property coinsurance clause: insure to at least ``coinsurance_pct`` of value.

    When the insured carries less than the required amount, the carrier pays
    only ``insured/required`` of each loss (the penalty).
    """
    raw_pct = float(coinsurance_pct or 0.0)
    # Accept either a decimal (0.80) or a percentage number (80).
    if 0 < raw_pct <= 1.0:
        raw_pct *= 100.0
    required = raw_pct / 100.0 * max(float(property_value or 0.0), 0.0)
    limit = max(float(insured_limit or 0.0), 0.0)
    if required <= 0:
        return {"required_coverage": required, "compliance_ratio": None, "penalty_applies": False, "penalty_pct": 0.0, "detail": "No coinsurance clause applicable"}
    ratio = min(limit / required, 1.0)
    penalty_pct = 1.0 - ratio
    return {
        "required_coverage": round(required, 2),
        "compliance_ratio": round(ratio, 4),
        "penalty_applies": ratio < 1.0,
        "penalty_pct": round(penalty_pct, 4),
        "detail": (
            "Coinsurance satisfied" if ratio >= 1.0
            else f"Under-insured: carries {ratio:.1%} of the required {required:,.0f} — {penalty_pct:.1%} of each loss would be uninsured"
        ),
    }


def sir_rating_credit(*, sir_amount: float, base_premium: float) -> dict[str, Any]:
    """Self-insured retention discount: the insured funds the first dollars (and
    often defense costs) before the insurer's duty to indemnify triggers."""
    sir = max(float(sir_amount or 0.0), 0.0)
    premium = max(float(base_premium or 0.0), 0.0)
    if sir <= 0 or premium <= 0:
        return {"credit_pct": 0.0, "credit_amount": 0.0, "detail": "No SIR — no credit"}
    # Credit scales with SIR relative to a multiple of premium, capped at 25%.
    credit_pct = min(sir / (premium * 10.0), 0.25)
    return {
        "credit_pct": round(credit_pct, 4),
        "credit_amount": round(premium * credit_pct, 2),
        "detail": f"SIR {sir:,.0f} carries a {credit_pct:.1%} premium credit ({premium * credit_pct:,.0f})",
    }


def aggregate_utilization(
    *,
    aggregate_limit: float,
    aggregate_used: float = 0.0,
) -> dict[str, Any]:
    """Aggregate-limit exhaustion tracking across the policy cycle."""
    limit = max(float(aggregate_limit or 0.0), 0.0)
    used = max(float(aggregate_used or 0.0), 0.0)
    if limit <= 0:
        return {"utilization_pct": None, "remaining": None, "exhausted": False, "detail": "No aggregate limit declared"}
    utilization = used / limit
    return {
        "utilization_pct": round(utilization, 4),
        "remaining": round(limit - used, 2),
        "exhausted": used >= limit,
        "detail": (
            "Aggregate limit exhausted — coverage suspended"
            if used >= limit
            else f"{utilization:.1%} of aggregate limit consumed ({limit - used:,.0f} remaining)"
        ),
    }


def per_occurrence_vs_aggregate(*, per_occurrence_limit: float, aggregate_limit: float) -> dict[str, Any]:
    """Sanity check that the aggregate cap is at least the per-occurrence cap."""
    per = max(float(per_occurrence_limit or 0.0), 0.0)
    agg = max(float(aggregate_limit or 0.0), 0.0)
    if per > 0 and agg > 0 and agg < per:
        return {
            "valid": False,
            "detail": f"Aggregate limit {agg:,.0f} is below the per-occurrence limit {per:,.0f} — invalid policy architecture",
        }
    return {
        "valid": True,
        "detail": f"Per-occurrence {per:,.0f} vs aggregate {agg:,.0f}" if per and agg else "Per-occurrence or aggregate limit not declared",
    }


def architecture_assessment(coverage: CoverageDetail | dict[str, Any]) -> dict[str, Any]:
    """Summarize the structured architecture of one coverage and flag gaps."""
    if isinstance(coverage, dict):
        coverage = CoverageDetail(**coverage)
    flags: list[str] = []
    if coverage.per_occurrence_limit is None and "occurrence" not in coverage.coverage_type.lower():
        if coverage.aggregate_limit is None and coverage.lifetime_maximum is None and coverage.annual_maximum is None:
            flags.append(f"{coverage.coverage_type}: no per-occurrence / aggregate / maximum limit declared")
    if coverage.self_insured_retention is not None and coverage.self_insured_retention > coverage.deductible:
        flags.append(f"{coverage.coverage_type}: SIR ({coverage.self_insured_retention:,.0f}) above the deductible — confirm defense-cost funding")
    if coverage.coinsurance_pct is not None and coverage.coinsurance_pct not in (80, 90, 100):
        flags.append(f"{coverage.coverage_type}: unusual coinsurance clause {coverage.coinsurance_pct}% — verify")
    arch = {
        "per_occurrence_limit": coverage.per_occurrence_limit,
        "aggregate_limit": coverage.aggregate_limit,
        "lifetime_maximum": coverage.lifetime_maximum,
        "annual_maximum": coverage.annual_maximum,
        "self_insured_retention": coverage.self_insured_retention,
        "coinsurance_pct": coverage.coinsurance_pct,
        "copayment": coverage.copayment,
        "elimination_period_days": coverage.elimination_period_days,
        "waiting_period_days": coverage.waiting_period_days,
        "valuation_basis": coverage.valuation_basis,
        "flags": flags,
    }
    if coverage.per_occurrence_limit:
        arch["per_occurrence_vs_aggregate"] = per_occurrence_vs_aggregate(
            per_occurrence_limit=coverage.per_occurrence_limit,
            aggregate_limit=coverage.aggregate_limit or 0.0,
        )
    return arch
