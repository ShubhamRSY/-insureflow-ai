"""Permanent-life cash-value accumulation and surrender-value projection.

Whole and universal life build cash value inside the policy; term life is pure
protection with none. This projects the account/cash value year over year so the
suitability review (and any net-cost illustration) has real numbers instead of a
catalog-only stub.
"""

from __future__ import annotations

from typing import Any

from insureflow.models.policy import LifeCashValue
from insureflow.underwriting.life_product import classify_life_family

# Up-front acquisition/expense load on each premium dollar (universal-life style).
_EXPENSE_LOAD = 0.10
# Level annual renewable term cost per $1,000 (used to isolate the savings element).
_TERM_COST_PER_1000 = 4.0
_GUARANTEED_CREDIT = 0.02
_ILLUSTRATED_CREDIT = 0.045

# Surrender-charge schedule: % of cash value forfeited by policy year.
_SURRENDER_CHARGE_PCT = {1: 0.35, 2: 0.30, 3: 0.25, 4: 0.20, 5: 0.15, 6: 0.10, 7: 0.05, 8: 0.0}

_SAVINGS_PRODUCTS = {"whole_life", "universal", "variable_universal"}


def project_cash_value(
    *,
    face_amount: float,
    annual_premium: float,
    product_family: str = "whole_life",
    years: int = 20,
    illustrated_credit_rate: float | None = None,
    guaranteed_only: bool = False,
) -> LifeCashValue:
    """Project the cash value and surrender value of a permanent policy."""
    face = max(float(face_amount or 0.0), 0.0)
    premium = max(float(annual_premium or 0.0), 0.0)
    years = max(min(int(years or 20), 50), 1)

    schedule: list[dict[str, Any]] = []
    account = 0.0
    for year in range(1, years + 1):
        # Net premium after expense load, minus the pure term-cost of protection
        # on the outstanding face — the remainder is the savings element.
        term_cost = face / 1000.0 * _TERM_COST_PER_1000
        net = max(premium * (1.0 - _EXPENSE_LOAD) - term_cost, 0.0)
        if guaranteed_only:
            credit = _GUARANTEED_CREDIT
        else:
            credit = illustrated_credit_rate if illustrated_credit_rate is not None else _ILLUSTRATED_CREDIT
        account = account * (1.0 + credit) + net
        charge = float(_SURRENDER_CHARGE_PCT.get(year, 0.0))
        surrender = account * (1.0 - charge)
        schedule.append(
            {
                "year": year,
                "premium_paid": round(premium * year, 2),
                "cash_value": round(account, 2),
                "surrender_value": round(surrender, 2),
                "surrender_charge_pct": charge,
            }
        )

    return LifeCashValue(
        product_family=product_family,
        face_amount=face,
        annual_premium=premium,
        years_projected=years,
        cash_value_schedule=schedule,
        guaranteed=guaranteed_only,
        notes=(
            f"{product_family} cash-value projection at {'guaranteed' if guaranteed_only else 'illustrated'} crediting" + (" — illustrative, not a policy illustration" if not guaranteed_only else "")
        ),
    )


def cash_value_for_bundle(
    bundle: Any,
    *,
    face_amount: float | None = None,
    annual_premium: float | None = None,
    product_id: str | None = None,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
) -> LifeCashValue | None:
    """Project cash value from a submission's life factors when the product has
    a savings element; return None for term / annuity / unknown products."""
    family = classify_life_family(product_id, coverage_id, coverage_name)
    if family not in _SAVINGS_PRODUCTS:
        return None

    from insureflow.underwriting.personal_lines import extract_life_factors

    factors = extract_life_factors(bundle)
    face = face_amount if face_amount is not None else factors.face_amount
    if not face:
        return None
    # Representative annual level premium for a savings product (~2.5% of face);
    # callers may pass an explicit annual_premium from the application instead.
    premium = annual_premium if annual_premium is not None else face * 0.025
    return project_cash_value(
        face_amount=face,
        annual_premium=premium,
        product_family=family,
    )
