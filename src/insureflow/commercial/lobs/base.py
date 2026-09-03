"""Shared plumbing for dedicated Commercial LOB logic paths.

Mirrors ``insureflow.life.lobs.base`` / ``insureflow.health.lobs.base``:
this module holds ONLY data plumbing (context, outcome, QuoteResult
conversion) and tiny shared helpers. Underwriting rules, exposure sizing,
and pricing math stay owned by each product module (which reuses the
existing, already-tested actuarial engines — NCCI WC tables, specialty
loss-cost tables, COPE/ISO — rather than re-deriving them), and state law
is applied INSIDE each path via ``insureflow.commercial.lobs.state_law``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent


@dataclass
class CommercialProductContext:
    """Everything a commercial product-level logic path needs to decide."""

    bundle: SubmissionBundle
    memo: UnderwritingMemo
    line: InsuranceLine
    state_code: str  # explicit issue state from the selector/blob ("" if none)
    product_id: str
    coverage_id: str = ""
    coverage_name: str = ""
    schedule_mod_pct: float = 0.0
    market_mod_pct: float = 0.0
    experience_mod: float | None = None

    @property
    def issue_state(self) -> str:
        return (self.state_code or "").upper()[:2]


@dataclass
class LobOutcome:
    """Result of one product logic path before QuoteResult conversion."""

    product_label: str = ""
    base_premium: float = 0.0
    adjusted_premium: float = 0.0
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
    ctx: CommercialProductContext,
    default_rules: dict[str, Any],
    state_rules: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Merge DEFAULT_STATE_RULES with STATE_RULES[issue_state].

    Stamps ``issue_state``/``source`` so every decision record shows exactly
    which state rules fired — same contract as the life/health equivalent.
    """
    merged = dict(default_rules or {})
    state_row = (state_rules or {}).get(ctx.issue_state) or {}
    merged.update(state_row)
    merged["issue_state"] = ctx.issue_state
    merged["source"] = "state_table" if state_row else "carrier_default"
    return merged


def surplus_lines_tax(ctx: CommercialProductContext, taxable_premium: float) -> dict[str, Any] | None:
    """Non-admitted surplus-lines premium tax for this issue state.

    Trade Credit and E&O are predominantly placed non-admitted; this is a
    genuine per-state cost, not decoration. Returns None when there's no
    taxable premium to compute against.
    """
    from insureflow.commercial.lobs.state_law import SURPLUS_LINES_TAX, SURPLUS_LINES_TAX_DEFAULT

    if taxable_premium <= 0:
        return None
    rate = SURPLUS_LINES_TAX.get(ctx.issue_state, SURPLUS_LINES_TAX_DEFAULT)
    return {
        "state": ctx.issue_state or "(unresolved — default rate applied)",
        "rate": rate,
        "amount": round(taxable_premium * rate, 2),
        "insurer_paid": False,
        "basis": "non_admitted_surplus_lines",
    }


def add_common_life_loads(manual: dict[str, Any], premium: float, face: float) -> float:
    """Flat policy fee load — the mortality-based Key Person path's analogue
    of ``insureflow.life.lobs.base.add_common_loads`` (minus flat-extra/rider
    loads, which don't apply to a simplified-issue employer-owned policy)."""
    return premium + float(manual.get("policy_fee", 60.0))


def ilf_power_curve(limit: float, basic_limit: float, b: float = 0.25) -> float:
    """Increased Limits Factor via the standard power-curve ("Riebesell")
    technique used industry-wide for excess/increased-limit liability
    pricing: ILF(L) = (L / L_basic) ** b. b in [0.20, 0.30] is the typical
    liability range (0.25 used here as the illustrative midpoint — verify
    against a real filed ILF exhibit before production use). Unlike a flat
    per-dollar rate, this correctly prices diminishing marginal rate per
    dollar of limit as the limit grows, and rises faster than linearly
    below the basic limit.
    """
    if basic_limit <= 0 or limit <= 0:
        return 1.0
    return float((limit / basic_limit) ** b)


