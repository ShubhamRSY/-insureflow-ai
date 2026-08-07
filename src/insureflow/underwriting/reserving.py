"""Loss reserving standards — Casualty Actuarial Society (CAS).

Chapter: Loss Reserving Standards. A set of standards must be observed by
licensed actuaries when conducting actuarial studies. This module turns those
standards into structured checks and estimators the automation can run against
a book of claims:

* Data organization — every claim must be keyed to accident, report, and
  valuation dates (all now fields on ``ClaimRecord``).
* Data availability — enough data, in enough detail, to assess reserves.
* Emergence patterns — the delay between occurrence and reporting.
* Settlement patterns — how long reported claims take to settle.
* Development patterns — consistency in settlement and reserving.
* Frequency and severity — high frequency with low average severity makes
  reserve estimates more reliable.
* Reopened claims potential — closed claims reopen, varying by line and claims
  practice.
* Operational changes — changes in systems, accounting, claims handling, or
  underwriting can distort loss experience.
* Reasonableness — the loss estimate should be compared with an independent
  measure (premium, exposure, claim counts).
* Multiple reserving methods — an actuary looks at more than one method and
  establishes a range; case reserves must be kept current.

The module implements two simple reserving methods (a paid/incurred-based
development method and a loss-ratio / Bornhuetter-Ferguson style method) and
reports both plus a range, mirroring the standard practice of triangulating
independent estimates.
"""

from __future__ import annotations

import statistics
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import ClaimRecord, SubmissionBundle

_SMALL_CLAIM_SEVERITY = 10_000.0  # below this, claims count as "low average size"

# Operational-change markers that distort the continuity of loss experience.
_OPERATIONAL_CHANGE_MARKERS = (
    "system conversion",
    "new claims system",
    "claims system upgrade",
    "accounting system change",
    "claims handling change",
    "new claims handling procedure",
    "underwriting guideline change",
    "underwriting procedure change",
    "portfolio acquisition",
    "reinsurance change",
    "program change",
    "policy form change",
    "deductible change",
    "legacy system migration",
    "data migration",
)

# Reopened-claims potential by line of business: workers comp / GL are prone,
# short-tail property far less so.
_REOPENED_POTENTIAL: dict[str, float] = {
    "workers_comp": 0.15,
    "workers compensation": 0.15,
    "general_liability": 0.12,
    "auto": 0.08,
    "commercial_auto": 0.08,
    "commercial property": 0.04,
    "property": 0.04,
    "inland_marine": 0.05,
    "umbrella": 0.12,
}


class DataAvailabilityStatus(str, Enum):
    ADEQUATE = "adequate"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"


class ReservingMethod(str, Enum):
    PAID_INCURRED_DEVELOPMENT = "paid_incurred_development"
    LOSS_RATIO_BORNHUETTER_FERGUSON = "loss_ratio_bornhuetter_ferguson"


class DataOrganization(BaseModel):
    """Are claims keyed to accident, report, and valuation dates?"""

    claims_with_accident_date: int = 0
    claims_with_report_date: int = 0
    claims_with_valuation_date: int = 0
    total_claims: int = 0
    status: DataAvailabilityStatus = DataAvailabilityStatus.INSUFFICIENT
    detail: str = ""


def assess_data_organization(claims: list[ClaimRecord]) -> DataOrganization:
    total = len(claims)
    accident = sum(1 for c in claims if c.date_of_loss is not None)
    reported = sum(1 for c in claims if c.date_reported is not None)
    valued = sum(1 for c in claims if c.valuation_date is not None or c.open_reserve > 0 or c.paid_amount > 0)
    org = DataOrganization(
        claims_with_accident_date=accident,
        claims_with_report_date=reported,
        claims_with_valuation_date=valued,
        total_claims=total,
    )
    if total == 0:
        org.status = DataAvailabilityStatus.INSUFFICIENT
        org.detail = "No claims available to organize"
    elif reported >= total * 0.8 and valued >= total * 0.8:
        org.status = DataAvailabilityStatus.ADEQUATE
        org.detail = "Claims are keyed to accident, report, and valuation dates"
    elif reported >= total * 0.5:
        org.status = DataAvailabilityStatus.PARTIAL
        org.detail = "Some claims missing report/valuation dates — reserves may be distorted"
    else:
        org.status = DataAvailabilityStatus.INSUFFICIENT
        org.detail = "Report/valuation dates missing for most claims — cannot assess emergence or development"
    return org


