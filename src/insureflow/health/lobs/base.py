"""Shared plumbing for dedicated health LOB logic paths.

Mirrors insureflow.life.lobs.base: this module carries ONLY data plumbing
(context, outcome, QuoteResult conversion) and tiny numeric helpers. All
underwriting rules, factors, and state tables live explicitly inside each
product module — there is no generic rules engine here.

US market. Existing medical/eligibility logic in
insureflow.underwriting.health_uw (pregnancy knockout, occupation class,
senior age gates, disease-specific labs) is REUSED via underwrite_health(),
not reimplemented — each product module calls it with whichever existing
product_id/coverage_id activates the closest-matching real handler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, RateComponent
from insureflow.rating.models import QuoteResult as QuoteResult
from insureflow.underwriting.health_uw import HealthUWDecision
from insureflow.underwriting.personal_lines import _blob


def _extract_sex(blob: str) -> str:
    if "female" in blob or " sex: f" in blob:
        return "female"
    if "male" in blob or " sex: m" in blob:
        return "male"
    return "unknown"


def _extract_tobacco(blob: str) -> bool:
    import re

    return bool(re.search(r"(?:current smoker|nicotine\s*:\s*positive|tobacco\s*:\s*(?!none\b|no\b|non-)\w+|cigarettes\s*:\s*(?!none\b|no\b|0)\w+)", blob, re.I))


def reconcile_for_aca_guaranteed_issue(uw: HealthUWDecision) -> None:
    """Mutates a reused HealthUWDecision in place to match two ACA facts the
    reused handler's own assumptions get wrong:

    1. ACA §2704 bans pre-existing-condition exclusions/waiting periods
       entirely, on every individual/family/group major-medical plan — the
       reused handler's static "PED waiting period" disclosure is simply
       false here, not just inapplicable, so it's replaced with the correct
       statement rather than silently dropped.
    2. Some reused handlers gate on a 60+ "route to senior" rule (the
       reused source market's senior threshold) — the real US Medicare
       eligibility age is 65, already enforced by each ACA product's own
       MAX_ISSUE_AGE=64 gate, so a same-labeled "age_fit" gate failure here
       is a false referral, not a real finding. Downgrades the decision back
       from REFER to ACCEPT only when that was the SOLE failing gate — a
       genuine KYC gap elsewhere still refers normally.
    """
    from insureflow.models.agents import UWDecision

    aca_disclosure = "No pre-existing-condition exclusions or waiting periods — prohibited under ACA §2704"
    uw.conditions = [aca_disclosure if "ped waiting period" in c.lower() else c for c in uw.conditions]
    if aca_disclosure not in uw.conditions:
        uw.conditions.append(aca_disclosure)
    uw.reasons = [r for r in uw.reasons if "route to senior" not in r.lower()]

    if uw.gates.get("age_fit") == "fail" and uw.decision == UWDecision.REFER and all(v != "fail" for k, v in uw.gates.items() if k != "age_fit"):
        uw.decision = UWDecision.ACCEPT
        uw.conditions = [c for c in uw.conditions if "route to senior" not in c.lower()]


@dataclass
class HealthProductContext:
    """Everything a health product-level logic path needs to make its own decision."""

    bundle: SubmissionBundle
    state_code: str  # explicit issue state from the selector ("" if none)
    product_id: str
    coverage_id: str
    coverage_name: str
    manual: dict[str, Any]  # filed manual (rates / factors / filing id)
    # Placeholder from underwrite_health() with no product hint (resolves to
    # the generic KYC-only handler) — underwrite_health() is itself
    # product-id-aware (its own dispatch table keyed on the EXISTING catalog
    # ids), so each LOB path overwrites this with its own
    # `ctx.uw = underwrite_health(ctx.bundle, product_id="<reused handler id>")`
    # call to pull in the real, differentiated, already-tested underwriting
    # logic for that product (pregnancy knockout, occupation class, senior
    # age gates, etc.) rather than reimplementing it.
    uw: HealthUWDecision
    age: int
    sex_key: str  # "male" / "female" / "unknown"
    tobacco: bool = False
    income: float = 0.0
    benefit_amount: float = 0.0  # sum insured / lump sum / monthly benefit — product-specific meaning
    household_members: int = 1  # self + covered dependents, for family-rated products
    modal: str = "annual"
    modal_f: float = 1.0

    @property
    def issue_state(self) -> str:
        return (self.state_code or "").upper()[:2]

    @property
    def filing_state(self) -> str:
        return str((self.manual or {}).get("state_of_filing") or "").upper()

    @property
    def blob(self) -> str:
        return _blob(self.bundle)


@dataclass
class LobOutcome:
    """Result of one product/coverage logic path before QuoteResult conversion."""

    product_label: str = ""
    annual_premium: float = 0.0
    base_premium: float = 0.0
    eligible: bool = True
    reasons: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    components: list[RateComponent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_reason(self, reason: str) -> None:
        if reason and reason not in self.reasons:
            self.reasons.append(reason)

    def add_condition(self, condition: str) -> None:
        if condition and condition not in self.conditions:
            self.conditions.append(condition)


def merge_state_rules(
    ctx: HealthProductContext,
    default_rules: dict[str, Any],
    state_rules: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Merge DEFAULT_STATE_RULES with the canonical health.yaml law row and
    STATE_RULES[issue_state].

    Returns a flat dict with ``issue_state`` and ``source`` stamped so every
    decision record shows exactly which state rules fired.
    """
    from insureflow.health.lobs.state_law import canonical_state_row

    merged = dict(default_rules or {})
    law_row = canonical_state_row(ctx.issue_state)
    merged.update(law_row)
    state_row = (state_rules or {}).get(ctx.issue_state) or {}
    merged.update(state_row)
    merged["issue_state"] = ctx.issue_state
    if state_row:
        merged["source"] = "state_table"
        merged["rule_layer"] = "module"
    elif law_row:
        merged["source"] = "state_table"
        merged["rule_layer"] = "platform"
    else:
        merged["source"] = "carrier_default"
        merged["rule_layer"] = "default"
    return merged


def apply_state_filing_gate(
    ctx: HealthProductContext,
    outcome: LobOutcome,
    *,
    filed_for_state: bool,
    product_family: str,
) -> None:
    """State-of-filing gate — mirrors the platform-wide life rule inside this path."""
    issue = ctx.issue_state
    filing = ctx.filing_state
    if not filed_for_state:
        outcome.eligible = False
        outcome.add_reason(f"{product_family.replace('_', ' ')} has no {filing}-filed rates — illustrative only, not an issueable premium")
    elif issue and filing and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
        if issue not in ((ctx.manual or {}).get("state_relativities") or {}):
            outcome.eligible = False


def apply_binding_gates(ctx: HealthProductContext, outcome: LobOutcome, *, family: str) -> None:
    """Platform binding gates shared by every dedicated health LOB path.

    Propagates the reused HealthUWDecision (medical/eligibility) onto the
    outcome so no product path can bypass it, and lists riders like life's
    equivalent gate.
    """
    from insureflow.models.agents import UWDecision

    if ctx.uw.decision == UWDecision.DECLINE:
        outcome.eligible = False
        for r in ctx.uw.reasons:
            outcome.add_reason(r)
        outcome.metadata["_outcome"] = "decline"
    elif ctx.uw.decision == UWDecision.REFER:
        for c in ctx.uw.conditions:
            outcome.add_condition(c)
        outcome.add_condition("Underwriter referral required before issue")
        outcome.metadata["_outcome"] = "refer"
    else:
        for c in ctx.uw.conditions:
            outcome.add_condition(c)


def finish_quote(
    ctx: HealthProductContext,
    outcome: LobOutcome,
    *,
    logic_path: str,
    family: str,
    rating_engine: str | None = None,
    extra_meta: dict[str, Any] | None = None,
    apply_minimum_premium: bool = True,
) -> QuoteResult:
    """Convert a LobOutcome into the platform QuoteResult contract.

    Mirrors life's finish_quote: ineligible (declined / illustration-only)
    quotes never carry a booked premium in the contract fields — the real
    computed figures are preserved under illustrated_adjusted_premium /
    illustrated_modal_premium in metadata so quote documents and ordering
    tests still see the real number, while revenue/exposure aggregates see
    $0 for business that was never approved.
    """
    apply_binding_gates(ctx, outcome, family=family)
    manual = ctx.manual or {}
    minimum_premium = float(manual.get("minimum_premium", 0.0))
    annual_value = outcome.annual_premium
    if apply_minimum_premium:
        annual_value = max(annual_value, minimum_premium)
    adjusted = round(max(annual_value, 0.0), 2)
    modal_premium = round(adjusted * ctx.modal_f, 2) if ctx.modal != "annual" else adjusted

    illustrated_adjusted = adjusted
    illustrated_modal = modal_premium
    if not outcome.eligible:
        adjusted = 0.0
        modal_premium = 0.0

    meta: dict[str, Any] = {
        "filing_id": manual.get("filing_id"),
        "product": outcome.product_label,
        "product_id": ctx.product_id,
        "coverage_id": ctx.coverage_id,
        "product_family": family,
        "lob_logic_path": logic_path,
        "modal": ctx.modal,
        "modal_premium": modal_premium,
        "illustrated_adjusted_premium": illustrated_adjusted,
        "illustrated_modal_premium": illustrated_modal,
        "issue_state": ctx.issue_state,
        "state_of_filing": ctx.filing_state,
        "rating_engine": rating_engine or "health_filing",
        "benefit_amount": ctx.benefit_amount,
        "underwriting": ctx.uw.to_metadata(),
        "insurance_line": InsuranceLine.HEALTH.value,
        "personal_lines": True,
        "uw_decision_hint": ctx.uw.decision.value,
        "outcome": outcome.metadata.pop("_outcome", "accept"),
        "conditions": [],
        **(extra_meta or {}),
        **outcome.metadata,
    }
    meta["conditions"] = list(outcome.conditions)

    ineligibility = [r for r in outcome.reasons if r] if not outcome.eligible else []
    base = round(outcome.base_premium, 2) if outcome.eligible else 0.0
    rate_per_100 = round(adjusted / (ctx.benefit_amount / 100.0), 4) if ctx.benefit_amount and outcome.eligible else 0.0
    return QuoteResult(
        bundle_id=ctx.bundle.bundle_id,
        line=InsuranceLine.HEALTH,
        base_premium=base,
        adjusted_premium=adjusted,
        schedule_modifications=list(outcome.components),
        rate_per_100_tiv=rate_per_100,
        eligible=outcome.eligible,
        ineligibility_reasons=ineligibility,
        metadata=meta,
    )


def nearest_banded_key(table: dict[str, float], value: float) -> str:
    """Largest table key <= value, for age/deductible/etc. banded lookups."""
    keys = sorted(int(k) for k in table)
    best = keys[0]
    for k in keys:
        if k <= value:
            best = k
    return str(best)


def age_band_factor(ctx: HealthProductContext, table_key: str = "age_curve") -> float:
    """ACA-style age-band rating factor from the manual's age curve."""
    curve = (ctx.manual or {}).get(table_key) or {}
    if not curve:
        return 1.0
    keys = sorted((int(k) for k in curve), reverse=True)
    for k in keys:
        if ctx.age >= k:
            return float(curve[str(k)])
    return float(curve[str(min(keys))]) if keys else 1.0


def tobacco_surcharge(ctx: HealthProductContext) -> float:
    """ACA permits up to a 1.5x tobacco rating factor on individual/group medical."""
    if not ctx.tobacco:
        return 1.0
    return float((ctx.manual or {}).get("tobacco_factor", 1.5))


def area_relativity(ctx: HealthProductContext) -> float:
    return float(((ctx.manual or {}).get("state_relativities") or {}).get(ctx.issue_state) or 1.0)


def policy_fee(ctx: HealthProductContext) -> float:
    return float((ctx.manual or {}).get("policy_fee", 0.0))


def household_tier_factor(ctx: HealthProductContext) -> float:
    """Family-tier composite rating: self-only / self+spouse / self+child(ren) / family.

    US ACA-style composite-tier rating rather than per-member sum-of-ages —
    the whole household's premium is the tier factor applied to the primary
    applicant's individual rate.
    """
    tiers = (ctx.manual or {}).get("household_tier_factors") or {}
    if ctx.household_members <= 1:
        return float(tiers.get("self_only", 1.0))
    if ctx.household_members == 2:
        return float(tiers.get("self_plus_one", 1.9))
    return float(tiers.get("family", 2.75))


HandlerFn = Callable[[HealthProductContext], LobOutcome]
