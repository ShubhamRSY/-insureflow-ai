"""Loss reserve estimation — payout patterns, IBNR, and the rate filing delay.

Chapter: Pricing Insurance Products — Loss Reserves Estimation. Few losses are
paid immediately, so incurred losses include both paid losses and outstanding
loss reserves. Because reserves are estimates, under-reserving makes rates too
low and over-reserving makes them too high. This module turns that material into
modeled analysis:

* Payout patterns — the accident-year development table showing paid losses to
  date, reported-but-unpaid losses (case reserves), incurred-but-not-reported
  (IBNR) losses, and the estimated incurred loss at each valuation year.
* Development to ultimate — quantifying reserve redundancy when the early
  incurred estimate exceeds the ultimate estimate (the textbook example: a
  9.8% overstatement would have made rates roughly 10% too high).
* The rate filing schedule — the experience period, data collection, filing,
  approval, effective date, and final policy expiration, plus the sources of
  delay that keep loss experience from being reflected in rates for years.
"""

from __future__ import annotations

import statistics
from typing import Optional

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import ClaimRecord

# ── Payout pattern ──────────────────────────────────────────────────────────


class ValuationEstimate(BaseModel):
    """One valuation year of an accident-year development table."""

    valuation_year: int
    paid_to_date: float = 0.0
    reported_but_unpaid: float = 0.0
    ibnr: float = 0.0
    incurred_estimate: float = 0.0
    detail: str = ""


class PayoutPattern(BaseModel):
    """Development of an accident year from first valuation to maturity."""

    accident_year: str = ""
    valuations: list[ValuationEstimate] = Field(default_factory=list)
    ultimate_estimate: float = 0.0
    reserve_redundancy_pct: Optional[float] = None
    detail: str = ""


# The textbook vehicle liability payout example (Chart 5-2): for each of seven
# valuation years, (paid losses to date, reported-but-unpaid, IBNR).
_VEHICLE_LIABILITY_ROWS: list[tuple[float, float, float]] = [
    (5_051_145, 13_837_205, 9_592_239),
    (10_780_845, 12_906_866, 4_187_646),
    (16_036_708, 9_058_737, 2_036_246),
    (19_667_531, 6_782_231, 79_247),
    (22_268_032, 4_308_212, 0.0),
    (24_714_163, 3_136_059, 0.0),
    (25_088_249, 860_395, 0.0),
]


def vehicle_liability_payout_pattern() -> PayoutPattern:
    """The textbook auto liability development table (Chart 5-2).

    Incurred losses at each year-end are the sum of paid losses to date,
    reported-but-unpaid losses, and IBNR. The insurer assumed all Year 1 losses
    were reported by the end of Year 5, so IBNR is zero from Year 5 on.
    """
    valuations = [
        ValuationEstimate(
            valuation_year=i,
            paid_to_date=paid,
            reported_but_unpaid=case,
            ibnr=ibnr,
            incurred_estimate=paid + case + ibnr,
            detail=f"End of Year {i} estimate of losses incurred in Year 1",
        )
        for i, (paid, case, ibnr) in enumerate(_VEHICLE_LIABILITY_ROWS, start=1)
    ]
    initial = valuations[0].incurred_estimate
    ultimate = valuations[-1].incurred_estimate
    redundancy = round((initial - ultimate) / ultimate * 100.0, 1)
    return PayoutPattern(
        accident_year="Year 1",
        valuations=valuations,
        ultimate_estimate=round(ultimate, 2),
        reserve_redundancy_pct=redundancy,
        detail=(f"Estimated incurred at end of Year 1 was ${initial:,.0f}; the estimate matured to ${ultimate:,.0f}. Using the early estimate would have made rates ~{redundancy:.1f}% too high"),
    )


def _report_lag_days(claim: ClaimRecord) -> Optional[int]:
    if claim.date_reported is not None and claim.date_of_loss is not None:
        lag = (claim.date_reported - claim.date_of_loss).days
        if lag >= 0:
            return lag
    return None


