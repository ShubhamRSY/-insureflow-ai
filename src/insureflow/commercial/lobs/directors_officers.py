"""Directors & Officers (D&O) Liability — dedicated logic path.

Priced with a real Increased Limits Factor (ILF) power curve
(``insureflow.commercial.lobs.base.price_limit_driven_specialty``) instead
of the flat "exposure/100 x loss_cost x LCM" linear proxy
(``insureflow.rating.commercial_specialty.rate_specialty_line``) — a flat
per-dollar rate is actuarially wrong for a limit-driven liability line,
since loss cost grows sub-linearly with limit (frequency is roughly
limit-independent; only large-loss severity scales up). D&O has
comparatively little genuine state-specific law nationally, so this
path's other real value-add is architectural: the two hard UW gates that
today live buried inside ``commercial_specialty.underwrite_specialty``
(financial distress, unclear prior-acts/continuity) are owned here
directly, plus honest surplus-lines tax stamping where the placement is
non-admitted — no fabricated state table where none genuinely exists.
"""

from __future__ import annotations

from typing import Any

from insureflow.commercial.lobs.base import CommercialProductContext, LobOutcome, finish_quote, merge_state_rules, price_limit_driven_specialty, surplus_lines_tax
from insureflow.rating.models import InsuranceLine, QuoteResult
from insureflow.underwriting.personal_lines import _blob

PRODUCT_ID = "directors_officers"
LOGIC_PATH = "insureflow.commercial.lobs.directors_officers"
PRODUCT_LABEL = "Directors & Officers (D&O) Liability"

DEFAULT_STATE_RULES: dict[str, Any] = {"non_admitted_typical": True}
STATE_RULES: dict[str, dict[str, Any]] = {}


def underwrite_directors_officers(ctx: CommercialProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label=PRODUCT_LABEL)
    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    outcome.metadata["state_rules_applied"] = state_rules

    blob = _blob(ctx.bundle).lower()
    if any(k in blob for k in ("bankruptcy", "going concern", "insolvent")):
        outcome.eligible = False
        outcome.add_reason("Going-concern / insolvency language on file — decline or refer to Chief Underwriting Officer")
    elif "prior acts" not in blob and "continuity date" not in blob and "claims made" in blob:
        outcome.add_condition("Claims-made D&O without a documented prior-acts warranty or continuity date — underwriter referral required before bind")

    base, adjusted, components, price_meta = price_limit_driven_specialty(ctx, InsuranceLine.DIRECTORS_AND_OFFICERS)
    outcome.base_premium = base
    outcome.adjusted_premium = adjusted if outcome.eligible else 0.0
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
    outcome = underwrite_directors_officers(ctx)
    exposure = float(outcome.metadata.get("exposure") or 0.0)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="specialty",
        exposure=exposure,
        exposure_basis=str(outcome.metadata.get("exposure_basis") or "stated_limit"),
    )
