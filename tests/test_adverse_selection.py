"""Tests for the adverse-selection screen (purpose of underwriting doctrine)."""

from __future__ import annotations

from datetime import date

from insureflow.agents.adverse_selection_agent import AdverseSelectionAgent
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
)
from insureflow.oracles.cat_model_client import CATExposureResult, CATModelResult
from insureflow.underwriting.adverse_selection import (
    AdverseSelectionSignalType,
    assess_adverse_selection,
)


def _exposure(
    state: str,
    zip_code: str,
    *,
    in_flood_plain: bool = False,
    in_coastal_zone: bool = False,
    in_wildfire_zone: bool = False,
    flood: float = 0.0,
    hurricane: float = 0.0,
    wildfire: float = 0.0,
) -> CATExposureResult:
    return CATExposureResult(
        address="1 Main St",
        city="Testville",
        state=state,
        zip_code=zip_code,
        flood_risk_score=flood,
        hurricane_risk_score=hurricane,
        wildfire_risk_score=wildfire,
        earthquake_risk_score=0.05,
        combined_cat_score=max(flood, hurricane, wildfire),
        in_flood_plain=in_flood_plain,
        in_coastal_zone=in_coastal_zone,
        in_wildfire_zone=in_wildfire_zone,
    )


def _cat(*exposures: CATExposureResult) -> CATModelResult:
    return CATModelResult(exposures=list(exposures))


def _bundle(
    state: str,
    zip_code: str,
    coverages: list[str],
    *,
    prior_claims: list[ClaimRecord] | None = None,
    effective_date: date | None = None,
    loss_run_claims: list[ClaimRecord] | None = None,
) -> SubmissionBundle:
    risk_profile = RiskProfile(naics_code="452210", occupancy_type="retail")
    if prior_claims:
        risk_profile = risk_profile.model_copy(update={"prior_claims": prior_claims})
    financial = None
    if loss_run_claims:
        financial = FinancialData(
            loss_run=LossRunData(
                total_claims=len(loss_run_claims),
                total_incurred=sum(c.incurred_amount for c in loss_run_claims),
                claims=loss_run_claims,
            )
        )
    period = None
    if effective_date:
        period = PolicyPeriod(effective_date=effective_date, expiration_date=date(2027, 1, 1))
    return SubmissionBundle(
        bundle_id="adverse-test",
        structured=StructuredSubmission(
            submission_id="adverse-sub",
            named_insured=NamedInsured(legal_name="Testco LLC"),
            coverages=[CoverageDetail(coverage_type=name, limit_amount=1_000_000, premium=10_000, deductible=5_000) for name in coverages],
            locations=[LocationData(address="1 Main St", city="Testville", state=state, zip_code=zip_code, building_value=1_500_000)],
            risk_profile=risk_profile,
            financial=financial,
            policy_period=period,
            broker=BrokerInfo(broker_name="Acme Brokerage"),
        ),
    )


def _claim(days_ago: int) -> ClaimRecord:
    return ClaimRecord(
        claim_id=f"cl-{days_ago}",
        date_of_loss=date(2025, 11, 1),
        line_of_business="property",
        cause="water damage",
        incurred_amount=150_000,
        claim_status=ClaimStatus.CLOSED,
    )


def test_clean_applicant_has_no_signals() -> None:
    bundle = _bundle("IL", "60601", ["general_liability", "commercial_property"])
    result = assess_adverse_selection(
        bundle,
        cat_result=_cat(_exposure("IL", "60601")),
    )
    assert result.status == "low"
    assert result.adverse_selection_score == 0.0
    assert result.signals == []


def test_flood_plain_buyer_is_the_doctrine_example() -> None:
    bundle = _bundle("FL", "33101", ["flood"])
    result = assess_adverse_selection(
        bundle,
        cat_result=_cat(_exposure("FL", "33101", in_flood_plain=True, in_coastal_zone=True, flood=0.6, hurricane=0.85)),
    )
    assert result.status == "high"
    types = result.signal_types
    assert AdverseSelectionSignalType.HAZARD_ZONE_DEMAND.value in types
    assert AdverseSelectionSignalType.EXCLUDED_ZONE_DEMAND.value in types
    assert AdverseSelectionSignalType.BARE_CAT_COVER.value in types
    assert result.adverse_selection_score == 1.0


