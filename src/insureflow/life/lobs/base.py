"""Shared plumbing for dedicated life LOB logic paths.

This module intentionally contains ONLY data plumbing (context, outcome,
QuoteResult conversion) and tiny numeric helpers. All underwriting rules,
factors, and state tables live explicitly inside each product module —
per the confirmed architecture there is no generic rules engine here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, RateComponent
from insureflow.rating.models import QuoteResult as QuoteResult
from insureflow.underwriting.life_financial import LifeFinancialResult
from insureflow.underwriting.life_medical import LifeMedicalDecision


@dataclass
class LifeProductContext:
    """Everything a product-level logic path needs to make its own decision."""

    bundle: SubmissionBundle
    state_code: str  # explicit issue state from the selector ("" if none)
    product_id: str
    coverage_id: str
    coverage_name: str
    manual: dict[str, Any]  # filed manual (rates / factors / filing id)
    factors: Any  # extract_life_factors result
    medical: LifeMedicalDecision
    financial: LifeFinancialResult
    reinsurance: Any
    age: int
    sex_key: str  # "male" / "female" after unisex-state override
    unisex_forced: bool = False  # True when a unisex state (MT) forced one sex table
    face: float = 0.0
    modal: str = "annual"
    modal_f: float = 1.0

    @property
    def issue_state(self) -> str:
        return (self.state_code or getattr(self.factors, "state", "") or "").upper()[:2]

    @property
    def filing_state(self) -> str:
        return str((self.manual or {}).get("state_of_filing") or "IL").upper()

    @property
    def smoker(self) -> bool:
        return bool(self.medical.tobacco)


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
    ctx: LifeProductContext,
    default_rules: dict[str, Any],
    state_rules: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Merge DEFAULT_STATE_RULES with STATE_RULES[issue_state].

    Returns a flat dict with ``issue_state`` and ``source`` stamped so every
    decision record shows exactly which state rules fired.
    """
    merged = dict(default_rules or {})
    from insureflow.life.lobs.state_law import canonical_state_row

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
    ctx: LifeProductContext,
    outcome: LobOutcome,
    *,
    filed_for_state: bool,
    product_family: str,
) -> None:
    """State-of-filing gate — mirrors the platform-wide rule inside this path.

    A quote priced on another state's exhibit is never presented as issueable:
    when the selected state has no filed rates for this family the path marks
    the quote ineligible with an explicit reason on the record.
    """
    issue = ctx.issue_state
    filing = ctx.filing_state
    if not filed_for_state:
        outcome.eligible = False
        outcome.add_reason(f"{product_family.replace('_', ' ')} has no {filing}-filed rates — illustrative only, not an issueable premium")
    elif issue and issue != filing:
        outcome.add_reason(f"{filing} pilot exhibit applied — not a {issue} state-of-issue filing")
        if issue not in ((ctx.manual or {}).get("state_relativities") or {}):
            outcome.eligible = False


def finish_quote(
    ctx: LifeProductContext,
    outcome: LobOutcome,
    *,
    logic_path: str,
    family: str,
    rating_engine: str | None = None,
    extra_meta: dict[str, Any] | None = None,
    apply_minimum_premium: bool = True,
) -> QuoteResult:
    """Convert a LobOutcome into the platform QuoteResult contract."""
    manual = ctx.manual or {}
    minimum_premium = float(manual.get("minimum_premium", 250.0))
    annual_value = outcome.annual_premium
    if apply_minimum_premium:
        annual_value = max(annual_value, minimum_premium)
    adjusted = round(max(annual_value, 0.0), 2)
    modal_premium = round(adjusted * ctx.modal_f, 2) if ctx.modal != "annual" else adjusted

    meta: dict[str, Any] = {
        "filing_id": manual.get("filing_id"),
        "product": outcome.product_label,
        "product_id": ctx.product_id,
        "life_coverage_id": ctx.coverage_id,
        "coverage_id": ctx.coverage_id,
        "product_family": family,
        "lob_logic_path": logic_path,
        "modal": ctx.modal,
        "modal_premium": modal_premium,
        "issue_state": ctx.issue_state,
        "state_of_filing": ctx.filing_state,
        "serff_tracking": manual.get("serff_tracking"),
        "rating_engine": rating_engine or ("life_filing" if family == "term" else "life_whole_life_actuarial"),
        "face_amount": ctx.face,
        "medical": ctx.medical.to_metadata(),
        "financial": ctx.financial.to_metadata(),
        "life_reinsurance": ctx.reinsurance.to_metadata(),
        "facultative_required": ctx.reinsurance.facultative_required,
        "personal_factors": {k: v for k, v in vars(ctx.factors).items() if k != "findings"},
        "tiv": ctx.face,
        "insurance_line": InsuranceLine.LIFE.value,
        "personal_lines": True,
        "uw_decision_hint": ctx.medical.decision.value,
        "outcome": outcome.metadata.pop("_outcome", "accept"),
        "conditions": [],
        **(extra_meta or {}),
        **outcome.metadata,
    }
    meta["conditions"] = list(outcome.conditions)

    ineligibility = [r for r in outcome.reasons if r] if not outcome.eligible else []
    return QuoteResult(
        bundle_id=ctx.bundle.bundle_id,
        line=InsuranceLine.LIFE,
        base_premium=round(outcome.base_premium, 2),
        adjusted_premium=adjusted,
        schedule_modifications=list(outcome.components),
        rate_per_100_tiv=round(adjusted / (ctx.face / 100.0), 4) if ctx.face else 0.0,
        eligible=outcome.eligible,
        ineligibility_reasons=ineligibility,
        metadata=meta,
    )


