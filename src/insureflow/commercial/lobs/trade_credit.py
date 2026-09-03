"""Trade Credit Insurance — dedicated logic path.

Two real market-convention formulas replace the flat, undifferentiated
receivables rate the generic engine applied:

1. **Indemnity percentage** — a trade credit policy indemnifies a stated
   percentage of a covered loss (industry-standard ~90%, never 100%, so
   the insured stays co-invested in its own credit management) rather
   than the full declared receivables/limit.
2. **Concentration loading** — a real, quantifiable loss-volatility driver:
   a book concentrated in a few large buyers is riskier than an
   equally-sized diversified one. Reuses the same "top buyer
   concentration" extraction ``commercial_checklists.py`` already applies
   as a REFER trigger at >=40%, here as a continuous premium surcharge.

Trade credit is also predominantly placed non-admitted/surplus-lines, so
the per-state surplus-lines premium tax is a genuine, material state-law
cost the generic engine never applied either.
"""

from __future__ import annotations

from typing import Any

from insureflow.commercial.lobs.base import CommercialProductContext, LobOutcome, finish_quote, merge_state_rules, surplus_lines_tax
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.underwriting.personal_lines import _blob, _pct_field

PRODUCT_ID = "trade_credit"
LOGIC_PATH = "insureflow.commercial.lobs.trade_credit"
PRODUCT_LABEL = "Trade Credit Insurance"

DEFAULT_STATE_RULES: dict[str, Any] = {"non_admitted_typical": True}
STATE_RULES: dict[str, dict[str, Any]] = {}

# Standard trade-credit indemnity percentage (insured retains the rest).
INDEMNITY_PCT = 0.90

# Concentration surcharge: no load below the threshold that already
# matters elsewhere in this codebase (commercial_checklists.py refers at
# >=40% top-buyer concentration); above 25% each point adds a real,
# quantifiable loss-volatility surcharge, capped.
CONCENTRATION_SURCHARGE_THRESHOLD_PCT = 25.0
CONCENTRATION_SURCHARGE_PER_POINT = 1.5
CONCENTRATION_SURCHARGE_CAP_PCT = 50.0


def _concentration_surcharge_pct(concentration_pct: float | None) -> float:
    if concentration_pct is None or concentration_pct <= CONCENTRATION_SURCHARGE_THRESHOLD_PCT:
        return 0.0
    surcharge = (concentration_pct - CONCENTRATION_SURCHARGE_THRESHOLD_PCT) * CONCENTRATION_SURCHARGE_PER_POINT
    return min(surcharge, CONCENTRATION_SURCHARGE_CAP_PCT)


def underwrite_trade_credit(ctx: CommercialProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label=PRODUCT_LABEL)
    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.metadata["state_rules_applied"] = state_rules

    from insureflow.rating.commercial_specialty import SPECIALTY_LCM, SPECIALTY_LOSS_COSTS, SPECIALTY_MINIMUMS, estimate_specialty_exposure

    blob = _blob(ctx.bundle)
    gross_exposure, basis, used_default = estimate_specialty_exposure(ctx.bundle, InsuranceLine.TRADE_CREDIT)
    insured_exposure = gross_exposure * INDEMNITY_PCT

    loss_cost = SPECIALTY_LOSS_COSTS.get(InsuranceLine.TRADE_CREDIT, 0.22)
    lcm = SPECIALTY_LCM.get(InsuranceLine.TRADE_CREDIT, 2.15)
    min_prem = SPECIALTY_MINIMUMS.get(InsuranceLine.TRADE_CREDIT, 1_500.0)

    base = (insured_exposure / 100.0) * loss_cost * lcm

    concentration_pct = _pct_field(blob, "top buyer concentration", "top customer concentration", "buyer concentration", "customer concentration", "concentration")
    surcharge_pct = _concentration_surcharge_pct(concentration_pct)

    adjusted = base * (1 + surcharge_pct / 100.0) * (1 + ctx.market_mod_pct / 100.0) * (1 + ctx.schedule_mod_pct / 100.0)
    adjusted = max(round(adjusted + 75.0, 2), min_prem)

    components = [
        RateComponent(name="specialty_loss_cost", amount=loss_cost, basis=f"per_100_{basis}"),
        RateComponent(name="loss_cost_multiplier", amount=lcm, basis="expense_profit"),
        RateComponent(name="indemnity_pct", amount=INDEMNITY_PCT, basis="insured_share_of_loss"),
        RateComponent(name="exposure", amount=gross_exposure, basis=basis),
    ]
    if surcharge_pct:
        components.append(RateComponent(name="buyer_concentration_surcharge", amount=concentration_pct or 0.0, basis="top_buyer_pct", modifier_pct=surcharge_pct))
    if ctx.market_mod_pct:
        components.append(RateComponent(name="market_cycle_adjustment", amount=ctx.market_mod_pct, basis="market", modifier_pct=ctx.market_mod_pct))
    if ctx.schedule_mod_pct:
        components.append(RateComponent(name="uw_schedule_modification", amount=0, basis="uw_discretion", modifier_pct=ctx.schedule_mod_pct))

    outcome.eligible = True
    outcome.base_premium = round(base, 2)
    outcome.adjusted_premium = adjusted
    outcome.components = components
    if used_default:
        outcome.add_reason(f"No explicit exposure found — rated on default {basis.replace('_', ' ')} ${gross_exposure:,.0f}")
    outcome.metadata.update(
        {
            "exposure": gross_exposure,
            "exposure_basis": basis,
            "used_default_exposure": used_default,
            "insured_exposure": round(insured_exposure, 2),
            "indemnity_pct": INDEMNITY_PCT,
            "top_buyer_concentration_pct": concentration_pct,
            "concentration_surcharge_pct": surcharge_pct,
            "rating_engine": "trade_credit_indemnity_concentration",
        }
    )
    if surcharge_pct:
        outcome.add_condition(f"Top-buyer concentration {concentration_pct:.0f}% loads the rate {surcharge_pct:.1f}% — concentrated receivables carry disproportionate loss volatility")

    tax = surplus_lines_tax(ctx, outcome.adjusted_premium)
    if tax:
        outcome.metadata["surplus_lines_tax"] = tax
        outcome.add_condition(f"Surplus-lines premium tax {tax['rate']:.2%} (≈${tax['amount']:,.0f}) applies if placed non-admitted in {tax['state']} — insured-paid, due at bind")

    return outcome


def build_quote(ctx: CommercialProductContext) -> QuoteResult:
    outcome = underwrite_trade_credit(ctx)
    exposure = float(outcome.metadata.get("exposure") or 0.0)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="specialty",
        exposure=exposure,
        exposure_basis=str(outcome.metadata.get("exposure_basis") or "receivables"),
    )
