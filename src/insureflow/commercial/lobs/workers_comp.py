"""Workers' Compensation — dedicated logic path.

Reuses the existing NCCI class-code/e-mod pricing engine
(``insureflow.rating.commercial_actuarial.rate_workers_comp_ncci``) rather
than re-deriving it, and adds two real things that engine never applied:

1. State law: exclusive state-fund states where a private carrier cannot
   write coverage at all, and Texas non-subscription.
2. The real NCCI premium-discount mechanism — larger accounts carry a
   lower per-dollar expense load, so standard premium is discounted in
   LAYERS (each tier's rate applies only to the premium within that
   layer, never the whole premium at the top tier's rate — a common
   implementation bug this deliberately avoids). Tier boundaries/rates
   below are illustrative (the real table is state-filed) but the layered
   mechanism is the actual NCCI methodology.
"""

from __future__ import annotations

from typing import Any

from insureflow.commercial.lobs.base import CommercialProductContext, LobOutcome, finish_quote, merge_state_rules
from insureflow.commercial.lobs.state_law import wc_state_row
from insureflow.rating.models import QuoteResult, RateComponent

PRODUCT_ID = "workers_comp"
LOGIC_PATH = "insureflow.commercial.lobs.workers_comp"
PRODUCT_LABEL = "Workers' Compensation"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "monopolistic_fund": False,
    "non_subscription_permitted": False,
    "waiting_period_days": 7,
}

STATE_RULES: dict[str, dict[str, Any]] = {}

# Illustrative NCCI-style layered premium discount — (layer_ceiling, discount_pct
# applied to the premium WITHIN that layer only). Real table is state-filed;
# verify before production. Layers must be applied marginally, not as a single
# top-tier rate over the whole premium.
PREMIUM_DISCOUNT_LAYERS: list[tuple[float, float]] = [
    (10_000.0, 0.0),
    (100_000.0, 8.0),
    (float("inf"), 15.0),
]


def ncci_premium_discount(standard_premium: float) -> tuple[float, float]:
    """Layered/marginal premium discount. Returns (discounted_premium, effective_discount_pct)."""
    if standard_premium <= 0:
        return standard_premium, 0.0
    remaining = standard_premium
    floor = 0.0
    discounted = 0.0
    for ceiling, discount_pct in PREMIUM_DISCOUNT_LAYERS:
        layer_width = max(min(standard_premium, ceiling) - floor, 0.0)
        if layer_width <= 0:
            floor = ceiling
            continue
        discounted += layer_width * (1 - discount_pct / 100.0)
        remaining -= layer_width
        floor = ceiling
        if remaining <= 0:
            break
    effective_pct = (1 - discounted / standard_premium) * 100.0
    return discounted, effective_pct


def underwrite_workers_comp(ctx: CommercialProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label=PRODUCT_LABEL)

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    state_rules.update(wc_state_row(ctx.issue_state))
    outcome.metadata["state_rules_applied"] = state_rules

    if state_rules.get("monopolistic_fund"):
        outcome.eligible = False
        fund_name = state_rules.get("state_fund_name") or f"{ctx.issue_state} state fund"
        outcome.add_reason(f"{ctx.issue_state} is an exclusive/monopolistic workers' comp state — private carriers cannot write this coverage; employer must purchase from {fund_name}")
        outcome.metadata["exposure"] = 0.0
        outcome.metadata["exposure_basis"] = "monopolistic_fund_ineligible"
        return outcome

    if state_rules.get("non_subscription_permitted"):
        outcome.add_condition(
            f"{ctx.issue_state} permits non-subscription — confirm the employer is electing WC coverage "
            "rather than opting out of the state system (opt-out forfeits standard WC coverage and common-law defenses)"
        )

    outcome.add_condition(f"{state_rules['waiting_period_days']}-day waiting period before indemnity benefits begin ({ctx.issue_state or 'default'})")

    from insureflow.rating.commercial_actuarial import WC_EXPENSE_CONSTANT, WC_MIN, rate_workers_comp_ncci

    priced: QuoteResult = rate_workers_comp_ncci(
        ctx.bundle,
        ctx.memo,
        state=ctx.issue_state,
        schedule_mod_pct=ctx.schedule_mod_pct,
        market_mod_pct=ctx.market_mod_pct,
        experience_mod=ctx.experience_mod,
    )
    outcome.eligible = priced.eligible
    outcome.base_premium = priced.base_premium
    outcome.adjusted_premium = priced.adjusted_premium
    outcome.components = list(priced.schedule_modifications)
    for r in priced.ineligibility_reasons:
        outcome.add_reason(r)
    outcome.metadata.update(priced.metadata)
    outcome.metadata["exposure"] = priced.metadata.get("payroll", 0.0)
    outcome.metadata["exposure_basis"] = "payroll"

    if priced.eligible:
        exp_mod = float(priced.metadata.get("experience_mod") or 1.0)
        state_rel = float(priced.metadata.get("state_relativity") or 1.0)
        standard_premium = priced.base_premium * exp_mod * state_rel
        discounted_standard, discount_pct = ncci_premium_discount(standard_premium)
        if discount_pct > 0 and standard_premium > 0:
            # Same discount ratio applied to the pre-expense-constant premium
            # (which already carries market/schedule mods on top of standard
            # premium) — the flat expense constant itself isn't discountable.
            pre_constant = priced.adjusted_premium - WC_EXPENSE_CONSTANT
            discounted_pre_constant = pre_constant * (discounted_standard / standard_premium)
            outcome.adjusted_premium = max(round(discounted_pre_constant + WC_EXPENSE_CONSTANT, 2), WC_MIN)
            outcome.components.append(RateComponent(name="ncci_premium_discount", amount=round(standard_premium, 2), basis="standard_premium", modifier_pct=-discount_pct))
            outcome.metadata["standard_premium"] = round(standard_premium, 2)
            outcome.metadata["premium_discount_pct"] = round(discount_pct, 2)
            outcome.add_condition(f"NCCI premium discount {discount_pct:.1f}% applied on ${standard_premium:,.0f} standard premium (layered by size, not flat)")

    return outcome


def build_quote(ctx: CommercialProductContext) -> QuoteResult:
    outcome = underwrite_workers_comp(ctx)
    exposure = float(outcome.metadata.get("exposure") or 0.0)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="workers_comp",
        exposure=exposure,
        exposure_basis=str(outcome.metadata.get("exposure_basis") or "payroll"),
        extra_meta={"rating_engine": "ncci_class_emod"},
    )
