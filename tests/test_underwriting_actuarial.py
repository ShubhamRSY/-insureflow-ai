"""Tests for the Chapter 5 additions: CAS loss reserving standards and ASOP 12 risk classification."""

from __future__ import annotations

from datetime import date, timedelta

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import ClaimRecord, ClaimStatus, NamedInsured, RiskProfile, StructuredSubmission, SubmissionBundle, UnstructuredSubmission
from insureflow.underwriting.acceptability import AcceptabilityCode, ClassAcceptability
from insureflow.underwriting.asop12 import ClassificationStatus, RiskCharacteristic, check_surrogate, review_classification
from insureflow.underwriting.reserving import (
    ReservingMethod,
    assess_data_organization,
    assess_development_consistency,
    assess_emergence,
    assess_frequency_severity,
    assess_reopened_potential,
    assess_settlement,
    check_reasonableness,
    detect_operational_changes,
    run_reserve_study,
    run_reserving_standards_review,
)


def _claim(
    claim_id: str,
    *,
    loss: date,
    reported: date | None = None,
    closed: date | None = None,
    incurred: float = 5_000.0,
    paid: float = 2_000.0,
    reserve: float = 3_000.0,
    status: ClaimStatus = ClaimStatus.CLOSED,
    lob: str = "general_liability",
    reopened: bool = False,
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        date_of_loss=loss,
        line_of_business=lob,
        cause="slip and fall",
        description="",
        incurred_amount=incurred,
        paid_amount=paid,
        open_reserve=reserve,
        claim_status=status,
        date_reported=reported,
        date_closed=closed,
        valuation_date=loss + timedelta(days=60),
        reopened=reopened,
    )


def _bundle(claims: list[ClaimRecord]) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="reserve-bundle",
        structured=StructuredSubmission(
            submission_id="reserve-sub",
            named_insured=NamedInsured(legal_name="Reserve Co."),
            risk_profile=RiskProfile(prior_claims=claims),
        ),
    )


def _claims() -> list[ClaimRecord]:
    today = date(2024, 1, 1)
    return [
        _claim("CL-1", loss=today - timedelta(days=300), reported=today - timedelta(days=290), closed=today - timedelta(days=200)),
        _claim("CL-2", loss=today - timedelta(days=200), reported=today - timedelta(days=195), closed=today - timedelta(days=100)),
        _claim("CL-3", loss=today - timedelta(days=150), reported=today - timedelta(days=140), closed=today - timedelta(days=60)),
        _claim("CL-4", loss=today - timedelta(days=80), reported=today - timedelta(days=70), status=ClaimStatus.OPEN, reserve=20_000),
    ]


# ── 1. Data organization (accident / report / valuation dates) ────────────


def test_data_organization_adequate():
    org = assess_data_organization(_claims())
    assert org.claims_with_accident_date == 4
    assert org.claims_with_report_date == 4
    assert org.status.value == "adequate"


def test_data_organization_insufficient():
    claims = [_claim("CL-1", loss=date(2024, 1, 1), reported=None)]
    org = assess_data_organization(claims)
    assert org.status.value == "insufficient"


# ── 2. Emergence patterns ──────────────────────────────────────────────────


def test_emergence_average_lag():
    pattern = assess_emergence(_claims())
    assert pattern.average_report_lag_days is not None
    assert 5.0 <= pattern.average_report_lag_days <= 15.0
    assert pattern.pct_reported_within_30_days == 100.0
    assert pattern.severity == RiskSeverity.LOW


def test_emergence_slow_lag_is_high_severity():
    loss = date(2023, 1, 1)
    claim = _claim("CL-1", loss=loss, reported=loss + timedelta(days=400))
    pattern = assess_emergence([claim])
    assert pattern.severity == RiskSeverity.HIGH


# ── 3. Settlement patterns ─────────────────────────────────────────────────


def test_settlement_average_duration():
    pattern = assess_settlement(_claims())
    assert pattern.average_settlement_days is not None
    assert pattern.open_claim_ratio == 0.25
    assert pattern.severity == RiskSeverity.LOW


# ── 4. Development consistency ─────────────────────────────────────────────


def test_development_consistency():
    result = assess_development_consistency(_claims())
    assert result.settlement_cv is not None
    assert result.severity in (RiskSeverity.LOW, RiskSeverity.HIGH)


