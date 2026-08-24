"""Canonical state-law table for Life lines — the platform layer of the merge chain.

    carrier defaults  ←  THIS TABLE (state law)  ←  module STATE_RULES rows

Values here reflect statutory minimums / commonly filed provisions and MUST be
reviewed against DOI filings before production use in a given state. Module
rows always win where a product deviates (e.g., annuity free-look in CA).
"""

from __future__ import annotations

# Statutory free-look (cancellation) period in days for life insurance.
# Distinctive states encoded explicitly; the NAIC-model floor of 10 days is
# used elsewhere. Verify each against the state DOI before filing.
FREE_LOOK_DAYS: dict[str, int] = {
    "AL": 10,
    "AK": 10,
    "AZ": 10,
    "AR": 10,
    "CA": 10,
    "CO": 10,
    "CT": 30,
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
    "RI": 10,
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
    "WY": 10,
}

# Spousal/community consent applies in community- (and Wisconsin marital-)
# property jurisdictions — relevant to annuity payout elections.
COMMUNITY_PROPERTY_STATES: frozenset[str] = frozenset({"AZ", "CA", "ID", "LA", "NV", "NM", "TX", "WA", "WI"})


def canonical_state_row(issue_state: str) -> dict[str, int]:
    """State-law row for the merge chain; empty dict when unknown state."""
    days = FREE_LOOK_DAYS.get((issue_state or "").upper())
    return {"free_look_days": days} if days else {}