class EmergencePattern(BaseModel):
    """Delay between occurrence and recording of a claim."""

    report_lag_days: list[float] = Field(default_factory=list)
    average_report_lag_days: Optional[float] = None
    max_report_lag_days: Optional[float] = None
    pct_reported_within_30_days: float = 0.0
    severity: RiskSeverity = RiskSeverity.LOW
    detail: str = ""


def assess_emergence(claims: list[ClaimRecord]) -> EmergencePattern:
    lags: list[float] = []
    for c in claims:
        if c.date_reported is not None and c.date_of_loss is not None:
            lag = (c.date_reported - c.date_of_loss).days
            if lag >= 0:
                lags.append(float(lag))
    pattern = EmergencePattern(report_lag_days=lags)
    if not lags:
        pattern.detail = "No report dates available — cannot assess emergence"
        pattern.severity = RiskSeverity.HIGH
        return pattern
    pattern.average_report_lag_days = round(statistics.mean(lags), 1)
    pattern.max_report_lag_days = round(max(lags), 1)
    pattern.pct_reported_within_30_days = round(100.0 * sum(1 for lag in lags if lag <= 30) / len(lags), 1)
    if pattern.average_report_lag_days > 180:
        pattern.severity = RiskSeverity.HIGH
        pattern.detail = f"Avg report lag {pattern.average_report_lag_days:.0f} days — significant IBNR exposure; emergence is slow"
    elif pattern.average_report_lag_days > 60:
        pattern.severity = RiskSeverity.MODERATE
        pattern.detail = f"Avg report lag {pattern.average_report_lag_days:.0f} days — moderate emergence delay"
    else:
        pattern.severity = RiskSeverity.LOW
        pattern.detail = f"Avg report lag {pattern.average_report_lag_days:.0f} days — claims emerge promptly"
    return pattern


class SettlementPattern(BaseModel):
    """Length of time it takes for reported claims to settle."""

    settlement_days: list[float] = Field(default_factory=list)
    average_settlement_days: Optional[float] = None
    open_claim_ratio: float = 0.0
    severity: RiskSeverity = RiskSeverity.LOW
    detail: str = ""


def assess_settlement(claims: list[ClaimRecord]) -> SettlementPattern:
    durations: list[float] = []
    open_count = sum(1 for c in claims if c.claim_status.value == "open")
    for c in claims:
        if c.date_closed is not None and c.date_of_loss is not None:
            duration = (c.date_closed - c.date_of_loss).days
            if duration >= 0:
                durations.append(float(duration))
    pattern = SettlementPattern(settlement_days=durations)
    pattern.open_claim_ratio = round(open_count / len(claims), 4) if claims else 0.0
    if not durations:
        pattern.detail = "No settlement dates available — cannot assess settlement pattern"
        pattern.severity = RiskSeverity.HIGH
        return pattern
    pattern.average_settlement_days = round(statistics.mean(durations), 1)
    if pattern.average_settlement_days > 730:
        pattern.severity = RiskSeverity.HIGH
        pattern.detail = f"Avg {pattern.average_settlement_days:.0f} days to settle — long-tailed book; reserves held open longer"
    elif pattern.average_settlement_days > 365:
        pattern.severity = RiskSeverity.MODERATE
        pattern.detail = f"Avg {pattern.average_settlement_days:.0f} days to settle — moderate tail"
    else:
        pattern.severity = RiskSeverity.LOW
        pattern.detail = f"Avg {pattern.average_settlement_days:.0f} days to settle — short-tailed book"
    return pattern


class DevelopmentConsistency(BaseModel):
    """Consistency in settlement and reserving of claims."""

    settlement_cv: Optional[float] = None  # low CV = consistent claims handling
    reserve_adequacy_ratio: Optional[float] = None  # incurred / (paid + reserve)
    severity: RiskSeverity = RiskSeverity.LOW
    detail: str = ""


def _coefficient_of_variation(values: list[float]) -> Optional[float]:
    if len(values) < 2 or statistics.mean(values) == 0:
        return None
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    return stdev / mean


