"""Ratemaking — Chapter 5: Pricing Insurance Products.

The chapter describes ratemaking as the process of turning past loss statistics
into future rates. Rates must be adequate, not excessive, and not unfairly
discriminatory, and should ideally be stable, responsive, provide for
contingencies, promote loss control, and be simple. Ratemaking is the
responsibility of actuaries, who may be supported by advisory organizations
(ISO, AAIS, NCCI, Surety Association of America) supplying prospective loss
costs.

The base-rate process has three steps:
  1. Calculate the amount needed to pay future claims (the pure premium).
  2. Calculate the amount needed to pay future expenses (the expense loading).
  3. Add (1) and (2) to determine the rate; then load for contingencies and
     profit to reach the gross rate.

Three methods are examined: the pure premium method, the loss ratio method,
and the judgment method. This module makes the process, the terms, the three
methods, the statutory goals, the five rate characteristics, and the advisory
organizations structured, runnable checks so the automation can price like an
actuary.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.rating.models import InsuranceLine

# ── Ratemaking responsibility: advisory organizations ─────────────────────


class AdvisoryOrganization(str, Enum):
    """The four principal advisory organizations plus independent filings."""

    ISO = "ISO"
    AAIS = "AAIS"
    NCCI = "NCCI"
    SURETY = "Surety Association of America"
    INDEPENDENT = "independent"


class AdvisoryLossCost(BaseModel):
    """A prospective loss cost supplied by an advisory organization."""

    organization: AdvisoryOrganization
    line: str
    loss_cost_per_exposure: float
    exposure_basis: str = "per $100 of exposure"
    note: str = ""


_ADVISORY_LOSS_COSTS: list[dict[str, Any]] = [
    {
        "organization": AdvisoryOrganization.ISO,
        "line": "commercial_property",
        "loss_cost_per_exposure": 0.28,
        "exposure_basis": "per $100 of TIV",
        "note": "Insurance Services Office — loss costs for most commercial P&C lines; carriers add their own expense factors",
    },
    {
        "organization": AdvisoryOrganization.ISO,
        "line": "general_liability",
        "loss_cost_per_exposure": 0.08,
        "exposure_basis": "per $100 of TIV",
        "note": "Insurance Services Office — liability loss costs",
    },
    {
        "organization": AdvisoryOrganization.AAIS,
        "line": "business_owners_policy",
        "loss_cost_per_exposure": 0.32,
        "exposure_basis": "per $100 of TIV",
        "note": "American Association of Insurance Services — alternative BOP loss costs",
    },
    {
        "organization": AdvisoryOrganization.NCCI,
        "line": "workers_comp",
        "loss_cost_per_exposure": 0.05,
        "exposure_basis": "per $100 of payroll",
        "note": "National Council on Compensation Insurance — workers compensation loss costs",
    },
    {
        "organization": AdvisoryOrganization.SURETY,
        "line": "surety",
        "loss_cost_per_exposure": 0.04,
        "exposure_basis": "per $100 of bond",
        "note": "Surety Association of America — surety bond loss costs",
    },
]


def advisory_loss_costs(organization: AdvisoryOrganization) -> list[AdvisoryLossCost]:
    """Return the loss costs a given advisory organization supplies."""
    return [AdvisoryLossCost(**row) for row in _ADVISORY_LOSS_COSTS if row["organization"] is organization]


# ── Step 1–3: the base-rate build-up (pure premium method) ────────────────


class RatemakingStep(BaseModel):
    step: int
    label: str
    amount: float
    detail: str = ""


class RatemakingResult(BaseModel):
    """The three-step build-up of a base rate and gross rate per exposure unit."""

    pure_premium: float = 0.0
    total_expenses: float = 0.0
    expense_loading: float = 0.0
    base_rate: float = 0.0
    contingency_loading: float = 0.0
    profit_loading: float = 0.0
    gross_rate: float = 0.0
    earned_exposure_units: float = 0.0
    steps: list[RatemakingStep] = Field(default_factory=list)
    detail: str = ""


def pure_premium_method(
    incurred_losses: float,
    exposure_units: float,
    *,
    lae: float = 0.0,
    acquisition: float = 0.0,
    general_admin: float = 0.0,
    premium_taxes: float = 0.0,
    contingency_pct: float = 0.0,
    profit_pct: float = 0.0,
    loss_adjustment_in_pure_premium: bool = True,
) -> RatemakingResult:
    """Base rate = pure premium + expense loading (the three-step process).

    Step 1: pure premium = incurred losses / earned exposure units.
    Step 2: expense loading = total expenses / exposure units.
    Step 3: base rate = pure premium + expense loading; then load for
    contingencies and profit to get the gross rate.

    When ``loss_adjustment_in_pure_premium`` is true (the textbook's default),
    loss adjustment expenses ride in the pure premium; otherwise they are part
    of the expense loading.
    """
    if exposure_units <= 0:
        raise ValueError("earned exposure units must be positive")

    lae_effective = 0.0 if loss_adjustment_in_pure_premium else lae
    pure_premium = round(incurred_losses / exposure_units, 2)

    total_expenses = lae_effective + acquisition + general_admin + premium_taxes
    expense_loading = round(total_expenses / exposure_units, 2)

    base_rate = round(pure_premium + expense_loading, 2)
    contingency_loading = round(base_rate * contingency_pct / 100.0, 2)
    profit_loading = round(base_rate * profit_pct / 100.0, 2)
    gross_rate = round(base_rate + contingency_loading + profit_loading, 2)

    steps = [
        RatemakingStep(
            step=1,
            label="Amount needed to pay future claims (pure premium)",
            amount=pure_premium,
            detail=f"${incurred_losses:,.0f} incurred / {exposure_units:,.0f} earned exposure units",
        ),
        RatemakingStep(
            step=2,
            label="Amount needed to pay future expenses (expense loading)",
            amount=expense_loading,
            detail=f"${total_expenses:,.0f} expenses / {exposure_units:,.0f} exposure units",
        ),
        RatemakingStep(
            step=3,
            label="Base rate (pure premium + expense loading)",
            amount=base_rate,
            detail=f"${pure_premium:,.2f} + ${expense_loading:,.2f}; loaded ${contingency_loading:,.2f} contingencies + ${profit_loading:,.2f} profit",
        ),
    ]

    return RatemakingResult(
        pure_premium=pure_premium,
        total_expenses=round(total_expenses, 2),
        expense_loading=expense_loading,
        base_rate=base_rate,
        contingency_loading=contingency_loading,
        profit_loading=profit_loading,
        gross_rate=gross_rate,
        earned_exposure_units=exposure_units,
        steps=steps,
        detail=(f"Pure premium ${pure_premium:,.2f} + expense loading ${expense_loading:,.2f} = base rate ${base_rate:,.2f}; gross rate ${gross_rate:,.2f} per exposure unit"),
    )


# ── Ratemaking factors ─────────────────────────────────────────────────────


class RateFactorAssessment(BaseModel):
    """A factor that affects ratemaking (reserves, data delays, investment income, etc.)."""

    factor: str
    severity: RiskSeverity = RiskSeverity.LOW
    detail: str = ""


_FACTOR_DEFAULTS: list[tuple[str, RiskSeverity, str]] = [
    ("Loss reserve estimation", RiskSeverity.LOW, "Case reserves must be kept current; reserve adequacy is reviewed separately"),
    ("Delays in data collection and use", RiskSeverity.MODERATE, "Past statistics can only show what has happened; trend and loss development must project to the future"),
    ("Investment income", RiskSeverity.LOW, "Investment earnings may offset some of the cost of funds"),
    ("Policy limits", RiskSeverity.LOW, "Higher limits concentrate exposure and require higher rates per exposure unit"),
    ("Deductible level", RiskSeverity.LOW, "Higher deductibles remove small claims from the loss cost"),
    ("Vehicle type / driving record", RiskSeverity.MODERATE, "Personal auto relativities vary by symbol, use, territory, and record"),
    ("Geographic area", RiskSeverity.MODERATE, "Territory relativities adjust the base rate for location loss costs"),
]


def ratemaking_factors() -> list[RateFactorAssessment]:
    """The factors that affect ratemaking once the base rate is established."""
    return [RateFactorAssessment(factor=f, severity=s, detail=d) for f, s, d in _FACTOR_DEFAULTS]


# ── Loss ratio method ──────────────────────────────────────────────────────


class LossRatioMethodResult(BaseModel):
    current_rate: float = 0.0
    actual_loss_ratio: float = 0.0
    trend_factor: float = 1.0
    loss_development_factor: float = 1.0
    projected_loss_ratio: float = 0.0
    permissible_loss_ratio: float = 0.0
    rate_change_pct: float = 0.0
    indicated_rate: float = 0.0
    detail: str = ""


def loss_ratio_method(
    current_rate: float,
    actual_loss_ratio: float,
    permissible_loss_ratio: float,
    *,
    trend_factor: float = 1.0,
    loss_development_factor: float = 1.0,
) -> LossRatioMethodResult:
    """Indicated rate change from the loss ratio method.

    The projected loss ratio (actual loss ratio adjusted for trend and loss
    development) is compared with the permissible loss ratio (the loss ratio
    that leaves room for expenses, profit, and contingencies).
    """
    if permissible_loss_ratio <= 0:
        raise ValueError("permissible loss ratio must be positive")

    projected = actual_loss_ratio * trend_factor * loss_development_factor
    rate_change = (projected / permissible_loss_ratio - 1.0) * 100.0
    indicated = current_rate * (1.0 + rate_change / 100.0)

    return LossRatioMethodResult(
        current_rate=round(current_rate, 4),
        actual_loss_ratio=round(actual_loss_ratio, 4),
        trend_factor=round(trend_factor, 4),
        loss_development_factor=round(loss_development_factor, 4),
        projected_loss_ratio=round(projected, 4),
        permissible_loss_ratio=round(permissible_loss_ratio, 4),
        rate_change_pct=round(rate_change, 2),
        indicated_rate=round(indicated, 4),
        detail=(f"Projected loss ratio {projected:.2f} vs permissible {permissible_loss_ratio:.2f} → {rate_change:+.1f}% rate change; indicated rate {indicated:,.2f}"),
    )


# ── Judgment method ────────────────────────────────────────────────────────


class JudgmentAdjustment(BaseModel):
    factor: str
    pct: float
    rationale: str = ""


class JudgmentRateResult(BaseModel):
    base_rate: float = 0.0
    adjustments: list[JudgmentAdjustment] = Field(default_factory=list)
    judgment_rate: float = 0.0
    detail: str = ""


def judgment_method(base_rate: float, adjustments: list[JudgmentAdjustment]) -> JudgmentRateResult:
    """The judgment method applies professional judgment to a base rate.

    Used when statistics are insufficient or too unstable for the pure premium
    or loss ratio methods. Adjustments compound multiplicatively.
    """
    rate = base_rate
    for adj in adjustments:
        rate *= 1.0 + adj.pct / 100.0
    return JudgmentRateResult(
        base_rate=round(base_rate, 4),
        adjustments=list(adjustments),
        judgment_rate=round(rate, 4),
        detail=(f"Judgment rate {rate:,.2f} from base {base_rate:,.2f} across {len(adjustments)} judgment adjustment(s)"),
    )


# ── Regulatory goals ───────────────────────────────────────────────────────


class RegulatoryGoal(str, Enum):
    ADEQUATE = "adequate"
    NOT_EXCESSIVE = "not_excessive"
    NOT_UNFAIRLY_DISCRIMINATORY = "not_unfairly_discriminatory"


class RegulatoryAssessment(BaseModel):
    goal: RegulatoryGoal
    status: str  # pass / flag / fail
    detail: str = ""


def regulatory_review(
    result: RatemakingResult,
    *,
    max_allowable_markup: float = 2.5,
    max_class_relativity: float = 5.0,
    uses_prohibited_basis: bool = False,
) -> list[RegulatoryAssessment]:
    """Statutory goals: adequate, not excessive, not unfairly discriminatory."""
    assessments: list[RegulatoryAssessment] = []

    covers_cost = result.gross_rate >= result.pure_premium + result.expense_loading - 0.005
    assessments.append(
        RegulatoryAssessment(
            goal=RegulatoryGoal.ADEQUATE,
            status="pass" if covers_cost else "fail",
            detail=(f"Gross rate ${result.gross_rate:,.2f} covers pure premium ${result.pure_premium:,.2f} + expenses ${result.expense_loading:,.2f}")
            if covers_cost
            else "Rate does not cover projected losses and expenses",
        )
    )

    markup = result.gross_rate / result.pure_premium if result.pure_premium > 0 else 0.0
    excessive = result.pure_premium > 0 and markup > max_allowable_markup
    assessments.append(
        RegulatoryAssessment(
            goal=RegulatoryGoal.NOT_EXCESSIVE,
            status="fail" if excessive else "pass",
            detail=(f"Markup {markup:.2f}x exceeds allowable {max_allowable_markup:.2f}x" if excessive else f"Markup {markup:.2f}x within allowable {max_allowable_markup:.2f}x"),
        )
    )

    discriminatory = uses_prohibited_basis or max_class_relativity < 1.0 or max_class_relativity > 10.0
    assessments.append(
        RegulatoryAssessment(
            goal=RegulatoryGoal.NOT_UNFAIRLY_DISCRIMINATORY,
            status="fail" if discriminatory else "pass",
            detail=(
                "Classification relativities exceed a defensible band or embed a prohibited basis"
                if discriminatory
                else f"Class relativities within a {max_class_relativity:.1f}x band; no prohibited basis used"
            ),
        )
    )

    return assessments


# ── The five rate characteristics ──────────────────────────────────────────


class RateCharacteristic(str, Enum):
    STABLE = "stable"
    RESPONSIVE = "responsive"
    PROVIDES_FOR_CONTINGENCIES = "provides_for_contingencies"
    PROMOTES_LOSS_CONTROL = "promotes_loss_control"
    SIMPLE = "simple"


class CharacteristicAssessment(BaseModel):
    characteristic: RateCharacteristic
    status: str  # pass / flag
    detail: str = ""


def rate_characteristics_review(
    result: RatemakingResult,
    *,
    rate_change_pct: float = 0.0,
    data_lag_years: float = 1.0,
    has_loss_control_credits: bool = True,
    component_count: Optional[int] = None,
) -> list[CharacteristicAssessment]:
    """The five ideal rate characteristics (compromises are often necessary)."""
    assessments: list[CharacteristicAssessment] = []

    stable = abs(rate_change_pct) <= 15.0
    assessments.append(
        CharacteristicAssessment(
            characteristic=RateCharacteristic.STABLE,
            status="pass" if stable else "flag",
            detail=f"Proposed rate change {rate_change_pct:+.1f}% within the ±15% stability band" if stable else f"Proposed rate change {rate_change_pct:+.1f}% exceeds the ±15% stability band",
        )
    )

    responsive = data_lag_years <= 2.0
    assessments.append(
        CharacteristicAssessment(
            characteristic=RateCharacteristic.RESPONSIVE,
            status="pass" if responsive else "flag",
            detail=f"Data lag {data_lag_years:.1f} years — rates update promptly to reflect external factors"
            if responsive
            else f"Data lag {data_lag_years:.1f} years — rates respond slowly to change",
        )
    )

    assessments.append(
        CharacteristicAssessment(
            characteristic=RateCharacteristic.PROVIDES_FOR_CONTINGENCIES,
            status="pass" if result.contingency_loading > 0 else "flag",
            detail=f"Contingency loading ${result.contingency_loading:,.2f} protects against unexpected loss/expense variation"
            if result.contingency_loading > 0
            else "No contingency loading — unexpected variation is unprotected",
        )
    )

    assessments.append(
        CharacteristicAssessment(
            characteristic=RateCharacteristic.PROMOTES_LOSS_CONTROL,
            status="pass" if has_loss_control_credits else "flag",
            detail="Loss-control credits (deductible, protective devices) reward sound risk management" if has_loss_control_credits else "No loss-control credits offered",
        )
    )

    count = component_count if component_count is not None else len(result.steps) + 2
    simple = count <= 8
    assessments.append(
        CharacteristicAssessment(
            characteristic=RateCharacteristic.SIMPLE,
            status="pass" if simple else "flag",
            detail=f"Rate built from {count} components — simple enough for producers and policyholders" if simple else f"Rate built from {count} components — risk of becoming too complex",
        )
    )

    return assessments


# ── Per-line rate build-ups from the rating engine ─────────────────────────


def line_rate_build_ups(*, contingency_pct: float = 5.0, profit_pct: float = 5.0) -> list[RatemakingResult]:
    """A base-rate build-up per line using the engine's loss costs and LCM.

    Uses the ISO-style loss cost as the pure premium (step 1) and derives the
    expense loading from the carrier's loss cost multiplier (step 2), which
    bundles expenses and profit, plus an explicit contingency loading.
    """
    from insureflow.rating.engine import ISO_LOSS_COSTS, LCM

    build_ups: list[RatemakingResult] = []
    for line in InsuranceLine:
        loss_cost = ISO_LOSS_COSTS.get(line, 0.0)
        lcm = LCM.get(line, 2.0)
        pure = loss_cost
        expense_loading = round(loss_cost * (lcm - 1.0), 4)
        base = round(pure + expense_loading, 4)
        contingency = round(base * contingency_pct / 100.0, 4)
        profit = round(base * profit_pct / 100.0, 4)
        gross = round(base + contingency + profit, 4)
        build_ups.append(
            RatemakingResult(
                pure_premium=pure,
                total_expenses=expense_loading,
                expense_loading=expense_loading,
                base_rate=base,
                contingency_loading=contingency,
                profit_loading=profit,
                gross_rate=gross,
                earned_exposure_units=100.0,
                steps=[
                    RatemakingStep(step=1, label="Loss cost (pure premium)", amount=pure),
                    RatemakingStep(step=2, label="Expense loading from LCM", amount=expense_loading),
                    RatemakingStep(step=3, label="Base rate", amount=base),
                ],
                detail=f"{line.value}: base ${base:.4f} → gross ${gross:.4f} per $100 of exposure",
            )
        )
    return build_ups


# ── Aggregate study ────────────────────────────────────────────────────────


class RatemakingStudy(BaseModel):
    line: str = ""
    exposure_units: float = 0.0
    pure_premium_result: Optional[RatemakingResult] = None
    loss_ratio_result: Optional[LossRatioMethodResult] = None
    judgment_result: Optional[JudgmentRateResult] = None
    regulatory: list[RegulatoryAssessment] = Field(default_factory=list)
    characteristics: list[CharacteristicAssessment] = Field(default_factory=list)
    factors: list[RateFactorAssessment] = Field(default_factory=list)
    advisory_orgs: list[str] = Field(default_factory=list)
    worst_severity: RiskSeverity = RiskSeverity.LOW
    summary: str = ""


def run_ratemaking_study(
    *,
    line: InsuranceLine = InsuranceLine.COMMERCIAL_PROPERTY,
    incurred_losses: float = 10_000_000.0,
    exposure_units: float = 100_000.0,
    lae: float = 0.0,
    acquisition: float = 0.0,
    general_admin: float = 0.0,
    premium_taxes: float = 0.0,
    contingency_pct: float = 5.0,
    profit_pct: float = 5.0,
    current_rate: float = 0.0,
    actual_loss_ratio: float = 0.60,
    permissible_loss_ratio: float = 0.65,
    trend_factor: float = 1.03,
    loss_development_factor: float = 1.05,
) -> RatemakingStudy:
    """Run the three ratemaking methods plus the statutory and quality reviews."""
    pure = pure_premium_method(
        incurred_losses,
        exposure_units,
        lae=lae,
        acquisition=acquisition,
        general_admin=general_admin,
        premium_taxes=premium_taxes,
        contingency_pct=contingency_pct,
        profit_pct=profit_pct,
    )

    base_rate = current_rate if current_rate > 0 else pure.base_rate
    lr = loss_ratio_method(
        base_rate,
        actual_loss_ratio,
        permissible_loss_ratio,
        trend_factor=trend_factor,
        loss_development_factor=loss_development_factor,
    )

    judgment = judgment_method(
        base_rate,
        [
            JudgmentAdjustment(factor="Market position", pct=0.0, rationale="Judgment offset for competitive positioning"),
            JudgmentAdjustment(factor="Loss control features", pct=-5.0, rationale="Credit for protective devices / loss control"),
        ],
    )

    regulatory = regulatory_review(pure)
    characteristics = rate_characteristics_review(
        pure,
        rate_change_pct=lr.rate_change_pct,
        data_lag_years=1.5,
        has_loss_control_credits=True,
        component_count=8,
    )

    severities = [a.severity for a in ratemaking_factors()]
    worst = max(severities, key=lambda s: s.value) if severities else RiskSeverity.LOW
    regulatory_failed = any(a.status == "fail" for a in regulatory)
    if regulatory_failed and worst.value < RiskSeverity.HIGH.value:
        worst = RiskSeverity.HIGH
    characteristic_flagged = any(a.status == "flag" for a in characteristics)
    if characteristic_flagged and worst.value < RiskSeverity.MODERATE.value:
        worst = RiskSeverity.MODERATE

    return RatemakingStudy(
        line=line.value,
        exposure_units=exposure_units,
        pure_premium_result=pure,
        loss_ratio_result=lr,
        judgment_result=judgment,
        regulatory=regulatory,
        characteristics=characteristics,
        factors=ratemaking_factors(),
        advisory_orgs=[org.value for org in AdvisoryOrganization if org is not AdvisoryOrganization.INDEPENDENT],
        worst_severity=worst,
        summary=f"{line.value}: pure premium ${pure.pure_premium:,.2f}, base rate ${pure.base_rate:,.2f}, gross rate ${pure.gross_rate:,.2f}; loss-ratio method {lr.rate_change_pct:+.1f}%",
    )