def test_hazard_demand_without_exclusion_stays_high() -> None:
    bundle = _bundle("LA", "70001", ["flood", "general_liability"])
    result = assess_adverse_selection(
        bundle,
        cat_result=_cat(_exposure("LA", "70001", in_flood_plain=True, in_coastal_zone=True, flood=0.7, hurricane=0.75)),
    )
    assert result.status == "high"
    assert result.signal_types == [AdverseSelectionSignalType.HAZARD_ZONE_DEMAND.value]
    # No appetite exclusion for LA (only additional CAT modeling is required).
    assert AdverseSelectionSignalType.EXCLUDED_ZONE_DEMAND.value not in result.signal_types


def test_loss_motivated_seeking_flags_without_cat_data() -> None:
    bundle = _bundle("IL", "60601", ["general_liability"], prior_claims=[_claim(400)])
    result = assess_adverse_selection(bundle, cat_result=None)
    assert result.status == "flagged"
    assert result.signal_types == [AdverseSelectionSignalType.LOSS_MOTIVATED_SEEKING.value]
    assert result.adverse_selection_score == 0.5


def test_loss_motivated_recency_is_evidenced() -> None:
    bundle = _bundle(
        "IL",
        "60601",
        ["general_liability"],
        prior_claims=[_claim(400)],
        effective_date=date(2026, 1, 1),
    )
    result = assess_adverse_selection(bundle, cat_result=None)
    signal = result.signals[0]
    assert any("days before the coverage effective date" in e for e in signal.evidence)


def test_excluded_zone_escalation_on_coastal_tx() -> None:
    bundle = _bundle("TX", "78000", ["wind"])
    result = assess_adverse_selection(
        bundle,
        cat_result=_cat(_exposure("TX", "78000", in_flood_plain=True, in_coastal_zone=True, flood=0.5, hurricane=0.55)),
    )
    assert result.status == "high"
    types = result.signal_types
    assert AdverseSelectionSignalType.HAZARD_ZONE_DEMAND.value in types
    assert AdverseSelectionSignalType.EXCLUDED_ZONE_DEMAND.value in types


def test_bare_cat_cover_alone_flags() -> None:
    bundle = _bundle("NY", "10001", ["earthquake"])
    result = assess_adverse_selection(
        bundle,
        cat_result=_cat(_exposure("NY", "10001")),
    )
    assert result.status == "flagged"
    assert result.signal_types == [AdverseSelectionSignalType.BARE_CAT_COVER.value]
    assert result.adverse_selection_score == 0.3


def test_no_structured_data_is_inert() -> None:
    bundle = SubmissionBundle(bundle_id="empty")
    result = assess_adverse_selection(bundle, cat_result=None)
    assert result.status == "low"
    assert result.signals == []


def test_agent_flags_high_for_flood_plain_demand() -> None:
    from insureflow.oracles.cat_model_client import CatastropheModelClient

    agent = AdverseSelectionAgent(cat_model=CatastropheModelClient())
    bundle = _bundle("FL", "33101", ["flood"])
    result = agent.run(bundle, org_id="default")
    assert agent.last_assessment is not None
    assert agent.last_assessment.status == "high"
    finding = result.findings[0]
    assert finding.severity == RiskSeverity.HIGH
    assert "disproportionately motivated" in finding.title
    assert finding.source_value is not None and finding.source_value >= 0.6


def test_agent_clean_applicant_is_low() -> None:
    from insureflow.oracles.cat_model_client import CatastropheModelClient

    agent = AdverseSelectionAgent(cat_model=CatastropheModelClient())
    bundle = _bundle("IL", "60601", ["general_liability", "commercial_property"])
    result = agent.run(bundle, org_id="default")
    assert agent.last_assessment is not None
    assert agent.last_assessment.status == "low"
    assert result.findings[0].severity == RiskSeverity.LOW
    assert "no disproportionate motivation" in result.findings[0].title


def test_agent_no_structured_data_emits_no_findings() -> None:
    from insureflow.oracles.cat_model_client import CatastropheModelClient

    agent = AdverseSelectionAgent(cat_model=CatastropheModelClient())
    bundle = SubmissionBundle(bundle_id="unstructured-only")
    result = agent.run(bundle, org_id="default")
    assert result.findings == []
    assert agent.last_assessment is not None
    assert agent.last_assessment.status == "low"
