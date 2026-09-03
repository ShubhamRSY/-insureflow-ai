"""Errors & Omissions (E&O) / Professional Liability — dedicated logic path.

Priced with a real Increased Limits Factor (ILF) power curve
(``insureflow.commercial.lobs.base.price_limit_driven_specialty``) instead
of the flat "exposure/100 x loss_cost x LCM" linear proxy — see
``directors_officers.py``'s module docstring for why a flat per-dollar
rate is actuarially wrong for a limit-driven liability line. Adds two real
state-law layers the generic engine never applied: the per-state
surplus-lines premium tax (E&O is frequently non-admitted for
higher-hazard professions) and a small, explicitly-sourced flag for
states that condition real-estate licensure on carrying E&O. The flag
names the state requirement only — the actual required minimum limit is
set by the state real-estate commission, not a filed insurance manual,
and must be confirmed there before bind.
"""

from __future__ import annotations

from typing import Any

from insureflow.commercial.lobs.base import CommercialProductContext, LobOutcome, finish_quote, merge_state_rules, price_limit_driven_specialty, surplus_lines_tax
from insureflow.commercial.lobs.state_law import eo_state_row
from insureflow.rating.models import InsuranceLine, QuoteResult
from insureflow.underwriting.personal_lines import _blob

PRODUCT_ID = "errors_omissions"
LOGIC_PATH = "insureflow.commercial.lobs.errors_omissions"
PRODUCT_LABEL = "Errors & Omissions (E&O) / Professional Liability"

DEFAULT_STATE_RULES: dict[str, Any] = {"real_estate_eo_mandatory": False}
STATE_RULES: dict[str, dict[str, Any]] = {}


def underwrite_errors_omissions(ctx: CommercialProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label=PRODUCT_LABEL)
    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    state_rules.update(eo_state_row(ctx.issue_state))
    outcome.metadata["state_rules_applied"] = state_rules

    blob = _blob(ctx.bundle).lower()
    if state_rules.get("real_estate_eo_mandatory") and "real estate" in blob:
        outcome.add_condition(
            f"{ctx.issue_state} conditions real-estate-licensee practice on carrying E&O (or a documented client opt-out) — "
            "confirm the state real estate commission's current minimum limit before bind"
        )

    base, adjusted, components, price_meta = price_limit_driven_specialty(ctx, InsuranceLine.ERRORS_AND_OMISSIONS)
    outcome.base_premium = base
    outcome.adjusted_premium = adjusted
    outcome.components = components
    outcome.metadata.update(price_meta)
    if price_meta.get("used_default_exposure"):
        outcome.add_reason(f"No explicit exposure found — rated on default {price_meta['exposure_basis'].replace('_', ' ')} ${price_meta['exposure']:,.0f}")

    tax = surplus_lines_tax(ctx, outcome.adjusted_premium)
    if tax:
        outcome.metadata["surplus_lines_tax"] = tax
        outcome.add_condition(f"Surplus-lines premium tax {tax['rate']:.2%} (≈${tax['amount']:,.0f}) applies if placed non-admitted in {tax['state']}")

    return outcome


def build_quote(ctx: CommercialProductContext) -> QuoteResult:
    outcome = underwrite_errors_omissions(ctx)
    exposure = float(outcome.metadata.get("exposure") or 0.0)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="specialty",
        exposure=exposure,
        exposure_basis=str(outcome.metadata.get("exposure_basis") or "stated_limit"),
    )