def assess_development_consistency(claims: list[ClaimRecord]) -> DevelopmentConsistency:
    durations: list[float] = []
    for c in claims:
        if c.date_closed is not None and c.date_of_loss is not None:
            duration = (c.date_closed - c.date_of_loss).days
            if duration >= 0:
                durations.append(float(duration))
    result = DevelopmentConsistency()
    result.settlement_cv = _coefficient_of_variation(durations)

    # Reserve adequacy: incurred should equal paid + open reserve on each claim.
    adequacy: list[float] = []
    for c in claims:
        denominator = c.paid_amount + c.open_reserve
        if denominator > 0:
            adequacy.append(c.incurred_amount / denominator)
    if adequacy:
        result.reserve_adequacy_ratio = round(statistics.mean(adequacy), 4)

    if result.settlement_cv is not None and result.settlement_cv > 0.6:
        result.severity = RiskSeverity.HIGH
        result.detail = f"Settlement CV {result.settlement_cv:.2f} — inconsistent settlement/reserving; development will be erratic"
    elif result.reserve_adequacy_ratio is not None and (result.reserve_adequacy_ratio > 1.3 or result.reserve_adequacy_ratio < 0.7):
        result.severity = RiskSeverity.HIGH
        result.detail = f"Reserve adequacy ratio {result.reserve_adequacy_ratio:.2f} — case reserves inconsistent with paid+held"
    else:
        result.severity = RiskSeverity.LOW
        result.detail = "Settlement and reserving appear consistent"
    return result


class FrequencySeverityProfile(BaseModel):
    """Frequency and severity of the claim book."""

    claim_count: int = 0
    frequency_per_year: Optional[float] = None
    average_severity: Optional[float] = None
    small_claim_ratio: float = 0.0
    reliability: float = 0.0  # 0..1 — high freq + low severity = more reliable reserves
    detail: str = ""


def assess_frequency_severity(claims: list[ClaimRecord], years: Optional[int] = None) -> FrequencySeverityProfile:
    profile = FrequencySeverityProfile(claim_count=len(claims))
    if not claims:
        profile.detail = "No claims to profile"
        return profile
    loss_years = sorted({c.date_of_loss.year for c in claims})
    span = years or (max(loss_years) - min(loss_years) + 1 if len(loss_years) > 1 else 1)
    profile.frequency_per_year = round(len(claims) / span, 2)
    severities = [c.incurred_amount for c in claims if c.incurred_amount > 0]
    if severities:
        profile.average_severity = round(statistics.mean(severities), 2)
        profile.small_claim_ratio = round(sum(1 for s in severities if s <= _SMALL_CLAIM_SEVERITY) / len(severities), 4)

    # CAS: high frequency + low average claim size → reserve estimates more reliable.
    freq_component = min(1.0, (profile.frequency_per_year or 0) / 10.0)
    severity_component = 1.0 if (profile.average_severity or float("inf")) <= _SMALL_CLAIM_SEVERITY else 0.4
    profile.reliability = round(min(1.0, freq_component * 0.6 + severity_component * 0.4), 4)
    profile.detail = (
        f"{profile.claim_count} claims, {profile.frequency_per_year}/yr, "
        f"avg ${profile.average_severity:,.0f}, small-claim ratio {profile.small_claim_ratio:.0%}"
    )
    return profile


class ReopenedClaimsPotential(BaseModel):
    """The inclination of closed claims to reopen, by line of business."""

    reopened_count: int = 0
    potential_by_line: dict[str, float] = Field(default_factory=dict)
    severity: RiskSeverity = RiskSeverity.LOW
    detail: str = ""


def assess_reopened_potential(claims: list[ClaimRecord]) -> ReopenedClaimsPotential:
    reopened = sum(1 for c in claims if c.reopened)
    potential: dict[str, float] = {}
    for c in claims:
        key = c.line_of_business.lower()
        rate = _REOPENED_POTENTIAL.get(key, 0.08)
        potential[key] = max(potential.get(key, 0.0), rate)
    result = ReopenedClaimsPotential(reopened_count=reopened, potential_by_line=potential)
    if reopened > 0 or any(rate >= 0.12 for rate in potential.values()):
        result.severity = RiskSeverity.MODERATE
        result.detail = f"{reopened} reopened claim(s); lines with high reopen potential: {', '.join(sorted(potential))}"
    else:
        result.severity = RiskSeverity.LOW
        result.detail = "No reopened claims; reopen potential low"
    return result


class OperationalChange(BaseModel):
    """A detected operational change that can distort loss experience."""

    marker: str
    severity: RiskSeverity = RiskSeverity.MODERATE
    detail: str = ""