def estimate_ibnr(
    claims: list[ClaimRecord],
    *,
    accident_year: Optional[int] = None,
    valuation_age_years: int = 1,
    average_severity: Optional[float] = None,
) -> float:
    """Average-cost IBNR estimate from the report-lag emergence pattern.

    Claims that have not yet been reported by a given valuation age are
    projected by multiplying the unreported share of claims by the average
    severity. At maturity (all claims reported) the estimate is zero.
    """
    year_claims = [c for c in claims if accident_year is None or (c.date_of_loss is not None and c.date_of_loss.year == accident_year)]
    if not year_claims:
        return 0.0
    severities = [c.incurred_amount for c in year_claims if c.incurred_amount > 0]
    if not severities:
        return 0.0
    severity = average_severity or statistics.mean(severities)
    lags = [lag for c in year_claims if (lag := _report_lag_days(c)) is not None]
    if not lags:
        return 0.0
    horizon_days = valuation_age_years * 365
    reported_share = sum(1 for lag in lags if lag <= horizon_days) / len(lags)
    unreported_share = max(0.0, 1.0 - reported_share)
    return round(unreported_share * len(year_claims) * severity, 2)


def build_payout_pattern(
    claims: list[ClaimRecord],
    *,
    accident_year: int,
    valuation_years: int = 7,
) -> PayoutPattern:
    """Build an accident-year development table from actual claim records."""
    year_claims = [c for c in claims if c.date_of_loss is not None and c.date_of_loss.year == accident_year]
    if not year_claims:
        return PayoutPattern(accident_year=str(accident_year), detail="No claims recorded for this accident year")

    severities = [c.incurred_amount for c in year_claims if c.incurred_amount > 0]
    average_severity = statistics.mean(severities) if severities else 0.0
    lags = [lag for c in year_claims if (lag := _report_lag_days(c)) is not None]
    ultimate = sum(c.incurred_amount for c in year_claims)

    valuations: list[ValuationEstimate] = []
    for t in range(1, valuation_years + 1):
        horizon_days = t * 365
        paid_to_date = sum(c.paid_amount for c in year_claims if c.date_closed is not None and c.date_of_loss is not None and 0 <= (c.date_closed - c.date_of_loss).days <= horizon_days)
        reported_unpaid = sum(
            c.open_reserve
            for c in year_claims
            if c.claim_status.value == "open" and c.date_reported is not None and c.date_of_loss is not None and 0 <= (c.date_reported - c.date_of_loss).days <= horizon_days
        )
        reported_share = sum(1 for lag in lags if lag <= horizon_days) / len(lags) if lags else 1.0
        ibnr = round(max(0.0, 1.0 - reported_share) * len(year_claims) * average_severity, 2)
        valuations.append(
            ValuationEstimate(
                valuation_year=t,
                paid_to_date=round(paid_to_date, 2),
                reported_but_unpaid=round(reported_unpaid, 2),
                ibnr=ibnr,
                incurred_estimate=round(paid_to_date + reported_unpaid + ibnr, 2),
            )
        )

    initial = valuations[0].incurred_estimate
    redundancy = round((initial - ultimate) / ultimate * 100.0, 1) if ultimate else None
    return PayoutPattern(
        accident_year=str(accident_year),
        valuations=valuations,
        ultimate_estimate=round(ultimate, 2),
        reserve_redundancy_pct=redundancy,
        detail=f"{len(year_claims)} claims in {accident_year}; incurred estimate vs ultimate {redundancy:+.1f}%" if redundancy is not None else "",
    )


# ── Rate filing schedule and data delays ────────────────────────────────────


class FilingStage(BaseModel):
    date: str
    stage: str
    description: str = ""


class FilingSchedule(BaseModel):
    experience_period: str = ""
    stages: list[FilingStage] = Field(default_factory=list)
    total_lag_years: float = 0.0
    detail: str = ""


