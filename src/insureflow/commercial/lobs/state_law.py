"""State-law tables for Commercial lines — researched statutory/regulatory facts.

    carrier defaults  <-  THIS TABLE (state law)  <-  product STATE_RULES rows

Scope is deliberately honest and uneven across products, matching where real
state-specific commercial insurance law actually exists:

  - Workers' Comp has hard state variance: 4 states run an exclusive/
    monopolistic state fund where a private carrier CANNOT write coverage
    at all, and Texas is the one state where WC is optional, not mandatory.
  - Property has two well-established state doctrines: valued policy law
    (pays full stated value on a total loss of real property, regardless of
    actual cash value) and named-storm/hurricane percentage deductibles in
    wind-exposed coastal states.
  - Trade Credit and E&O are predominantly placed non-admitted (surplus
    lines) — the per-state surplus-lines premium tax is a real, material
    cost difference by state.
  - D&O and Key Person have comparatively little genuine state-specific
    variance nationally; they consume only the shared surplus-lines table
    below rather than a fabricated bespoke table.

Sources (web-verified September 2026, not just training-data recall — see
inline citations below for the load-bearing facts):
  - Monopolistic fund states: Insureon/Progressive/Hartford/Sentry state-fund
    guides, cross-confirmed (ND, OH, WA, WY unanimous across all sources).
  - Texas non-subscription: Texas Labor Code Sec. 406.002; Fibich Leebron
    Copeland & Briggs, Higginbotham.
  - Valued Policy Law states: cross-confirmed via IRMI ("Valued Policy
    Laws—What Constitutes a Total Loss?") and PropertyCasualty360 — both
    independently list the same 20-state set. Wisconsin is DELIBERATELY
    EXCLUDED despite appearing in some general summaries: its 1976 repeal
    and 1979 re-enactment narrowed it to owner-occupied 1-4 family
    residential only (IRMI), so it does not apply to commercial property.
    California is deliberately excluded for the same reason (Cal. Ins.
    Code Sec. 2051 is a dwelling-total-loss statute).
  - Named-storm deductible states: NAIC consumer-insight page ("What Are
    Named Storm Deductibles?"), current as of June 2025 — 19 states + DC.
  - Wind pool / beach-plan states: AgentSync's insurer-of-last-resort survey
    (FL/MS/SC/TX named explicitly as dedicated "windstorm plans"; NC's
    NCIUA/Beach Plan confirmed separately) plus the well-documented
    Louisiana Citizens and Alabama Insurance Underwriting Association wind
    pools.
  - Surplus-lines tax rates: primary DOI/association sources per state —
    FL: FSLSO (4.94%, eff. 7/1/2020, F.S. 626.938 for the un-reduced 5%
    IPC rate); TX: Texas Insurance Code Sec. 225.004 (4.85%); LA: LDI
    (4.85%); NY (3.60%), IL: Surplus Line Association of Illinois (3.5%);
    CA: California DOI / SLA of California (3.0%); WA: WA OIC (2.0%); GA
    (4%), PA (3%), NV (3.5%) per general secondary-source cross-check
    (lower confidence than the primary-cited states above).
  - Real-estate-E&O-mandatory states: this is a genuinely contested list
    across secondary sources — one search returned a 7-state list, another
    a disjoint 14-state list. Only entries with either a primary statute
    citation or 2+ independent corroborating sources are kept here (CO,
    ID, IA, AK, SD, MT — MT confirmed via a direct hit on Mont. Code Ann.
    Sec. 37-51-325, SD via its own Real Estate Commission page). This is
    almost certainly incomplete; treat "not in this set" as "unconfirmed,"
    not "does not require it."

None of the above substitutes for a licensed insurance-law review before
relying on these facts in an actual bind decision — see the same standing
caveat in insureflow.life.lobs.state_law.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# WORKERS' COMPENSATION
# ---------------------------------------------------------------------------

# Exclusive/monopolistic state funds — a private WC carrier cannot write
# coverage in these states at all; the employer must buy from the state fund.
MONOPOLISTIC_FUND_STATES: frozenset[str] = frozenset({"ND", "OH", "WA", "WY"})

MONOPOLISTIC_FUND_NAMES: dict[str, str] = {
    "ND": "North Dakota Workforce Safety & Insurance",
    "OH": "Ohio Bureau of Workers' Compensation",
    "WA": "Washington State Fund (L&I)",
    "WY": "Wyoming Workers' Compensation Division",
}

# Texas is the sole US state where carrying workers' comp is optional
# (Texas Labor Code Sec. 406.002) — a "non-subscriber" employer forfeits
# the common-law defenses WC would otherwise provide.
NON_SUBSCRIPTION_STATES: frozenset[str] = frozenset({"TX"})

# Waiting period before disability/indemnity benefits begin (days). NCCI
# model states use 7 days; states below are documented exceptions.
WC_WAITING_PERIOD_DAYS_DEFAULT = 7
WC_WAITING_PERIOD_DAYS: dict[str, int] = {
    "CA": 3,
    "OR": 3,
    "MA": 5,
    "WI": 3,
    "FL": 7,
}


def wc_state_row(issue_state: str) -> dict[str, Any]:
    """State-law row for a workers' comp submission; empty when unknown state."""
    state = (issue_state or "").upper()
    row: dict[str, Any] = {
        "waiting_period_days": WC_WAITING_PERIOD_DAYS.get(state, WC_WAITING_PERIOD_DAYS_DEFAULT),
    }
    if state in MONOPOLISTIC_FUND_STATES:
        row["monopolistic_fund"] = True
        row["state_fund_name"] = MONOPOLISTIC_FUND_NAMES.get(state, "")
    if state in NON_SUBSCRIPTION_STATES:
        row["non_subscription_permitted"] = True
    return row


