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
    finish_quote,
    merge_state_rules,
    purchase_price,
)
from insureflow.rating.models import RateComponent
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


def _parse_schedule(ctx: LifeProductContext) -> tuple[float, int]:
    """Explicit schedule parse: '$X per month for N years' from the submission."""
    blob = _blob(ctx.bundle)
    m = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)\s*(?:per\s+month|/month|monthly)", blob, re.I)
    monthly = float(m.group(1).replace(",", "")) if m else 0.0
    y = re.search(r"for\s+(\d{1,2})\s*years", blob, re.I)
    years = int(y.group(1)) if y else 20
    if monthly <= 0:
        annual = purchase_price(ctx) / years
        return round(annual / 12.0, 2), years
    return monthly, years


def underwrite_structured_settlement(ctx: LifeProductContext) -> LobOutcome:
    outcome = LobOutcome(product_label="Structured Settlement Annuity")

    state_rules = merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
    interest = float(state_rules["payout_basis_interest"])
    monthly_payment, years = _parse_schedule(ctx)

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

    outcome.components = [
        RateComponent(name="monthly_payment", amount=round(monthly_payment, 2), basis=f"guaranteed {years}yr certain"),
        RateComponent(name="pv_of_schedule", amount=settlement_value, basis=f"@ {interest:.0%} monthly"),
    ]
    outcome.metadata.update(
        {
            "actuarial": {
                "basis": "PV of fixed settlement schedule (period-certain)",
                "interest_rate": interest,
            },
            "monthly_payment": round(monthly_payment, 2),
            "term_years": years,
            "total_nominal_payouts": total_paid,
            "present_value_of_settlement": settlement_value,
            "qualified_assignment_required": True,
            "tax_free_treatment_if_qualifying": True,
            "state_rules_applied": state_rules,
            "exam_required": False,
        }
    )

    filing = ctx.filing_state
    issue = ctx.issue_state
    outcome.eligible = False
    outcome.add_reason("structured settlement illustration only — requires a qualified assignment filing to issue")
    if issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
    return outcome


def build_quote(ctx: LifeProductContext) -> Any:
    outcome = underwrite_structured_settlement(ctx)
    return finish_quote(
        ctx,
        outcome,
        logic_path=LOGIC_PATH,
        family="annuity",
        rating_engine="annuity_illustration",
        apply_minimum_premium=False,
    )
