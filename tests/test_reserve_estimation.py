from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from insureflow.api import app
from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import ClaimRecord, ClaimStatus
from insureflow.rating.reserve_estimation import assess_data_delays, build_payout_pattern, estimate_ibnr, rate_filing_schedule, run_reserve_analysis, vehicle_liability_payout_pattern


def _claim(
    claim_id: str,
    *,
    date_of_loss: date,
    incurred: float,
    paid: float = 0.0,
    reserve: float = 0.0,
    date_reported: date | None = None,
    date_closed: date | None = None,
    status: ClaimStatus = ClaimStatus.OPEN,
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        date_of_loss=date_of_loss,
        line_of_business="commercial_auto",
        cause="collision",
        incurred_amount=incurred,
        paid_amount=paid,
        open_reserve=reserve,
        claim_status=status,
        date_reported=date_reported,
        date_closed=date_closed,
    )


def test_vehicle_liability_payout_pattern_matches_textbook() -> None:
    pattern = vehicle_liability_payout_pattern()
    assert len(pattern.valuations) == 7
    first = pattern.valuations[0]
    assert first.paid_to_date == 5_051_145
    assert first.reported_but_unpaid == 13_837_205
    assert first.ibnr == 9_592_239
    assert first.incurred_estimate == 28_480_589
    assert pattern.valuations[4].ibnr == 0.0
    assert pattern.valuations[5].ibnr == 0.0
    assert pattern.ultimate_estimate == 25_948_644


def test_reserve_redundancy_pct_is_9_8_percent() -> None:
    pattern = vehicle_liability_payout_pattern()
    assert pattern.reserve_redundancy_pct is not None
    assert pattern.reserve_redundancy_pct == round((28_480_589 - 25_948_644) / 25_948_644 * 100, 1)
    assert pattern.reserve_redundancy_pct == 9.8


def test_estimate_ibnr_no_claims_returns_zero() -> None:
    assert estimate_ibnr([], accident_year=2020) == 0.0
    assert estimate_ibnr([_claim("c", date_of_loss=date(2020, 1, 1), incurred=0.0)]) == 0.0


def test_estimate_ibnr_unreported_share_scales_with_severity() -> None:
    dol = date(2020, 1, 1)
    claims = [_claim("c1", date_of_loss=dol, incurred=1000.0, date_reported=dol) for _ in range(10)]
    assert estimate_ibnr(claims, accident_year=2020, valuation_age_years=1) == 0.0


def test_estimate_ibnr_projects_from_emergence() -> None:
    dol = date(2020, 1, 1)
    lags = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450]
    claims = [_claim(f"c{i}", date_of_loss=dol, incurred=1000.0, date_reported=dol + timedelta(days=lags[i])) for i in range(10)]
    # At one year of age, claims with a report lag beyond ~365 days are still unreported.
    ibnr = estimate_ibnr(claims, accident_year=2020, valuation_age_years=1)
    assert ibnr > 0
    assert ibnr < 10_000


def test_build_payout_pattern_from_claims() -> None:
    dol = date(2020, 1, 1)
    claims = [
        _claim(
            "closed-1",
            date_of_loss=dol,
            incurred=5000.0,
            paid=5000.0,
            date_reported=dol + timedelta(days=5),
            date_closed=dol + timedelta(days=180),
            status=ClaimStatus.CLOSED,
        ),
        _claim(
            "open-1",
            date_of_loss=dol,
            incurred=3000.0,
            paid=1000.0,
            reserve=2000.0,
            date_reported=dol + timedelta(days=5),
            status=ClaimStatus.OPEN,
        ),
    ]
    pattern = build_payout_pattern(claims, accident_year=2020, valuation_years=2)
    assert pattern.accident_year == "2020"
    assert pattern.ultimate_estimate == 8000.0
    year1 = pattern.valuations[0]
    assert year1.paid_to_date == 5000.0
    assert year1.reported_but_unpaid == 2000.0
    assert year1.ibnr == 0.0
    assert year1.incurred_estimate == 7000.0
    assert pattern.reserve_redundancy_pct is not None