def test_development_reserve_adequacy_detects_inconsistency():
    claim = _claim("CL-1", loss=date(2024, 1, 1), incurred=100_000, paid=5_000, reserve=10_000)
    result = assess_development_consistency([claim])
    assert result.reserve_adequacy_ratio is not None
    assert result.reserve_adequacy_ratio > 1.3
    assert result.severity == RiskSeverity.HIGH


# ── 5. Frequency and severity ──────────────────────────────────────────────


def test_frequency_severity_reliability():
    profile = assess_frequency_severity(_claims())
    assert profile.claim_count == 4
    assert profile.frequency_per_year is not None
    assert profile.average_severity is not None
    assert profile.small_claim_ratio == 1.0
    assert profile.reliability > 0.0


def test_frequency_severity_empty():
    profile = assess_frequency_severity([])
    assert profile.claim_count == 0
    assert profile.detail == "No claims to profile"


# ── 6. Reopened claims potential ───────────────────────────────────────────


def test_reopened_potential_detects_reopens():
    today = date(2024, 1, 1)
    claims = [
        _claim("CL-1", loss=today - timedelta(days=100), reopened=True),
        _claim("CL-2", loss=today - timedelta(days=90)),
    ]
    result = assess_reopened_potential(claims)
    assert result.reopened_count == 1
    assert result.severity == RiskSeverity.MODERATE


# ── 7. Operational change detection ────────────────────────────────────────


def test_operational_change_detection():
    bundle = _bundle([])
    bundle.unstructured = [
        type(
            "Doc",
            (),
            {
                "document_type": "supplemental",
                "raw_text": "The carrier completed a claims system conversion last year, which may distort loss history.",
                "extracted_fields": {},
            },
        )()
    ]
    changes = detect_operational_changes(bundle)
    assert any("system conversion" in c.marker for c in changes)


# ── 8. Reasonableness check ────────────────────────────────────────────────


def test_reasonableness_ratio():
    claims = _claims()
    result = check_reasonableness(claims, premium=100_000, expected_loss_ratio=0.65)
    assert result.loss_ratio is not None
    assert result.is_reasonable is True


def test_reasonableness_out_of_band():
    claim = _claim("CL-1", loss=date(2024, 1, 1), incurred=80_000)
    result = check_reasonableness([claim], premium=10_000, expected_loss_ratio=0.65)
    assert result.loss_ratio == 8.0
    assert result.is_reasonable is False


# ── 9. Multi-method reserve study ──────────────────────────────────────────


def test_reserve_study_two_methods():
    claims = _claims()
    study = run_reserve_study(claims, premium=100_000, expected_loss_ratio=0.65)
    assert len(study.estimates) == 2
    methods = {e.method for e in study.estimates}
    assert methods == {ReservingMethod.PAID_INCURRED_DEVELOPMENT, ReservingMethod.LOSS_RATIO_BORNHUETTER_FERGUSON}
    assert study.range_low <= study.recommended <= study.range_high
    assert study.case_reserves > 0


def test_reserve_study_bf_bounded_below():
    claims = [_claim("CL-1", loss=date(2024, 1, 1), incurred=1_000, paid=5_000, reserve=0)]
    study = run_reserve_study(claims, premium=10_000, expected_loss_ratio=0.5)
    bf = [e for e in study.estimates if e.method == ReservingMethod.LOSS_RATIO_BORNHUETTER_FERGUSON][0]
    assert bf.outstanding_reserve == 0.0


# ── 10. Full standards review ──────────────────────────────────────────────


def test_full_review_summary():
    bundle = _bundle(_claims())
    review = run_reserving_standards_review(bundle, premium=100_000)
    assert review.organization is not None
    assert review.emergence is not None
    assert review.settlement is not None
    assert review.development is not None
    assert review.frequency_severity is not None
    assert review.reopened is not None
    assert review.reasonableness is not None
    assert review.reserve_study is not None
    assert review.worst_severity in (RiskSeverity.LOW, RiskSeverity.MODERATE, RiskSeverity.HIGH)
    assert "claims" in review.summary


# ── 11. ASOP 12 — classification review ────────────────────────────────────


def _clean_characteristics() -> list[RiskCharacteristic]:
    return [
        RiskCharacteristic(name="Age of building", is_objective=True, related_to_expected_cost=True, has_demonstrated_relationship=True, benchmark_group="Standard construction"),
        RiskCharacteristic(name="Protection class", is_objective=True, related_to_expected_cost=True, has_demonstrated_relationship=True, benchmark_group="PC 1-3"),
    ]


