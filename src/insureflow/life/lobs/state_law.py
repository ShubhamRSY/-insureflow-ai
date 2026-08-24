"""State-law tables for Life lines — researched statutory minimums.

    carrier defaults  ←  THIS TABLE (state law)  ←  module STATE_RULES rows

Sources: state insurance statutes/admin codes as compiled by Fidelity Life
"Life insurance laws by state" (citing e.g. AL Admin Code 482-1-131-.03,
CO Rev. Stat. 10-7-302, CT Gen. Stat. 38a-436, RI Gen. Laws 27-4-6.1,
WY Admin Code Ins Gen Ch 12 s4, 28 TX Admin Code 3.804, UT 31A-22-423,
VA 38.2-3300, WA 48.23.380, NV ST 688A.010), Annuity.org / GetYourAnnuity
50-state annuity free-look compilations, and Cal. Ins. Code 10127.10.
Values are NEW-contract standards; verify against the current DOI exhibit
before production filing in any given state.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# LIFE insurance — statutory free-look minimums (days), new contracts.
# States not listed use the NAIC-model 10-day floor.
# ---------------------------------------------------------------------------
LIFE_FREE_LOOK_DAYS: dict[str, int] = {
    "AL": 10,
    "AK": 20,
    "AZ": 10,
    "AR": 10,
    "CA": 30,
    "CO": 15,
    "CT": 10,
    "DE": 10,
    "DC": 10,
    "FL": 14,
    "GA": 10,
    "HI": 10,
    "ID": 10,
    "IL": 10,
    "IN": 10,
    "IA": 10,
    "KS": 10,
    "KY": 10,
    "LA": 10,
    "ME": 10,
    "MD": 10,
    "MA": 10,
    "MI": 10,
    "MN": 10,
    "MS": 10,
    "MO": 10,
    "MT": 10,
    "NE": 10,
    "NV": 10,
    "NH": 10,
    "NJ": 10,
    "NM": 10,
    "NY": 20,
    "NC": 10,
    "ND": 10,
    "OH": 10,
    "OK": 10,
    "OR": 10,
    "PA": 10,
    "RI": 20,
    "SC": 10,
    "SD": 10,
    "TN": 10,
    "TX": 10,
    "UT": 10,
    "VT": 10,
    "VA": 10,
    "WA": 10,
    "WV": 10,
    "WI": 10,
    "WY": 30,
}

# ---------------------------------------------------------------------------
# ANNUITIES — distinct statutory schedules (new contracts, days).
# ---------------------------------------------------------------------------
ANNUITY_FREE_LOOK_DAYS: dict[str, int] = {
    "AL": 15,
    "AK": 10,
    "AZ": 10,
    "AR": 10,
    "CA": 30,
    "CO": 15,
    "CT": 10,
    "DE": 10,
    "DC": 10,
    "FL": 21,
    "GA": 10,
    "HI": 15,
    "ID": 20,
    "IL": 10,
    "IN": 10,
    "IA": 10,
    "KS": 10,
    "KY": 15,
    "LA": 10,
    "ME": 15,
    "MD": 10,
    "MA": 20,
    "MI": 10,
    "MN": 10,
    "MS": 10,
    "MO": 10,
    "MT": 15,
    "NE": 10,
    "NV": 10,
    "NH": 15,
    "NJ": 10,
    "NM": 15,
    "NY": 30,
    "NC": 10,
    "ND": 10,
    "OH": 15,
    "OK": 15,
    "OR": 15,
    "PA": 10,
    "RI": 20,
    "SC": 10,
    "SD": 10,
    "TN": 10,
    "TX": 20,
    "UT": 10,
    "VT": 10,
    "VA": 10,
    "WA": 10,
    "WV": 15,
    "WI": 30,
    "WY": 30,
}

# Extended window when the contract REPLACES existing coverage (days).
ANNUITY_REPLACEMENT_FREE_LOOK_DAYS: dict[str, int] = {
    "DE": 20,
    "MN": 30,
    "NV": 30,
    "NC": 30,
    "OR": 30,
    "PA": 20,
    "TX": 30,
    "UT": 30,
    "WI": 30,
}

# Senior extensions: {state: (days, min_age)} — e.g. Cal. Ins. Code 10127.10.
ANNUITY_SENIOR_FREE_LOOK: dict[str, tuple[int, int]] = {
    "AZ": (30, 65),
    "CA": (30, 60),
}

# Spousal/community consent applies in community- (and Wisconsin marital-)
# property jurisdictions — relevant to annuity payout elections.
COMMUNITY_PROPERTY_STATES: frozenset[str] = frozenset({"AZ", "CA", "ID", "LA", "NV", "NM", "TX", "WA", "WI"})

_ANNUITY_RE = re.compile(r"annuit|qlac|payout|settlement", re.I)

# ---------------------------------------------------------------------------
# Guaranty-association caps (per policyholder, per insurer).
# Defaults follow the NAIC Life & Health Model Act; overrides per NOLHGA
# member-association disclosures. CA applies 80% coinsurance to each category.
# ---------------------------------------------------------------------------
GUARANTY_DEATH_CAP_DEFAULT = 300_000.0
GUARANTY_CASH_CAP_DEFAULT = 100_000.0
GUARANTY_ANNUITY_PV_CAP_DEFAULT = 250_000.0
GUARANTY_AGGREGATE_DEFAULT = 300_000.0

GUARANTY_DEATH_CAP: dict[str, float] = {
    "CT": 500_000.0,
    "MN": 500_000.0,
    "NJ": 500_000.0,
    "NY": 500_000.0,
    "UT": 500_000.0,
    "WA": 500_000.0,
}
GUARANTY_CASH_CAP: dict[str, float] = {
    "CA": 80_000.0,
    "CT": 500_000.0,
    "MN": 130_000.0,
    "NC": 300_000.0,
    "NY": 500_000.0,
    "SC": 300_000.0,
    "UT": 200_000.0,
    "WA": 500_000.0,
    "WI": 300_000.0,
}
GUARANTY_ANNUITY_PV_CAP: dict[str, float] = {
    "AK": 100_000.0,
    "CT": 500_000.0,
    "DC": 300_000.0,
    "MO": 100_000.0,
    "MS": 100_000.0,
    "NC": 300_000.0,
    "NH": 100_000.0,
    "NY": 500_000.0,
    "OK": 300_000.0,
    "PA": 100_000.0,
    "SC": 300_000.0,
    "UT": 200_000.0,
    "WA": 500_000.0,
    "WI": 300_000.0,
}
GUARANTY_AGGREGATE: dict[str, float] = {
    "CT": 500_000.0,
    "LA": 500_000.0,
    "MN": 500_000.0,
    "NJ": 500_000.0,
    "NY": 500_000.0,
    "UT": 500_000.0,
    "VA": 350_000.0,
    "WA": 500_000.0,
    "WY": 500_000.0,
}
GUARANTY_COINSURANCE_PCT: dict[str, float] = {"CA": 80.0}

# ---------------------------------------------------------------------------
# Grace periods (days) — statutory minimums; NAIC model is 31.
# AL 27-15-3 · CA Ins. Code 10113.71 (60 days!) · CO 10-7-302 · MO 376.726
# NV 688A.060 · RI/SC/TX/UT/VA/WI/WY statutes cited by Fidelity Life table.
# ---------------------------------------------------------------------------
GRACE_PERIOD_DAYS: dict[str, int] = {
    "AL": 30,
    "CA": 60,
    "CO": 31,
    "DE": 30,
    "MO": 31,
    "NV": 30,
    "RI": 31,
    "SC": 31,
    "TX": 31,
    "UT": 31,
    "VA": 31,
    "WA": 30,
    "WI": 31,
    "WY": 31,
}
GRACE_PERIOD_DAYS_DEFAULT = 31

# ---------------------------------------------------------------------------
# Claims-settlement interest rules: {"max_settlement_days", "accrues_from",
# "offset_days"} — interest runs after max_settlement_days from the accrual
# anchor (date of death or receipt of proof of death), shifted by offset_days.
# Sources: AL 27-15-13 · CA 10172.5 · CT 38a-452 · DE 18 DE ADC 2914 ·
# MO 374.191 · NV 688A.140 · RI 27-4-26 · SC 38-63-80 · TX 542.058 ·
# WA 48.23.300 · WI 628.46 · WY 26-16-112.
# ---------------------------------------------------------------------------
CLAIMS_SETTLEMENT_DEFAULT = {"max_settlement_days": 30, "accrues_from": "proof_of_death", "offset_days": 0}
CLAIMS_SETTLEMENT: dict[str, dict[str, Any]] = {
    "AL": {"max_settlement_days": 30, "accrues_from": "proof_of_death", "offset_days": 0},
    "CA": {"max_settlement_days": 30, "accrues_from": "date_of_death", "offset_days": 0},
    "CT": {"max_settlement_days": 30, "accrues_from": "date_of_death", "offset_days": 10},
    "DE": {"max_settlement_days": 30, "accrues_from": "claim_filed", "offset_days": 0},
    "MO": {"max_settlement_days": 30, "accrues_from": "date_of_death", "offset_days": 0},
    "NV": {"max_settlement_days": 60, "accrues_from": "proof_of_death", "offset_days": 0},
    "RI": {"max_settlement_days": 30, "accrues_from": "date_of_death", "offset_days": 0},
    "SC": {"max_settlement_days": 30, "accrues_from": "date_of_death", "offset_days": 0},
    "TX": {"max_settlement_days": 60, "accrues_from": "proof_of_loss", "offset_days": 0},
    "WA": {"max_settlement_days": 30, "accrues_from": "date_of_death", "offset_days": 0},
    "WI": {"max_settlement_days": 30, "accrues_from": "date_of_death", "offset_days": 0},
    "WY": {"max_settlement_days": 45, "accrues_from": "date_of_death", "offset_days": 0},
}

# ---------------------------------------------------------------------------
# State premium tax on annuity considerations — insurer-paid, embedded in
# economics. Non-qualified headline rates; qualified_money_rate where lower.
# SD tiers: 1.25% on the first $500k of premium, 0.08% above.
# FL grants a credit when the tax savings are passed back to policyholders
# (pass_through_credit=True → effectively zero when carrier absorbs it).
# ---------------------------------------------------------------------------
ANNUITY_PREMIUM_TAX: dict[str, dict[str, Any]] = {
    "CA": {"rate": 0.0235, "qualified_money_rate": 0.005},
    "CO": {"rate": 0.02, "qualified_money_rate": 0.0},
    "FL": {"rate": 0.01, "qualified_money_rate": 0.01, "pass_through_credit": True},
    "ME": {"rate": 0.02, "qualified_money_rate": 0.0},
    "NV": {"rate": 0.035, "qualified_money_rate": 0.0},
    "SD": {"rate": 0.0125, "qualified_money_rate": 0.0, "tier_threshold": 500_000.0, "tier_rate_above": 0.0008},
    "WV": {"rate": 0.01, "qualified_money_rate": 0.01},
    "WY": {"rate": 0.01, "qualified_money_rate": 0.0},
}

# ---------------------------------------------------------------------------
# Annuity Best Interest — NAIC Model #275 (2020 revisions) adoption status as
# of the NAIC legislative brief (Aug 2025): 49 jurisdictions implemented;
# NY and DC have not (NY regulates through Reg 187 below).
# ---------------------------------------------------------------------------
BEST_INTEREST_NOT_ADOPTED: frozenset[str] = frozenset({"NY", "DC"})

# NY Reg 187 (11 NYCRR 224) — documented suitability process for BOTH life and
# annuity recommendations in New York.
REG_187_STATES: frozenset[str] = frozenset({"NY"})


def is_annuity_context(product_id: str | None, coverage_id: str | None, coverage_name: str | None) -> bool:
    """True when the selection is an annuity-family product/coverage."""
    blob = " ".join(p for p in (product_id, coverage_id, coverage_name) if p)
    return bool(_ANNUITY_RE.search(blob))


def canonical_state_row(issue_state: str, *, annuity: bool = False) -> dict[str, Any]:
    """State-law row for the merge chain; empty dict when unknown state."""
    state = (issue_state or "").upper()
    table = ANNUITY_FREE_LOOK_DAYS if annuity else LIFE_FREE_LOOK_DAYS
    row: dict[str, Any] = {}
    days = table.get(state)
    if days:
        row["free_look_days"] = days
    if annuity:
        repl = ANNUITY_REPLACEMENT_FREE_LOOK_DAYS.get(state)
        if repl:
            row["replacement_free_look_days"] = repl
        senior = ANNUITY_SENIOR_FREE_LOOK.get(state)
        if senior:
            row["senior_free_look_days"], row["senior_free_look_min_age"] = senior
    if state in GRACE_PERIOD_DAYS or True:
        row["grace_period_days"] = GRACE_PERIOD_DAYS.get(state, GRACE_PERIOD_DAYS_DEFAULT)
    claims = CLAIMS_SETTLEMENT.get(state) or CLAIMS_SETTLEMENT_DEFAULT
    row["claims_settlement"] = dict(claims)
    death_cap = GUARANTY_DEATH_CAP.get(state, GUARANTY_DEATH_CAP_DEFAULT)
    aggregate = GUARANTY_AGGREGATE.get(state, GUARANTY_AGGREGATE_DEFAULT)
    if annuity:
        pv_cap = GUARANTY_ANNUITY_PV_CAP.get(state, GUARANTY_ANNUITY_PV_CAP_DEFAULT)
        row["guaranty"] = {
            "annuity_pv_cap": pv_cap,
            "aggregate_cap": aggregate,
            "coinsurance_pct": GUARANTY_COINSURANCE_PCT.get(state),
        }
    else:
        row["guaranty"] = {
            "death_cap": death_cap,
            "cash_value_cap": GUARANTY_CASH_CAP.get(state, GUARANTY_CASH_CAP_DEFAULT),
            "aggregate_cap": aggregate,
            "coinsurance_pct": GUARANTY_COINSURANCE_PCT.get(state),
        }
    return row


def premium_tax_on_consideration(issue_state: str, consideration: float, *, qualified: bool = False) -> dict[str, Any] | None:
    """Premium-tax economics for an annuity purchase; None when untaxed."""
    rule = ANNUITY_PREMIUM_TAX.get((issue_state or "").upper())
    if not rule or consideration <= 0:
        return None
    rate = rule["qualified_money_rate"] if qualified else rule["rate"]
    tier_threshold = rule.get("tier_threshold")
    amount = 0.0
    if tier_threshold and not qualified and consideration > tier_threshold:
        amount += tier_threshold * rule["rate"]
        amount += (consideration - tier_threshold) * rule["tier_rate_above"]
    else:
        amount = consideration * rate
    return {
        "state": issue_state,
        "rate": rate,
        "amount": round(amount, 2),
        "insurer_paid": True,
        "pass_through_credit": bool(rule.get("pass_through_credit")),
    }


def suitability_regime(issue_state: str, *, annuity: bool) -> dict[str, Any]:
    """Which sales-standard regime governs this recommendation."""
    state = (issue_state or "").upper()
    if state in REG_187_STATES:
        return {
            "regime": "NY Reg 187",
            "citation": "11 NYCRR 224",
            "applies_to": "life_and_annuity",
            "documented_suitability_required": True,
        }
    if annuity and state not in BEST_INTEREST_NOT_ADOPTED:
        return {
            "regime": "NAIC Model #275 Best Interest",
            "obligations": ["care", "disclosure", "conflict_of_interest", "documentation"],
            "producer_training": "4-hour best-interest annuity training",
        }
    if annuity:
        return {"regime": "legacy NAIC suitability (pre-2020 model)"}
    return {"regime": "none_beyond_general_standards"}
