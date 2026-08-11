"""Tests for the moral-hazard / character screen (judge-of-people doctrine)."""

from __future__ import annotations

from datetime import date

from insureflow.agents.moral_hazard_agent import MoralHazardAgent
from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import (
    BrokerInfo,
    ClaimRecord,
    ClaimStatus,
    CoverageDetail,
    FinancialData,
    LocationData,
    LossRunData,
    NamedInsured,
    PolicyPeriod,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)
from insureflow.underwriting.moral_hazard import MoralHazardSignalType, assess_moral_hazard


def _claim(
    claim_id: str,
    *,
    days_offset: int = 0,
    cause: str = "water damage",
    notes: str = "",
    incurred: float = 50_000,
    effective_date: date | None = None,
) -> ClaimRecord:
    from datetime import timedelta

    date_of_loss = (effective_date + timedelta(days=days_offset)) if effective_date is not None else date(2025, 11, 1)
    return ClaimRecord(
        claim_id=claim_id,
        date_of_loss=date_of_loss,
        line_of_business="property",
        cause=cause,
        incurred_amount=incurred,
        claim_status=ClaimStatus.CLOSED,
        notes=notes,
    )


def _bundle(
    *,
    effective_date: date | None = None,
    claims: list[ClaimRecord] | None = None,
    loss_run_claims: list[ClaimRecord] | None = None,
    prior_losses: list[dict[str, str]] | None = None,
    doc_text: str | None = None,
    credit_rating: str | None = None,
) -> SubmissionBundle:
    risk_profile = RiskProfile(naics_code="452210", occupancy_type="retail")
    if claims:
        risk_profile = risk_profile.model_copy(update={"prior_claims": claims})
    financial = None
    if loss_run_claims or credit_rating or prior_losses:
        financial = FinancialData(
            prior_losses=prior_losses or [],
            credit_rating=credit_rating,
            loss_run=LossRunData(
                total_claims=len(loss_run_claims or []),
                total_incurred=sum(c.incurred_amount for c in (loss_run_claims or [])),
                claims=loss_run_claims or [],
            ),
        )
    period = None
    if effective_date:
        period = PolicyPeriod(effective_date=effective_date, expiration_date=date(2027, 1, 1))
    unstructured = []
    if doc_text:
        unstructured.append(UnstructuredSubmission(submission_id="doc-1", raw_text=doc_text, document_type="supplemental"))
    return SubmissionBundle(
        bundle_id="moral-test",
        structured=StructuredSubmission(
            submission_id="moral-sub",
            named_insured=NamedInsured(legal_name="Testco LLC"),
            coverages=[CoverageDetail(coverage_type="commercial_property", limit_amount=1_000_000, premium=10_000, deductible=5_000)],
            locations=[LocationData(address="1 Main St", city="Testville", state="IL", zip_code="60601", building_value=1_500_000)],
            risk_profile=risk_profile,
            financial=financial,
            policy_period=period,
            broker=BrokerInfo(broker_name="Acme Brokerage"),
        ),
        unstructured=unstructured,
    )


def test_clean_applicant_has_no_signals() -> None:
    bundle = _bundle()
    result = assess_moral_hazard(bundle)
    assert result.status == "low"
    assert result.moral_hazard_score == 0.0
    assert result.signals == []


def test_intentional_misrepresentation_is_critical() -> None:
    claim = _claim("cl-1", notes="Claim was NOT disclosed on the broker application")
    bundle = _bundle(loss_run_claims=[claim], prior_losses=[{"claim_id": "cl-1"}])
    result = assess_moral_hazard(bundle)
    assert result.status == "critical"
    assert result.signal_types == [MoralHazardSignalType.INTENTIONAL_MISREPRESENTATION.value]
    assert result.moral_hazard_score == 1.0


def test_non_disclosed_losses_are_high() -> None:
    disclosed = _claim("cl-1")
    hidden = _claim("cl-2")
    bundle = _bundle(
        loss_run_claims=[disclosed, hidden],
        prior_losses=[{"claim_id": "cl-1"}],
    )
    result = assess_moral_hazard(bundle)
    assert result.status == "high"
    assert MoralHazardSignalType.NON_DISCLOSED_LOSSES.value in result.signal_types