def test_asop12_passes_clean_scheme():
    review = review_classification(
        _clean_characteristics(),
        policy_count=100,
        expected_cost_per_class={"A": 500.0, "B": 200.0},
        acceptability=[ClassAcceptability(class_code="A", line="gl", acceptability=AcceptabilityCode.STANDARD)],
    )
    assert review.overall == ClassificationStatus.PASS
    assert review.checks["q1_correlation"] == ClassificationStatus.PASS
    assert review.checks["q6_credibility"] == ClassificationStatus.PASS


def test_asop12_fails_unsupported_characteristics():
    review = review_classification(
        [RiskCharacteristic(name="Intuition factor", related_to_expected_cost=True, has_demonstrated_relationship=False)],
        policy_count=5,
    )
    assert review.checks["q2_superfluous"] == ClassificationStatus.FLAG
    assert review.checks["q6_credibility"] == ClassificationStatus.FLAG  # sqrt(5/30) < 0.5


def test_asop12_detects_impermissible_surrogate():
    review = review_classification(
        [RiskCharacteristic(name="Credit score", related_to_expected_cost=True, has_demonstrated_relationship=True)],
        policy_count=100,
    )
    assert review.checks["q4_surrogate"] == ClassificationStatus.FAIL
    assert any(s.surrogate_for == "race" for s in review.surrogate_findings)


def test_asop12_single_surrogate_helper():
    finding = check_surrogate("Zip code")
    assert finding is not None
    assert finding.surrogate_for == "race"
    assert check_surrogate("Sprinklered building") is None


def test_asop12_decline_without_mitigation_flagged():
    declined_no_conditions = ClassAcceptability(class_code="X", line="gl", acceptability=AcceptabilityCode.DECLINE)
    review = review_classification(
        _clean_characteristics(),
        policy_count=100,
        expected_cost_per_class={"A": 500.0, "B": 200.0},
        acceptability=[declined_no_conditions],
    )
    assert review.checks["q8_decline_vs_mitigation"] == ClassificationStatus.FLAG
    assert "exclusionary riders" in review.findings[-1]


def test_asop12_no_data_fails_credibility():
    review = review_classification([], policy_count=0)
    assert review.checks["q6_credibility"] == ClassificationStatus.FAIL
    assert review.overall == ClassificationStatus.FAIL


# ── 12. Risk analyst reserving hook ────────────────────────────────────────


def test_risk_analyst_flags_slow_emergence_and_operational_changes():
    from insureflow.agents.risk_analyst import RiskAnalystAgent

    claims = [
        ClaimRecord(
            claim_id="C1",
            date_of_loss=date(2023, 1, 1),
            date_reported=date(2023, 10, 1),
            date_closed=date(2024, 1, 1),
            line_of_business="general_liability",
            cause="slip and fall",
            incurred_amount=100_000,
            paid_amount=60_000,
            open_reserve=40_000,
            claim_status=ClaimStatus.CLOSED,
        )
    ]
    bundle = SubmissionBundle(
        bundle_id="agent-reserving",
        structured=StructuredSubmission(
            submission_id="agent-reserving-sub",
            named_insured=NamedInsured(legal_name="Slow Emergence Co."),
            risk_profile=RiskProfile(prior_claims=claims),
        ),
        unstructured=[
            UnstructuredSubmission(
                submission_id="agent-reserving-doc",
                document_type="supplemental",
                raw_text="A claims system conversion was completed last quarter.",
            )
        ],
    )
    result = RiskAnalystAgent().run(bundle, premium=150_000)
    titles = [f.title for f in result.findings]
    assert any("reserving" in t.lower() for t in titles)
    assert any("Operational changes" in t for t in titles)


def test_risk_analyst_no_reserving_finding_without_claims():
    from insureflow.agents.risk_analyst import RiskAnalystAgent

    bundle = SubmissionBundle(
        bundle_id="agent-clean",
        structured=StructuredSubmission(
            submission_id="agent-clean-sub",
            named_insured=NamedInsured(legal_name="Clean Co."),
            risk_profile=RiskProfile(),
        ),
    )
    result = RiskAnalystAgent().run(bundle)
    assert all("reserving" not in f.title.lower() for f in result.findings)