# ---------------------------------------------------------------------------
# PROPERTY / BUSINESS INTERRUPTION
# ---------------------------------------------------------------------------

# Valued Policy Law states: on a total loss of covered real property, the
# insurer must pay the FULL stated policy value, regardless of a lower
# actual-cash-value/replacement-cost appraisal at time of loss. CA and WI
# are deliberately excluded — both are narrowed by statute to owner-occupied
# 1-4 family residential total losses only, not commercial property.
VALUED_POLICY_LAW_STATES: frozenset[str] = frozenset({"AR", "FL", "GA", "KS", "LA", "MN", "MS", "MO", "MT", "NE", "NH", "ND", "OH", "SC", "SD", "TN", "TX", "WV"})

# States that apply a percentage-of-value (rather than a flat-dollar) named
# storm / hurricane deductible in wind-exposed counties, distinct from the
# policy's standard peril deductible. Per NAIC, 19 states + DC as of 6/2025.
NAMED_STORM_DEDUCTIBLE_STATES: frozenset[str] = frozenset({"AL", "CT", "DE", "FL", "GA", "HI", "LA", "ME", "MD", "MA", "MS", "NJ", "NY", "NC", "PA", "RI", "SC", "TX", "VA", "DC"})

# Illustrative named-storm deductible band (% of building value) — actual
# percentage is carrier-filed and county-specific; this is a placeholder
# range for disclosure purposes only.
NAMED_STORM_DEDUCTIBLE_PCT_RANGE: tuple[float, float] = (1.0, 5.0)

# States operating a residual-market wind pool / FAIR Plan that becomes the
# market of last resort for the highest coastal-wind-exposed risks.
WIND_POOL_STATES: frozenset[str] = frozenset({"FL", "TX", "LA", "MS", "AL", "SC", "NC"})


def property_state_row(issue_state: str) -> dict[str, Any]:
    """State-law row for a commercial property submission."""
    state = (issue_state or "").upper()
    row: dict[str, Any] = {}
    if state in VALUED_POLICY_LAW_STATES:
        row["valued_policy_law"] = True
    if state in NAMED_STORM_DEDUCTIBLE_STATES:
        row["named_storm_pct_deductible"] = True
        row["named_storm_pct_range"] = NAMED_STORM_DEDUCTIBLE_PCT_RANGE
    if state in WIND_POOL_STATES:
        row["wind_pool_available"] = True
    return row


# ---------------------------------------------------------------------------
# SURPLUS LINES PREMIUM TAX — Trade Credit, E&O, and (where non-admitted)
# D&O/Key Person are predominantly placed non-admitted. Rate applies to the
# taxable premium, insured-paid (not insurer-absorbed like life's annuity
# premium tax).
# ---------------------------------------------------------------------------
SURPLUS_LINES_TAX: dict[str, float] = {
    "CA": 0.030,
    "TX": 0.0485,
    "FL": 0.0494,
    "NY": 0.036,
    "IL": 0.035,
    "LA": 0.0485,
    "WA": 0.020,
    "GA": 0.040,
    "PA": 0.030,
    "NV": 0.035,
}
SURPLUS_LINES_TAX_DEFAULT = 0.030

# ---------------------------------------------------------------------------
# ERRORS & OMISSIONS — states that condition real-estate-licensee practice
# on carrying E&O (or an explicit client-disclosed opt-out). Flagged as a
# compliance condition, not a fabricated dollar minimum — the actual
# required limit is set by the state real-estate commission, not a filed
# insurance manual, and must be confirmed there before bind. This list is
# deliberately conservative (see module docstring: secondary sources
# disagree substantially on the full membership) — absence from this set
# means "unconfirmed," not "not required."
# ---------------------------------------------------------------------------
REAL_ESTATE_EO_MANDATORY_STATES: frozenset[str] = frozenset({"CO", "ID", "IA", "AK", "SD", "MT"})


def eo_state_row(issue_state: str) -> dict[str, Any]:
    state = (issue_state or "").upper()
    row: dict[str, Any] = {}
    if state in REAL_ESTATE_EO_MANDATORY_STATES:
        row["real_estate_eo_mandatory"] = True
    return row
