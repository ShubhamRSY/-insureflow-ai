"""Loss ratio is incurred ÷ earned premium — never TIV."""

from __future__ import annotations

from datetime import date

from insureflow.models.submissions import (
    ClaimRecord,
    CoverageDetail,
    FinancialData,
    LocationData,
    LossRunData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.underwriting.loss_ratio import compute_loss_ratio, loss_ratio_from_bundle, normalize_stored_ratio


def test_normalize_percent_vs_decimal() -> None:
    assert normalize_stored_ratio(0.65) == 0.65
    assert normalize_stored_ratio(65) == 0.65
    assert normalize_stored_ratio(125) == 1.25


def test_compute_uses_earned_premium_not_tiv() -> None:
    result = compute_loss_ratio(incurred=50_000, earned_premium=100_000, written_premium=120_000)
    assert result.known is True
    assert result.basis == "earned_premium"
    assert result.ratio == 0.5


def test_compute_falls_back_to_written_premium() -> None:
    result = compute_loss_ratio(incurred=40_000, written_premium=80_000)
    assert result.known is True
    assert result.basis == "written_premium"
    assert result.ratio == 0.5


def test_compute_unknown_without_premium() -> None:
    result = compute_loss_ratio(incurred=500_000)
    assert result.known is False
    assert result.ratio == 0.0
    assert result.basis == "unknown"


def test_stored_ratio_wins() -> None:
    result = compute_loss_ratio(
        incurred=999,
        earned_premium=1,
        stored_ratios={"2024": 0.42, "2023": 0.38},
    )
    assert result.known is True
    assert result.basis == "stored"
    assert result.ratio == 0.42


def test_bundle_uses_earned_not_building_value() -> None:
    bundle = SubmissionBundle(
        bundle_id="lr-1",
        structured=StructuredSubmission(
            submission_id="lr-1",
            named_insured=NamedInsured(legal_name="Test Co"),
            locations=[
                LocationData(
                    address="1 Main",
                    city="Austin",
                    state="TX",
                    zip_code="78701",
                    building_value=5_000_000,
                    contents_value=1_000_000,
                )
            ],
            coverages=[CoverageDetail(coverage_type="Property", limit_amount=6_000_000, deductible=10_000, premium=80_000)],
            financial=FinancialData(
                loss_run=LossRunData(
                    total_incurred=40_000,
                    earned_premium=100_000,
                    written_premium=80_000,
                    claims=[
                        ClaimRecord(
                            claim_id="c1",
                            date_of_loss=date(2024, 1, 1),
                            line_of_business="property",
                            cause="fire",
                            incurred_amount=40_000,
                        )
                    ],
                )
            ),
        ),
    )
    result = loss_ratio_from_bundle(bundle)
    assert result.known is True
    assert result.basis == "earned_premium"
    assert result.ratio == 0.4
    # Old formula incurred / TIV would be 40000/6000000 ≈ 0.0067
    assert result.ratio != round(40_000 / 6_000_000, 4)


def test_bundle_written_premium_from_coverages() -> None:
    bundle = SubmissionBundle(
        bundle_id="lr-2",
        structured=StructuredSubmission(
            submission_id="lr-2",
            named_insured=NamedInsured(legal_name="Test Co"),
            coverages=[CoverageDetail(coverage_type="GL", limit_amount=1_000_000, deductible=5_000, premium=50_000)],
            risk_profile=RiskProfile(
                prior_claims=[
                    ClaimRecord(
                        claim_id="c1",
                        date_of_loss=date(2024, 6, 1),
                        line_of_business="gl",
                        cause="slip",
                        incurred_amount=25_000,
                    )
                ]
            ),
        ),
    )
    result = loss_ratio_from_bundle(bundle)
    assert result.known is True
    assert result.basis == "written_premium"
    assert result.ratio == 0.5