def detect_operational_changes(bundle: SubmissionBundle) -> list[OperationalChange]:
    """Detect systems/accounting/claims/underwriting changes that break continuity."""
    texts: list[str] = []
    if bundle.structured:
        if bundle.structured.raw_xml:
            texts.append(bundle.structured.raw_xml)
        if bundle.structured.raw_json:
            texts.append(bundle.structured.raw_json)
    for doc in (bundle.unstructured or []) + (bundle.supplemental or []):
        texts.append(doc.raw_text)
    found: list[OperationalChange] = []
    for text in texts:
        lowered = text.lower()
        for marker in _OPERATIONAL_CHANGE_MARKERS:
            if marker in lowered:
                found.append(
                    OperationalChange(
                        marker=marker,
                        severity=RiskSeverity.HIGH if any(k in marker for k in ("system conversion", "data migration", "portfolio acquisition")) else RiskSeverity.MODERATE,
                        detail=f"Operational change detected: '{marker}' — loss experience before/after is not directly comparable",
                    )
                )
    return found


class ReasonablenessCheck(BaseModel):
    """The ratio of the loss estimate to an independent measure."""

    loss_ratio: Optional[float] = None  # incurred / premium
    loss_per_claim: Optional[float] = None  # incurred / claim count
    premium: float = 0.0
    expected_loss_ratio: float = 0.65
    is_reasonable: bool = True
    detail: str = ""


def check_reasonableness(
    claims: list[ClaimRecord],
    *,
    premium: float = 0.0,
    exposures: float = 0.0,
    expected_loss_ratio: float = 0.65,
) -> ReasonablenessCheck:
    """Compare the loss estimate with premiums/exposures/claims counts."""
    incurred = sum(c.incurred_amount for c in claims)
    result = ReasonablenessCheck(premium=premium, expected_loss_ratio=expected_loss_ratio)
    if premium > 0:
        result.loss_ratio = round(incurred / premium, 4)
    if claims:
        result.loss_per_claim = round(incurred / len(claims), 2)
    if result.loss_ratio is not None:
        upper = expected_loss_ratio * 1.5
        lower = max(expected_loss_ratio * 0.1, 0.05)
        result.is_reasonable = lower <= result.loss_ratio <= upper
        result.detail = f"Loss ratio {result.loss_ratio:.2f} vs expected {expected_loss_ratio:.2f} (band {lower:.2f}–{upper:.2f})"
    elif exposures > 0:
        per_exposure = incurred / exposures
        result.is_reasonable = per_exposure <= 0.5
        result.detail = f"Loss per exposure ${per_exposure:,.2f}"
    else:
        result.is_reasonable = True
        result.detail = "No independent premium/exposure measure — reasonableness not testable"
    return result


class ReserveEstimate(BaseModel):
    """One reserving method's estimate of the outstanding loss liability."""

    method: ReservingMethod
    outstanding_reserve: float
    detail: str = ""


class ReserveStudy(BaseModel):
    """The loss-and-loss-adjustment-expense liability estimate for a claim group."""

    incurred: float = 0.0
    paid: float = 0.0
    case_reserves: float = 0.0
    estimates: list[ReserveEstimate] = Field(default_factory=list)
    range_low: float = 0.0
    range_high: float = 0.0
    recommended: float = 0.0
    detail: str = ""


def run_reserve_study(
    claims: list[ClaimRecord],
    *,
    premium: float = 0.0,
    expected_loss_ratio: float = 0.65,
    ibnr_factor: float = 0.10,
) -> ReserveStudy:
    """Estimate the outstanding reserve using two independent methods.

    Method 1 (paid/incurred development): outstanding = sum of case reserves
    plus an IBNR load proportional to open/emerging exposure.

    Method 2 (loss-ratio / Bornhuetter-Ferguson style): ultimate = premium ×
    expected loss ratio; outstanding = ultimate − paid to date.

    The actuary's practice is to compare methods and carry a range — mirrored
    here as the min/max of the two independent estimates.
    """
    incurred = sum(c.incurred_amount for c in claims)
    paid = sum(c.paid_amount for c in claims)
    case_reserves = sum(c.open_reserve for c in claims)

    # Method 1 — paid/incurred development.
    open_ratio = (sum(1 for c in claims if c.claim_status.value == "open") / len(claims)) if claims else 0.0
    ibnr = incurred * ibnr_factor * (0.5 + open_ratio)
    method1 = case_reserves + ibnr

    # Method 2 — loss-ratio (BF style).
    method2 = max(0.0, premium * expected_loss_ratio - paid)

    estimates = [
        ReserveEstimate(
            method=ReservingMethod.PAID_INCURRED_DEVELOPMENT,
            outstanding_reserve=round(method1, 2),
            detail=f"Case reserves ${case_reserves:,.0f} + IBNR ${ibnr:,.0f}",
        ),
        ReserveEstimate(
            method=ReservingMethod.LOSS_RATIO_BORNHUETTER_FERGUSON,
            outstanding_reserve=round(method2, 2),
            detail=f"Ultimate (premium {premium:,.0f} × {expected_loss_ratio:.2f}) − paid ${paid:,.0f}",
        ),
    ]

    low = min(method1, method2)
    high = max(method1, method2)
    return ReserveStudy(
        incurred=round(incurred, 2),
        paid=round(paid, 2),
        case_reserves=round(case_reserves, 2),
        estimates=estimates,
        range_low=round(low, 2),
        range_high=round(high, 2),
        recommended=round((low + high) / 2, 2),
        detail=f"Two-method reserve range ${low:,.0f}–${high:,.0f}, recommended midpoint ${(low+high)/2:,.0f}",
    )