def medical_class_factor(ctx: LifeProductContext, cap: float | None = None) -> float:
    """Underwriting-class factor from the manual, optionally capped."""
    class_factors = (ctx.manual or {}).get("underwriting_class_factors") or {}
    factor = float(class_factors.get(ctx.medical.underwriting_class, class_factors.get("standard", 1.0)))
    if cap is not None:
        factor = min(factor, cap)
    return factor


def band_factor(ctx: LifeProductContext) -> float:
    band_f = 1.0
    for band in sorted((ctx.manual or {}).get("band_discounts") or [], key=lambda b: float(b.get("min_face") or 0)):
        if ctx.face >= float(band.get("min_face") or 0):
            band_f = float(band.get("factor", 1.0))
    return band_f


def state_relativity(ctx: LifeProductContext) -> float:
    return float(((ctx.manual or {}).get("state_relativities") or {}).get(ctx.issue_state) or 1.0)


def policy_fee(ctx: LifeProductContext) -> float:
    return float((ctx.manual or {}).get("policy_fee", 60.0))


def stack_shape_ratio(
    ctx: LifeProductContext,
    variant_premium: float,
    term_years: int,
    interest_rate: float = 0.04,
) -> float:
    """Benefit-shape ratio of a variant quote vs straight level term.

    The actuarial stack (life/term_formulas) and the filed manual use different
    mortality scales, so a variant's absolute premium can't be priced against
    the manual directly. This returns PV(shape) / PV(level) computed INSIDE one
    stack; callers apply it to the manual-based level premium so the filed
    economics hold while the benefit structure comes from the formulas.
    """
    from insureflow.life.term_formulas import level_net_premium as stack_level_rate

    rate = stack_level_rate(ctx.age, term_years, ctx.sex_key, ctx.smoker, interest_rate)
    stack_level_dollars = rate * ctx.face
    if stack_level_dollars <= 0:
        return 1.0
    return variant_premium / stack_level_dollars


def add_common_loads(ctx: LifeProductContext, premium: float) -> float:
    """Flat extras + rider loads + policy fee, identical across paths."""
    loaded = premium
    loaded += (ctx.face / 1000.0) * ctx.medical.flat_extras_per_1000
    loaded += (ctx.face / 1000.0) * ctx.financial.rider_load_per_1000
    return loaded + policy_fee(ctx)


def purchase_price(ctx: LifeProductContext) -> float:
    """Consideration for payout products (annuities): face → parsed principal → default.

    Annuity buyers state a "purchase price"/"principal", not a "face amount";
    this keeps every annuity path reading the same consideration consistently.
    """
    import re

    from insureflow.underwriting.personal_lines import _blob

    if ctx.face > 0:
        return float(ctx.face)
    blob = _blob(ctx.bundle)
    match = re.search(r"(?:principal|consideration|purchase price|premium)\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)", blob, re.I)
    if match:
        return float(match.group(1).replace(",", ""))
    income = getattr(ctx.factors, "income", 0.0) or 0.0
    return round(income * 10.0, 2) if income else 500_000.0


HandlerFn = Callable[[LifeProductContext], LobOutcome]
