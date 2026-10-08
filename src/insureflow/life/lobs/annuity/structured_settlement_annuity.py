"""Structured Settlement Annuity — dedicated logic path (LOB 7).

Coverages: Structured Periodic Payments, Commuted Lump. Settlement proceeds
from a legal claim are paid on a fixed schedule; the path prices the PV of
the schedule and requires a QUALIFIED ASSIGNMENT — this is litigation
infrastructure, not a retail purchase.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.life.lobs.base import (
    LifeProductContext,
    LobOutcome,
    apply_state_filing_gate,
    finish_quote,
    merge_state_rules,
    purchase_price,
)
from insureflow.rating.models import RateComponent
from insureflow.underwriting.life_product import is_filed_annuity_product
from insureflow.underwriting.personal_lines import _blob

PRODUCT_ID = "structured_settlement_annuity"
LOGIC_PATH = "insureflow.life.lobs.annuity.structured_settlement_annuity"

DEFAULT_STATE_RULES: dict[str, Any] = {
    "free_look_days": 10,
    "payout_basis_interest": 0.04,
    "court_approval_required": True,
    "disclosures": [
        "Transfer of structured settlement rights requires court approval under state structured settlement protection acts",
    ],
}
STATE_RULES: dict[str, dict[str, Any]] = {
    "AZ": {"spousal_consent_required": True},
    "ID": {"spousal_consent_required": True},
    "LA": {"spousal_consent_required": True},
    "NV": {"spousal_consent_required": True},
    "NM": {"spousal_consent_required": True},
    "WA": {"spousal_consent_required": True},
    "WI": {"spousal_consent_required": True},
}

MIN_SETTLEMENT = 25_000.0


def _parse_schedule(ctx: LifeProductContext) -> tuple[float, int, bool]:
    """Monthly amount, month count, and whether both were written on the submission.

    A missing term is not 20 years. An explicit "$0 per month" is a zero
    schedule, not a missing one.
    """
    blob = _blob(ctx.bundle)
    amount = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)\s*(?:per\s+month|/month|monthly)", blob, re.I)
    years_m = re.search(r"for\s+(\d{1,2})\s*years", blob, re.I)
    payments_m = re.search(r"for\s+(\d{1,4})\s*payments", blob, re.I)
    if years_m:
        months = int(years_m.group(1)) * 12
        term_stated = True
    elif payments_m:
        months = int(payments_m.group(1))
        term_stated = True
    else:
        months = 20 * 12
        term_stated = False
    if amount:
        return float(amount.group(1).replace(",", "")), months, term_stated
    annual = purchase_price(ctx) / (months / 12.0)
    return round(annual / 12.0, 2), months, False


def underwrite_structured_settlement(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Structured Settlement Annuity")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    interest = float(state_rules["payout_basis_interest"])
    monthly_payment, months, explicit = _parse_schedule(ctx)
    years = months / 12.0

    outcome.add_condition(f"{state_rules['free_look_days']}-day free-look period applies ({state_rules['issue_state'] or 'default'})")
    if state_rules["court_approval_required"]:
        outcome.add_condition("Court approval / qualified assignment REQUIRED before any transfer or commutation")
    for disclosure in state_rules["disclosures"]:
        outcome.add_condition(disclosure)

    # PV of the fixed payment stream (certain-and-period — not life-contingent).
    v = 1.0 / (1.0 + interest / 12.0)
    months = years * 12
    pv_monthly_stream = monthly_payment * (1.0 - v**months) / (interest / 12.0)
    settlement_value = round(pv_monthly_stream, 2)

    commuted = ctx.coverage_id == "structured_lump"
    if commuted:
        outcome.product_label = "Commuted Lump-Sum Settlement"
        outcome.metadata["commuted_lump_pv"] = settlement_value

    total_paid = round(monthly_payment * months, 2)

    # The settlement's PV is the closest analog to a "premium" this product
    # has — without it, QuoteResult.adjusted_premium/base_premium stay $0.
    outcome.annual_premium = settlement_value
    outcome.base_premium = settlement_value

    outcome.components = [
        RateComponent(name="monthly_payment", amount=round(monthly_payment, 2), basis=f"guaranteed {months} months certain"),
        RateComponent(name="pv_of_schedule", amount=settlement_value, basis=f"@ {interest:.0%} annual ({interest / 12:.3%} monthly)"),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "PV of fixed settlement schedule (period-certain)",
                "interest_rate": interest,
            },
            "monthly_payment": round(monthly_payment, 2),
            "term_years": years,
            "term_months": months,
            "schedule_source": "submission" if explicit else "assumed",
            "total_nominal_payouts": total_paid,
            "present_value_of_settlement": settlement_value,
            # Not a purchase_price in the retail-annuity sense, but this is
            # what apply_platform_state_law reads for the premium-tax note —
            # the qualified assignment carrier does fund this consideration.
            "purchase_price": settlement_value,
            "qualified_assignment_required": True,
            "tax_free_treatment_if_qualifying": True,
            "state_rules_applied": state_rules,
            "exam_required": False,
            # This is litigation infrastructure funding a court-ordered
            # schedule, not a producer recommending a purchase to a retail
            # buyer — NY Reg 187 / NAIC #275 Best Interest sales-suitability
            # language doesn't apply here (see apply_platform_state_law).
            "_skip_consumer_suitability": True,
        }
    )

    if not explicit:
        outcome.eligible = False
        outcome.add_reason("Payment schedule is not on the submission — structured settlement is not issueable on an assumed stream")
    elif monthly_payment <= 0:
        outcome.eligible = False
        outcome.add_reason("Structured settlement payment schedule is zero")
    elif settlement_value < MIN_SETTLEMENT:
        outcome.eligible = False
        outcome.add_reason(f"Settlement present value ${settlement_value:,.0f} is below the ${MIN_SETTLEMENT:,.0f} minimum")

    filed = is_filed_annuity_product(PRODUCT_ID)
    apply_state_filing_gate(ctx, outcome, filed_for_state=filed, product_family="structured_settlement_annuity")
    if filed and outcome.eligible:
        raw = (ctx.manual or {}).get("annuity_filing")
        filing = raw if isinstance(raw, dict) else {}
        outcome.metadata["filed_annuity"] = True
        if filing.get("filing_id"):
            outcome.metadata["filing_id"] = filing["filing_id"]
        if filing.get("serff_tracking"):
            outcome.metadata["serff_tracking"] = filing["serff_tracking"]
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_structured_settlement(ctx)
    filed = is_filed_annuity_product(PRODUCT_ID)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="life_filing" if filed else "annuity_illustration",
        apply_minimum_premium=False,
    )