class ReservingStandardsReview(BaseModel):
    """Aggregate CAS reserving-standards review for a book of claims."""

    organization: Optional[DataOrganization] = None
    emergence: Optional[EmergencePattern] = None
    settlement: Optional[SettlementPattern] = None
    development: Optional[DevelopmentConsistency] = None
    frequency_severity: Optional[FrequencySeverityProfile] = None
    reopened: Optional[ReopenedClaimsPotential] = None
    operational_changes: list[OperationalChange] = Field(default_factory=list)
    reasonableness: Optional[ReasonablenessCheck] = None
    reserve_study: Optional[ReserveStudy] = None
    worst_severity: RiskSeverity = RiskSeverity.LOW
    summary: str = ""


def run_reserving_standards_review(
    bundle: SubmissionBundle,
    *,
    premium: float = 0.0,
    exposures: float = 0.0,
    expected_loss_ratio: float = 0.65,
    years: Optional[int] = None,
) -> ReservingStandardsReview:
    """Run the full CAS standards review over a submission's claims."""
    claims: list[ClaimRecord] = []
    if bundle.structured:
        if bundle.structured.risk_profile:
            claims.extend(bundle.structured.risk_profile.prior_claims or [])
        if bundle.structured.financial and bundle.structured.financial.loss_run:
            claims.extend(bundle.structured.financial.loss_run.claims or [])

    review = ReservingStandardsReview(
        organization=assess_data_organization(claims),
        emergence=assess_emergence(claims),
        settlement=assess_settlement(claims),
        development=assess_development_consistency(claims),
        frequency_severity=assess_frequency_severity(claims, years=years),
        reopened=assess_reopened_potential(claims),
        operational_changes=detect_operational_changes(bundle),
        reasonableness=check_reasonableness(claims, premium=premium, exposures=exposures, expected_loss_ratio=expected_loss_ratio),
        reserve_study=run_reserve_study(claims, premium=premium, expected_loss_ratio=expected_loss_ratio),
    )

    severities: list[str] = []
    for result in (
        review.organization,
        review.emergence,
        review.settlement,
        review.development,
        review.reopened,
    ):
        if result is not None:
            severity = getattr(result, "severity", getattr(result, "status", None))
            if severity is not None:
                severities.append(severity.value)
    if review.operational_changes:
        severities.append(RiskSeverity.HIGH.value)
    if review.reasonableness and not review.reasonableness.is_reasonable:
        severities.append(RiskSeverity.HIGH.value)
    rank = {RiskSeverity.LOW.value: 0, RiskSeverity.MODERATE.value: 1, RiskSeverity.HIGH.value: 2, RiskSeverity.CRITICAL.value: 3}
    if severities:
        worst = max(severities, key=lambda s: rank.get(s, 0))
        review.worst_severity = RiskSeverity(worst)

    study = review.reserve_study
    if study is not None:
        review.summary = (
            f"{len(claims)} claims, case reserves ${study.case_reserves:,.0f}, "
            f"two-method reserve range ${study.range_low:,.0f}–${study.range_high:,.0f}; "
            f"{len(review.operational_changes)} operational change(s) detected"
        )
    else:
        review.summary = f"{len(claims)} claims; {len(review.operational_changes)} operational change(s) detected"
    return review