def rate_filing_schedule() -> FilingSchedule:
    """The textbook auto rate filing schedule.

    Data from a three-year experience period are collected, analyzed, filed,
    approved, and put into effect; the last policy issued under the new rates
    stays in force a further year, so the last loss under the rates is incurred
    about six years after the first loss on which the rates were based.
    """
    stages = [
        FilingStage(date="1/1/Yr. 1", stage="Start of experience period", description="First loss that will feed the rate calculation can be incurred"),
        FilingStage(date="12/31/Yr. 3", stage="End of experience period", description="Three-year loss experience period closes"),
        FilingStage(date="3/31/Yr. 4", stage="Data collection and analysis", description="Begins three months after the experience period; some insurers wait longer for loss data to mature"),
        FilingStage(date="7/1/Yr. 4", stage="Rates filed with regulators", description="Rate filing submitted for state approval"),
        FilingStage(date="9/1/Yr. 4", stage="Approval received", description="State approves the filed rates"),
        FilingStage(date="1/1/Yr. 5", stage="New rates first used", description="Rates become effective for new and renewal policies"),
        FilingStage(date="12/31/Yr. 5", stage="Rates no longer used", description="Rates remain in effect for one full year"),
        FilingStage(date="12/31/Yr. 6", stage="Last policy expiration", description="Coverage on the last policy issued under these rates expires"),
    ]
    return FilingSchedule(
        experience_period="Year 1 through Year 3",
        stages=stages,
        total_lag_years=6.0,
        detail=("The last loss under a rate filing is incurred roughly six years after the first loss on which the rate calculation was based; delays erode rate responsiveness"),
    )


class DataDelaySource(BaseModel):
    """One source of delay between loss occurrence and rate implementation."""

    source: str
    severity: RiskSeverity = RiskSeverity.MODERATE
    detail: str = ""


_DELAY_SOURCES: list[tuple[str, RiskSeverity, str]] = [
    ("Policyholder reporting delay", RiskSeverity.LOW, "Delays by policyholders in reporting losses to the insurer"),
    ("Data analysis and filing preparation", RiskSeverity.MODERATE, "Time required to analyze data and prepare a rate filing"),
    ("State approval of filed rates", RiskSeverity.MODERATE, "Delays in obtaining state approval of filed rates"),
    ("Implementation of new rates", RiskSeverity.LOW, "Time required to implement new rates in systems and manuals"),
    ("Rates-in-effect period", RiskSeverity.MODERATE, "Rates stay in effect ~a full year; the last policy issued under them runs another year"),
]


def assess_data_delays() -> list[DataDelaySource]:
    """The sources of delay that reduce rate responsiveness."""
    return [DataDelaySource(source=s, severity=sev, detail=d) for s, sev, d in _DELAY_SOURCES]


# ── Aggregate analysis ──────────────────────────────────────────────────────


class RateReserveAnalysis(BaseModel):
    """Payout pattern, filing schedule, and data delays for the rate book."""

    payout_pattern: Optional[PayoutPattern] = None
    filing_schedule: Optional[FilingSchedule] = None
    data_delays: list[DataDelaySource] = Field(default_factory=list)
    worst_severity: RiskSeverity = RiskSeverity.LOW
    summary: str = ""


def run_reserve_analysis(
    claims: Optional[list[ClaimRecord]] = None,
    *,
    accident_year: Optional[int] = None,
    valuation_years: int = 7,
) -> RateReserveAnalysis:
    """Run the full reserve-estimation analysis for a book of claims.

    With no claims the textbook vehicle-liability example is used; with claims,
    the development table is built from the actual claim records for the given
    accident year.
    """
    if claims:
        pattern = build_payout_pattern(claims, accident_year=accident_year or 0, valuation_years=valuation_years)
    else:
        pattern = vehicle_liability_payout_pattern()
    schedule = rate_filing_schedule()
    delays = assess_data_delays()

    severities = [d.severity for d in delays]
    rank = {RiskSeverity.LOW.value: 0, RiskSeverity.MODERATE.value: 1, RiskSeverity.HIGH.value: 2, RiskSeverity.CRITICAL.value: 3}
    worst = max(severities, key=lambda s: rank.get(s.value, 0)) if severities else RiskSeverity.LOW
    redundancy = pattern.reserve_redundancy_pct
    if redundancy is not None and redundancy > 0 and rank.get(worst.value, 0) < rank[RiskSeverity.HIGH.value]:
        worst = RiskSeverity.HIGH

    summary = f"Reserve redundancy {redundancy:+.1f}% at first valuation vs ultimate" if redundancy is not None else "Reserve redundancy not measurable"
    summary += f"; rate lag from experience-period start to last policy expiration ≈ {schedule.total_lag_years:.0f} years"
    return RateReserveAnalysis(
        payout_pattern=pattern,
        filing_schedule=schedule,
        data_delays=delays,
        worst_severity=worst,
        summary=summary,
    )