def test_build_payout_pattern_empty_year() -> None:
    pattern = build_payout_pattern([], accident_year=1999)
    assert pattern.valuations == []
    assert "No claims" in pattern.detail


def test_filing_schedule_stages() -> None:
    schedule = rate_filing_schedule()
    assert len(schedule.stages) == 8
    assert schedule.experience_period == "Year 1 through Year 3"
    assert schedule.total_lag_years == 6.0
    assert schedule.stages[0].stage == "Start of experience period"
    assert schedule.stages[-1].stage == "Last policy expiration"
    assert "six years" in schedule.detail


def test_data_delay_sources() -> None:
    delays = assess_data_delays()
    assert len(delays) == 5
    assert {d.source for d in delays} == {
        "Policyholder reporting delay",
        "Data analysis and filing preparation",
        "State approval of filed rates",
        "Implementation of new rates",
        "Rates-in-effect period",
    }
    assert all(d.severity in (RiskSeverity.LOW, RiskSeverity.MODERATE) for d in delays)


def test_run_reserve_analysis_defaults_to_textbook() -> None:
    analysis = run_reserve_analysis()
    assert analysis.payout_pattern is not None
    assert analysis.payout_pattern.reserve_redundancy_pct == 9.8
    assert analysis.filing_schedule is not None
    assert analysis.filing_schedule.total_lag_years == 6.0
    assert len(analysis.data_delays) == 5
    assert analysis.worst_severity == RiskSeverity.HIGH
    assert "6 years" in analysis.summary


def test_run_reserve_analysis_from_claims() -> None:
    dol = date(2021, 1, 1)
    claims = [_claim(f"c{i}", date_of_loss=dol, incurred=1000.0, date_reported=dol + timedelta(days=i)) for i in range(20)]
    analysis = run_reserve_analysis(claims, accident_year=2021, valuation_years=3)
    assert analysis.payout_pattern is not None
    assert len(analysis.payout_pattern.valuations) == 3
    assert analysis.payout_pattern.accident_year == "2021"
    assert analysis.filing_schedule is not None


def test_overview_endpoint_includes_reserve_analysis() -> None:
    from insureflow.auth import Role
    from insureflow.auth.jwt import create_access_token
    from insureflow.auth.models import User
    from insureflow.auth.store import get_user_store

    get_user_store()["uw"] = User(username="uw", hashed_password="x", role=Role.VIEWER, org_id="acme")
    token = create_access_token({"sub": "uw", "role": Role.VIEWER.value, "org_id": "acme"})
    resp = TestClient(app).get("/pipeline/rating/ratemaking", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    reserve = resp.json()["reserve_analysis"]
    assert reserve["payout_pattern"]["reserve_redundancy_pct"] == 9.8
    assert reserve["filing_schedule"]["total_lag_years"] == 6.0
    assert len(reserve["data_delays"]) == 5


def test_redundancy_negative_means_under_reserving() -> None:
    # A fully matured single-valuation book has no reserve redundancy.
    dol = date(2020, 1, 1)
    claims = [_claim("c", date_of_loss=dol, incurred=1000.0, paid=1000.0, date_reported=dol, date_closed=dol + timedelta(days=90), status=ClaimStatus.CLOSED)]
    analysis = run_reserve_analysis(claims, accident_year=2020, valuation_years=1)
    assert analysis.payout_pattern is not None
    assert analysis.payout_pattern.reserve_redundancy_pct == 0.0


def test_valuation_year_one_includes_ibnr_when_reported_share_is_low() -> None:
    dol = date(2020, 1, 1)
    lags = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450]
    claims = [_claim(f"c{i}", date_of_loss=dol, incurred=5000.0, date_reported=dol + timedelta(days=lags[i])) for i in range(10)]
    pattern = build_payout_pattern(claims, accident_year=2020, valuation_years=2)
    assert pattern.valuations[0].ibnr > 0
    assert pattern.valuations[1].ibnr == 0.0


def test_pydantic_fractional_rounding() -> None:
    # The textbook redundancy must hold to one decimal regardless of order.
    assert round((28_480_589 - 25_948_644) / 25_948_644 * 100, 1) == pytest.approx(9.8)