def price_limit_driven_specialty(ctx: CommercialProductContext, line: InsuranceLine) -> tuple[float, float, list[RateComponent], dict[str, Any]]:
    """Real ILF-curve pricing for a limit-driven specialty line (D&O, E&O).

    Replaces the flat "exposure/100 x loss_cost x LCM" linear proxy
    (``insureflow.rating.commercial_specialty.rate_specialty_line``) with
    the actual per-limit rate implied by ``ilf_power_curve`` — the base
    layer rate is charged AT the line's basic limit, and the increased
    limits factor scales it up/down from there, so pricing continuously
    matches the pre-existing flat rate exactly at the basic limit while
    correctly pricing sub-linearly above it.

    Returns (base_premium, adjusted_premium, components, exposure_meta).
    """
    from insureflow.rating.commercial_specialty import _DEFAULT_EXPOSURE, SPECIALTY_LCM, SPECIALTY_LOSS_COSTS, SPECIALTY_MINIMUMS, estimate_specialty_exposure

    exposure, basis, used_default = estimate_specialty_exposure(ctx.bundle, line)
    basic_limit = _DEFAULT_EXPOSURE.get(line, 1_000_000.0)
    loss_cost = SPECIALTY_LOSS_COSTS.get(line, 0.40)
    lcm = SPECIALTY_LCM.get(line, 2.2)
    min_prem = SPECIALTY_MINIMUMS.get(line, 1_000.0)

    base_layer_premium = (basic_limit / 100.0) * loss_cost * lcm
    ilf = ilf_power_curve(exposure, basic_limit)
    base = base_layer_premium * ilf

    adjusted = base * (1 + ctx.market_mod_pct / 100.0) * (1 + ctx.schedule_mod_pct / 100.0)
    adjusted = max(round(adjusted + 75.0, 2), min_prem)

    components = [
        RateComponent(name="basic_limit_loss_cost", amount=loss_cost, basis=f"per_100_at_{basic_limit:,.0f}_basic_limit"),
        RateComponent(name="loss_cost_multiplier", amount=lcm, basis="expense_profit"),
        RateComponent(name="increased_limits_factor", amount=round(ilf, 4), basis=f"limit_{exposure:,.0f}_vs_basic_{basic_limit:,.0f}"),
        RateComponent(name="exposure", amount=exposure, basis=basis),
    ]
    if ctx.market_mod_pct:
        components.append(RateComponent(name="market_cycle_adjustment", amount=ctx.market_mod_pct, basis="market", modifier_pct=ctx.market_mod_pct))
    if ctx.schedule_mod_pct:
        components.append(RateComponent(name="uw_schedule_modification", amount=0, basis="uw_discretion", modifier_pct=ctx.schedule_mod_pct))

    meta: dict[str, Any] = {
        "exposure": exposure,
        "exposure_basis": basis,
        "used_default_exposure": used_default,
        "basic_limit": basic_limit,
        "ilf": round(ilf, 4),
        "rating_engine": "ilf_power_curve",
    }
    return round(base, 2), adjusted, components, meta


def finish_quote(
    ctx: CommercialProductContext,
    outcome: LobOutcome,
    *,
    logic_path: str,
    family: str,
    exposure: float = 0.0,
    exposure_basis: str = "",
    extra_meta: dict[str, Any] | None = None,
) -> QuoteResult:
    """Convert a LobOutcome into the platform QuoteResult contract."""
    adjusted = round(max(outcome.adjusted_premium, 0.0), 2)
    base = round(max(outcome.base_premium, 0.0), 2)
    if not outcome.eligible:
        adjusted = 0.0
        base = 0.0

    meta: dict[str, Any] = {
        "product": outcome.product_label,
        "product_id": ctx.product_id,
        "coverage_id": ctx.coverage_id,
        "product_family": family,
        "lob_logic_path": logic_path,
        "issue_state": ctx.issue_state,
        "insurance_line": ctx.line.value,
        "personal_lines": False,
        "exposure": exposure,
        "exposure_basis": exposure_basis,
        "tiv": exposure,
        "conditions": [],
        **(extra_meta or {}),
        **outcome.metadata,
    }
    meta["conditions"] = list(outcome.conditions)

    ineligibility = list(outcome.reasons) if not outcome.eligible else []
    rate_per_100 = round(adjusted / (exposure / 100.0), 4) if exposure and outcome.eligible else 0.0
    return QuoteResult(
        bundle_id=ctx.bundle.bundle_id,
        line=ctx.line,
        base_premium=base,
        adjusted_premium=adjusted,
        schedule_modifications=list(outcome.components),
        rate_per_100_tiv=rate_per_100,
        eligible=outcome.eligible,
        ineligibility_reasons=ineligibility,
        metadata=meta,
    )