def test_prior_cancellation_is_high() -> None:
    bundle = _bundle(doc_text="The prior carrier cancelled this risk for cause in 2024.")
    result = assess_moral_hazard(bundle)
    assert result.status == "high"
    assert result.signal_types == [MoralHazardSignalType.PRIOR_CANCELLATION.value]


def test_bankruptcy_marker_is_high() -> None:
    bundle = _bundle(doc_text="Owner filed Chapter 7 bankruptcy in 2023.")
    result = assess_moral_hazard(bundle)
    assert result.status == "high"
    signal = result.signals[0]
    assert signal.signal_type == MoralHazardSignalType.FINANCIAL_DISTRESS
    assert signal.severity == RiskSeverity.HIGH


def test_distress_marker_is_flagged() -> None:
    bundle = _bundle(doc_text="A tax lien was filed against the business.")
    result = assess_moral_hazard(bundle)
    assert result.status == "flagged"
    signal = result.signals[0]
    assert signal.severity == RiskSeverity.MODERATE


def test_claim_immediately_after_inception_is_high() -> None:
    claim = _claim("cl-1", days_offset=10, cause="water damage", effective_date=date(2026, 1, 1))
    bundle = _bundle(effective_date=date(2026, 1, 1), loss_run_claims=[claim])
    result = assess_moral_hazard(bundle)
    assert result.status == "high"
    assert MoralHazardSignalType.SUSPICIOUS_CLAIM_TIMING.value in result.signal_types
    signal = next(s for s in result.signals if s.signal_type == MoralHazardSignalType.SUSPICIOUS_CLAIM_TIMING)
    assert signal.severity == RiskSeverity.HIGH


def test_suspicious_cause_is_critical() -> None:
    claim = _claim("cl-1", cause="suspected arson", notes="investigation ongoing")
    bundle = _bundle(loss_run_claims=[claim], prior_losses=[{"claim_id": "cl-1"}])
    result = assess_moral_hazard(bundle)
    assert result.status == "critical"
    assert MoralHazardSignalType.SUSPICIOUS_CLAIM_CAUSE.value in result.signal_types
    signal = next(s for s in result.signals if s.signal_type == MoralHazardSignalType.SUSPICIOUS_CLAIM_CAUSE)
    assert signal.severity == RiskSeverity.CRITICAL


def test_entity_churn_is_flagged() -> None:
    bundle = _bundle(doc_text="The successor in interest reorganized the entity in 2025.")
    result = assess_moral_hazard(bundle)
    assert result.status == "flagged"
    assert MoralHazardSignalType.ENTITY_CHURN.value in result.signal_types


def test_no_structured_data_is_inert() -> None:
    bundle = SubmissionBundle(bundle_id="empty")
    result = assess_moral_hazard(bundle)
    assert result.status == "low"
    assert result.signals == []


def test_agent_clean_applicant_is_low() -> None:
    agent = MoralHazardAgent()
    bundle = _bundle()
    result = agent.run(bundle, org_id="default")
    assert agent.last_assessment is not None
    assert agent.last_assessment.status == "low"
    finding = result.findings[0]
    assert finding.severity == RiskSeverity.LOW
    assert "no character red flags" in finding.title


def test_agent_critical_applicant_forces_declination_signal() -> None:
    agent = MoralHazardAgent()
    claim = _claim("cl-1", notes="Claim was NOT disclosed on the broker application")
    bundle = _bundle(loss_run_claims=[claim], prior_losses=[{"claim_id": "cl-1"}])
    result = agent.run(bundle, org_id="default")
    assert agent.last_assessment is not None
    assert agent.last_assessment.status == "critical"
    finding = result.findings[0]
    assert finding.severity == RiskSeverity.CRITICAL
    assert "declination" in finding.title
    assert finding.category == "moral_hazard"
    assert finding.source_value == 1.0
    assert any("NOT disclosed" in e for e in finding.evidence)


def test_agent_no_structured_data_emits_no_findings() -> None:
    agent = MoralHazardAgent()
    bundle = SubmissionBundle(bundle_id="unstructured-only")
    result = agent.run(bundle, org_id="default")
    assert result.findings == []
    assert agent.last_assessment is not None
    assert agent.last_assessment.status == "low"
