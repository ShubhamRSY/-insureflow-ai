"""Canonical US health-insurance state-law table.

Reuses the existing 52-jurisdiction regulatory data
(insureflow/regulatory/data/health.yaml, already loaded by
insureflow.regulatory.health_compliance) instead of re-parsing it — this
file translates that data into the flat "canonical row" shape every health
LOB path merges via base.merge_state_rules(), the same pattern
insureflow.life.lobs.state_law uses for life.

One concept health.yaml does NOT carry, added here explicitly: the 5 states
(plus Puerto Rico) that run their own state disability insurance (SDI)
program, which coordinates with — and can offset — a private short/long-term
disability policy. This is a real, specific compliance fact a Disability
Income underwriter has to account for that a generic ACA table wouldn't
carry.
"""

from __future__ import annotations

from typing import Any

# States (plus PR) that run a state disability insurance (SDI) program.
# A private STD/LTD policy issued here must coordinate benefits with the
# state program — carriers typically require an SDI offset rider or reduce
# the private benefit by the state benefit amount.
SDI_STATES: frozenset[str] = frozenset({"CA", "NY", "NJ", "RI", "HI", "PR"})

# Medigap "birthday rule" states: policyholders may switch Medigap plans
# (same or lesser value) within 30-63 days of their birthday each year
# without medical underwriting, independent of the federal one-time
# open-enrollment window at 65.
MEDIGAP_BIRTHDAY_RULE_STATES: frozenset[str] = frozenset({"CA", "OR", "MO", "NV", "ID", "IL", "LA"})

# Medigap continuous/guaranteed-issue states: community-rated or
# guaranteed-issue year-round, not just the 6-month window after 65.
MEDIGAP_CONTINUOUS_GI_STATES: frozenset[str] = frozenset({"CT", "MA", "NY", "ME"})

DEFAULT_GRACE_PERIOD_DAYS = 31


def _get_state_health_rule(issue_state: str) -> dict[str, Any]:
    from insureflow.regulatory.health_compliance import _get_state_health_rule as _loader

    return _loader(issue_state)


def canonical_state_row(issue_state: str) -> dict[str, Any]:
    """Flat, merge-ready row of everything the platform knows about a state's
    health-insurance regulation, sourced from health.yaml.
    """
    if not issue_state:
        return {}
    rule = _get_state_health_rule(issue_state)
    if not rule:
        return {"grace_period_days": DEFAULT_GRACE_PERIOD_DAYS}
    return {
        "rate_filing": rule.get("rate_filing", "file_and_use"),
        "state_individual_mandate": bool(rule.get("state_individual_mandate", False)),
        "state_exchange": bool(rule.get("state_exchange", False)),
        "state_exchange_type": rule.get("state_exchange_type", "federally_facilitated"),
        "small_group_reform": bool(rule.get("small_group_reform", False)),
        "essential_health_benefits": rule.get("essential_health_benefits", "federal_baseline"),
        "minimum_metal_level": rule.get("minimum_metal_level"),
        "community_rating": bool(rule.get("community_rating", False)),
        "guaranteed_issue": bool(rule.get("guaranteed_issue", False)),
        "modified_community_rating": bool(rule.get("modified_community_rating", False)),
        "mandated_benefits": list(rule.get("mandated_benefits") or []),
        "autism_mandate": bool(rule.get("autism_mandate", False)),
        "mental_health_parity": bool(rule.get("mental_health_parity", False)),
        "infusion_therapy": bool(rule.get("infusion_therapy", False)),
        "ivf_mandate": bool(rule.get("ivf_mandate", False)),
        "grace_period_days": int(rule.get("grace_period_days") or DEFAULT_GRACE_PERIOD_DAYS),
        "external_review": bool(rule.get("external_review", False)),
        "notes": rule.get("notes", ""),
    }


def is_sdi_state(issue_state: str) -> bool:
    return (issue_state or "").upper() in SDI_STATES


def medigap_enrollment_rules(issue_state: str) -> dict[str, Any]:
    state = (issue_state or "").upper()
    return {
        "birthday_rule": state in MEDIGAP_BIRTHDAY_RULE_STATES,
        "continuous_guaranteed_issue": state in MEDIGAP_CONTINUOUS_GI_STATES,
    }
