from __future__ import annotations

from datetime import date
from typing import Any

from insureflow.agents.compliance_agent import ComplianceAgent
from insureflow.agents.fraud_detection_agent import FraudDetectionAgent
from insureflow.agents.loss_run_analyst import LossRunAnalystAgent
from insureflow.agents.risk_analyst import RiskAnalystAgent
from insureflow.agents.supervisor import SupervisorAgent
from insureflow.agents.tools import UnderwritingTools
from insureflow.agents.uw_decision_agent import UWDecisionAgent
from insureflow.models.agents import AgentResult, AgentType, Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import (
    ClaimRecord,
    ClaimStatus,
    CoverageDetail,
    FinancialData,
    LocationData,
    LossRunData,
    NamedInsured,
    RiskProfile,
    ScheduleItem,
    ScheduleOfValues,
    StructuredSubmission,
    SubmissionBundle,
    SubmissionStatus,
)


def _make_bundle(
    claims: list[Any] | None = None,
    coverages: list[Any] | None = None,
    locations: list[Any] | None = None,
    risk_profile: dict[str, Any] | None = None,
    sovs: list[Any] | None = None,
    structured_claims: list[Any] | None = None,
    insured_name: str = "Test Corp",
    loss_run: LossRunData | None = None,
    credit_rating: str | None = None,
) -> SubmissionBundle:
    if claims is not None and loss_run is None:
        loss_run = LossRunData(
            total_claims=len(claims),
            total_incurred=sum(c.incurred_amount for c in claims),
            total_paid=sum(c.paid_amount for c in claims),
            claims=claims,
        )

    fi = FinancialData(loss_run=loss_run, credit_rating=credit_rating)
    if structured_claims:
        fi.prior_losses = structured_claims

    return SubmissionBundle(
        bundle_id="test-bundle",
        status=SubmissionStatus.COMPLETED,
        structured=StructuredSubmission(
            submission_id="test-sub",
            named_insured=NamedInsured(legal_name=insured_name),
            coverages=coverages or [],
            locations=locations or [],
            risk_profile=RiskProfile(**(risk_profile or {})),
            financial=fi,
            schedule_of_values=sovs or [],
        ),
    )


class TestUnderwritingTools:
    def test_loss_ratio(self) -> None:
        assert UnderwritingTools.loss_ratio(50_000, 100_000) == 0.5
        assert UnderwritingTools.loss_ratio(0, 100_000) == 0.0
        assert UnderwritingTools.loss_ratio(50_000, 0) == 0.0

    def test_claim_frequency(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="test",
                incurred_amount=1000,
            )
        ]
        assert UnderwritingTools.claim_frequency(claims, 5.0) == 0.2
        assert UnderwritingTools.claim_frequency([], 5.0) == 0.0

    def test_average_severity(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="t",
                incurred_amount=100_000,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 2, 1),
                line_of_business="WC",
                cause="t",
                incurred_amount=300_000,
            ),
        ]
        assert UnderwritingTools.average_severity(claims) == 200_000.0

    def test_large_loss_ratio(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="t",
                incurred_amount=50_000,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 2, 1),
                line_of_business="WC",
                cause="t",
                incurred_amount=200_000,
            ),
        ]
        assert UnderwritingTools.large_loss_ratio(claims) == 0.5

    def test_open_claim_ratio(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="t",
                incurred_amount=1000,
                claim_status=ClaimStatus.OPEN,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 2, 1),
                line_of_business="WC",
                cause="t",
                incurred_amount=2000,
                claim_status=ClaimStatus.CLOSED,
            ),
        ]
        assert UnderwritingTools.open_claim_ratio(claims) == 0.5

    def test_litigation_ratio(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="t",
                incurred_amount=1000,
                claim_status=ClaimStatus.PENDING_LITIGATION,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 2, 1),
                line_of_business="WC",
                cause="t",
                incurred_amount=2000,
                claim_status=ClaimStatus.CLOSED,
            ),
        ]
        assert UnderwritingTools.litigation_ratio(claims) == 0.5

    def test_protection_class_risk(self) -> None:
        assert UnderwritingTools.protection_class_risk(3) == RiskSeverity.LOW
        assert UnderwritingTools.protection_class_risk(5) == RiskSeverity.MODERATE
        assert UnderwritingTools.protection_class_risk(7) == RiskSeverity.HIGH
        assert UnderwritingTools.protection_class_risk(9) == RiskSeverity.CRITICAL
        assert UnderwritingTools.protection_class_risk(None) == RiskSeverity.MODERATE

    def test_sprinkler_risk(self) -> None:
        assert UnderwritingTools.sprinkler_risk(True) == RiskSeverity.LOW
        assert UnderwritingTools.sprinkler_risk(False) == RiskSeverity.HIGH
        assert UnderwritingTools.sprinkler_risk(None) == RiskSeverity.MODERATE

    def test_year_built_risk(self) -> None:
        assert UnderwritingTools.year_built_risk(2020) == RiskSeverity.LOW
        assert UnderwritingTools.year_built_risk(2000) == RiskSeverity.MODERATE
        assert UnderwritingTools.year_built_risk(1980) == RiskSeverity.HIGH
        assert UnderwritingTools.year_built_risk(1950) == RiskSeverity.CRITICAL

    def test_total_insurable_value(self) -> None:
        locs = [
            LocationData(
                address="A",
                city="C",
                state="S",
                zip_code="Z",
                building_value=1_000_000,
                contents_value=500_000,
                bi_value=250_000,
            ),
            LocationData(address="B", city="C", state="S", zip_code="Z", building_value=2_000_000),
        ]
        assert UnderwritingTools.total_insurable_value(locs) == 3_750_000

    def test_find_non_disclosed_losses(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="t",
                incurred_amount=1000,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 2, 1),
                line_of_business="WC",
                cause="t",
                incurred_amount=2000,
            ),
        ]
        structured = [{"claim_id": "C1"}]
        nd = UnderwritingTools.find_non_disclosed_losses(claims, structured)
        assert len(nd) == 1
        assert nd[0].claim_id == "C2"

    def test_assess_overall_severity(self) -> None:
        assert UnderwritingTools.assess_overall_severity([]) == RiskSeverity.LOW
        findings = [Finding(title="t", description="d", severity=RiskSeverity.HIGH)]
        assert UnderwritingTools.assess_overall_severity(findings) == RiskSeverity.HIGH
        findings.append(Finding(title="t2", description="d2", severity=RiskSeverity.CRITICAL))
        assert UnderwritingTools.assess_overall_severity(findings) == RiskSeverity.CRITICAL


class TestRiskAnalystAgent:
    def test_low_risk_construction(self) -> None:
        bundle = _make_bundle(
            risk_profile={"construction_type": "steel", "sprinklered": True, "protection_class": 3},
            locations=[
                LocationData(
                    address="1 Main",
                    city="City",
                    state="S",
                    zip_code="Z",
                    year_built=2015,
                    building_value=1_000_000,
                    square_footage=10_000,
                )
            ],
        )
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        assert result.success
        sevs = [f.severity for f in result.findings]
        assert RiskSeverity.CRITICAL not in sevs

    def test_high_risk_construction(self) -> None:
        bundle = _make_bundle(
            risk_profile={
                "construction_type": "wood frame",
                "sprinklered": False,
                "protection_class": 8,
            },
        )
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        assert result.success
        sevs = [f.severity for f in result.findings]
        assert RiskSeverity.HIGH in sevs

    def test_aging_building(self) -> None:
        bundle = _make_bundle(
            risk_profile={},
            locations=[LocationData(address="Old", city="C", state="S", zip_code="Z", year_built=1950)],
        )
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        assert any("Aging" in f.title for f in result.findings)

    def test_no_risk_profile(self) -> None:
        bundle = _make_bundle()
        bundle.structured = None
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        assert result.success

    def test_credit_rating_low(self) -> None:
        bundle = _make_bundle(credit_rating="750")
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        findings = [f for f in result.findings if f.category == "credit"]
        assert len(findings) == 1
        assert findings[0].severity == RiskSeverity.LOW

    def test_credit_rating_critical(self) -> None:
        bundle = _make_bundle(credit_rating="D")
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        findings = [f for f in result.findings if f.category == "credit"]
        assert len(findings) == 1
        assert findings[0].severity == RiskSeverity.CRITICAL

    def test_credit_rating_missing(self) -> None:
        bundle = _make_bundle()
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        findings = [f for f in result.findings if f.category == "credit"]
        assert len(findings) == 0

    def test_credit_rating_numeric_moderate(self) -> None:
        bundle = _make_bundle(credit_rating="680")
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        findings = [f for f in result.findings if f.category == "credit"]
        assert len(findings) == 1
        assert findings[0].severity == RiskSeverity.MODERATE

    def test_credit_rating_numeric_high(self) -> None:
        bundle = _make_bundle(credit_rating="580")
        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        findings = [f for f in result.findings if f.category == "credit"]
        assert len(findings) == 1
        assert findings[0].severity == RiskSeverity.HIGH


class TestLossRunAnalystAgent:
    def test_no_loss_run(self) -> None:
        bundle = _make_bundle()
        bundle.structured = None
        agent = LossRunAnalystAgent()
        result = agent.run(bundle)
        assert any("No loss run" in f.title for f in result.findings)

    def test_high_frequency(self) -> None:
        from datetime import timedelta

        base = date(2022, 1, 1)
        claims = [
            ClaimRecord(
                claim_id=f"C{i}",
                date_of_loss=base + timedelta(days=i * 60),
                line_of_business="GL",
                cause="test",
                incurred_amount=10_000,
            )
            for i in range(18)
        ]
        bundle = _make_bundle(claims=claims)
        agent = LossRunAnalystAgent()
        result = agent.run(bundle)
        assert any("High claim frequency" in f.title for f in result.findings)

    def test_high_severity(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="test",
                incurred_amount=500_000,
            ),
        ]
        bundle = _make_bundle(claims=claims)
        agent = LossRunAnalystAgent()
        result = agent.run(bundle)
        assert any("High average claim severity" in f.title for f in result.findings)

    def test_large_loss_concentration(self) -> None:
        claims = [
            ClaimRecord(
                claim_id=f"C{i}",
                date_of_loss=date(2024, 1, i),
                line_of_business="GL",
                cause="test",
                incurred_amount=200_000,
            )
            for i in range(1, 6)
        ]
        bundle = _make_bundle(claims=claims)
        agent = LossRunAnalystAgent()
        result = agent.run(bundle)
        assert any("Concentration" in f.title for f in result.findings)

    def test_litigation_claim(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="L1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="injury",
                incurred_amount=100_000,
                claim_status=ClaimStatus.PENDING_LITIGATION,
            ),
        ]
        bundle = _make_bundle(claims=claims)
        agent = LossRunAnalystAgent()
        result = agent.run(bundle)
        assert any("litigation" in f.title.lower() for f in result.findings)

    def test_non_disclosed_notes(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="ND1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="slip and fall",
                incurred_amount=50_000,
                notes="This loss was NOT disclosed on the current broker application",
            ),
        ]
        bundle = _make_bundle(claims=claims)
        agent = LossRunAnalystAgent()
        result = agent.run(bundle)
        assert any("non-disclosed" in f.title.lower() for f in result.findings)

    def test_open_exposure(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="O1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="test",
                incurred_amount=100_000,
                paid_amount=50_000,
                open_reserve=50_000,
                claim_status=ClaimStatus.OPEN,
            ),
        ]
        bundle = _make_bundle(claims=claims)
        agent = LossRunAnalystAgent()
        result = agent.run(bundle)
        assert any("Open claims" in f.title for f in result.findings)


class TestComplianceAgent:
    def test_no_coverages(self) -> None:
        bundle = _make_bundle()
        bundle.structured = None
        agent = ComplianceAgent()
        result = agent.run(bundle)
        assert not result.success or any("No coverage" in f.title for f in result.findings)

    def test_adequate_limits(self) -> None:
        covs = [
            CoverageDetail(coverage_type="Property", limit_amount=10_000_000, deductible=10_000, premium=50_000),
        ]
        bundle = _make_bundle(
            coverages=covs,
            locations=[
                LocationData(
                    address="A",
                    city="C",
                    state="S",
                    zip_code="Z",
                    building_value=5_000_000,
                    contents_value=2_000_000,
                ),
            ],
        )
        agent = ComplianceAgent()
        result = agent.run(bundle)
        high_sev = [f for f in result.findings if f.severity == RiskSeverity.HIGH]
        assert len(high_sev) == 0

    def test_inadequate_limits(self) -> None:
        covs = [
            CoverageDetail(coverage_type="Property", limit_amount=1_000_000, deductible=10_000, premium=50_000),
        ]
        bundle = _make_bundle(
            coverages=covs,
            locations=[
                LocationData(
                    address="A",
                    city="C",
                    state="S",
                    zip_code="Z",
                    building_value=5_000_000,
                    contents_value=5_000_000,
                ),
            ],
        )
        agent = ComplianceAgent()
        result = agent.run(bundle)
        assert any("inadequate" in f.title.lower() for f in result.findings)

    def test_high_deductible(self) -> None:
        covs = [
            CoverageDetail(coverage_type="Property", limit_amount=1_000_000, deductible=200_000, premium=50_000),
        ]
        bundle = _make_bundle(coverages=covs)
        agent = ComplianceAgent()
        result = agent.run(bundle)
        assert any("High" in f.title and "deductible" in f.title.lower() for f in result.findings)

    def test_coverage_gaps(self) -> None:
        covs = [
            CoverageDetail(coverage_type="Property", limit_amount=1_000_000, deductible=10_000, premium=50_000),
        ]
        bundle = _make_bundle(coverages=covs)
        agent = ComplianceAgent()
        result = agent.run(bundle)
        assert any("coverage gaps" in f.title.lower() for f in result.findings)

    def test_restrictive_sublimits(self) -> None:
        covs = [
            CoverageDetail(
                coverage_type="Property",
                limit_amount=10_000_000,
                deductible=10_000,
                premium=50_000,
                sublimits={"Ordinance or Law": 50_000},
            ),
        ]
        bundle = _make_bundle(coverages=covs)
        agent = ComplianceAgent()
        result = agent.run(bundle)
        assert any("sublimit" in f.title.lower() for f in result.findings)

    def test_recommendation_built(self) -> None:
        covs = [
            CoverageDetail(coverage_type="Property", limit_amount=100_000, deductible=10_000, premium=50_000),
        ]
        bundle = _make_bundle(
            coverages=covs,
            locations=[
                LocationData(address="A", city="C", state="S", zip_code="Z", building_value=5_000_000),
            ],
        )
        agent = ComplianceAgent()
        result = agent.run(bundle)
        assert result.recommendation is not None
        assert len(result.recommendation.conditions) > 0


class TestFraudDetectionAgent:
    def test_non_disclosed_claims(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="test",
                incurred_amount=50_000,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 2, 1),
                line_of_business="WC",
                cause="test",
                incurred_amount=100_000,
            ),
        ]
        bundle = _make_bundle(claims=claims, structured_claims=[{"claim_id": "C1"}])
        agent = FraudDetectionAgent()
        result = agent.run(bundle)
        assert any("Non-disclosed" in f.title for f in result.findings)

    def no_disclosed_flag_in_notes(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="ND1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="test",
                incurred_amount=50_000,
                notes="NOT DISCLOSED on application",
            ),
        ]
        bundle = _make_bundle(claims=claims)
        agent = FraudDetectionAgent()
        result = agent.run(bundle)
        assert any("non-disclosure" in f.title.lower() or "not disclosed" in f.description.lower() for f in result.findings)

    def test_valuation_discrepancy(self) -> None:
        bundle = _make_bundle(
            locations=[
                LocationData(
                    address="A",
                    city="C",
                    state="S",
                    zip_code="Z",
                    building_value=10_000_000,
                    contents_value=5_000_000,
                )
            ],
            sovs=[
                ScheduleOfValues(
                    schedule_type="Property",
                    coverage_type="Building",
                    items=[ScheduleItem(description="Building", value=3_000_000)],
                    total_value=3_000_000,
                )
            ],
        )
        agent = FraudDetectionAgent()
        result = agent.run(bundle)
        assert any("valuation" in f.title.lower() for f in result.findings)

    def test_entity_inconsistency(self) -> None:
        bundle = _make_bundle(insured_name="Test Corp")
        from insureflow.models.submissions import ExtractedField, UnstructuredSubmission

        bundle.unstructured = [
            UnstructuredSubmission(
                submission_id="u1",
                extracted_fields={
                    "named_insured": [
                        ExtractedField(
                            field_name="named_insured",
                            value="Test Corp LLC",
                            confidence=0.8,
                            context="report",
                        )
                    ]
                },
            )
        ]
        agent = FraudDetectionAgent()
        result = agent.run(bundle)
        assert any("Inconsistent entity" in f.title for f in result.findings)

    def test_recent_loss_cluster(self) -> None:
        from datetime import timedelta

        base = date(2026, 1, 1)
        claims = [
            ClaimRecord(
                claim_id=f"C{i}",
                date_of_loss=base + timedelta(days=i * 30),
                line_of_business="GL",
                cause="test",
                incurred_amount=10_000,
            )
            for i in range(3)
        ]
        bundle = _make_bundle(claims=claims)
        agent = FraudDetectionAgent()
        result = agent.run(bundle)
        assert any("Cluster" in f.title for f in result.findings)


class TestUWDecisionAgent:
    def test_accept_decision(self) -> None:
        UWDecisionAgent()
        result = AgentResult(
            agent_type=AgentType.RISK_ANALYST,
            agent_name="RiskAnalystAgent",
            findings=[
                Finding(
                    title="Clean risk",
                    description="No issues",
                    severity=RiskSeverity.LOW,
                    category="general",
                )
            ],
        )
        uw_agent = UWDecisionAgent()
        uw_result = uw_agent.run(_make_bundle(), agent_results={"RiskAnalystAgent": result})
        assert uw_result.recommendation is not None
        assert uw_result.recommendation.action == "accept"

    def test_refer_decision(self) -> None:
        agent = UWDecisionAgent()
        result = AgentResult(
            agent_type=AgentType.RISK_ANALYST,
            agent_name="RiskAnalystAgent",
            findings=[
                Finding(
                    title="High risk",
                    description="Issue found",
                    severity=RiskSeverity.HIGH,
                    category="general",
                )
            ],
        )
        uw_result = agent.run(_make_bundle(), agent_results={"RiskAnalystAgent": result})
        assert uw_result.recommendation is not None
        assert uw_result.recommendation.action == "refer"

    def test_critical_findings_refer_not_auto_decline(self) -> None:
        agent = UWDecisionAgent()
        result = AgentResult(
            agent_type=AgentType.FRAUD_DETECTION,
            agent_name="FraudDetectionAgent",
            findings=[
                Finding(
                    title="Fraud risk",
                    description="Material misrepresentation",
                    severity=RiskSeverity.CRITICAL,
                    category="fraud",
                )
            ],
        )
        uw_result = agent.run(_make_bundle(), agent_results={"FraudDetectionAgent": result})
        assert uw_result.recommendation is not None
        # Critical findings escalate to licensed UW; hard declines stay on appetite/moral/selection.
        assert uw_result.recommendation.action == "refer"

    def test_produce_memo(self) -> None:
        agent = UWDecisionAgent()
        agent_results = [
            AgentResult(
                agent_type=AgentType.RISK_ANALYST,
                agent_name="RiskAnalystAgent",
                findings=[
                    Finding(
                        title="Test finding",
                        description="desc",
                        severity=RiskSeverity.LOW,
                        category="test",
                    )
                ],
            ),
        ]
        uw_result = AgentResult(
            agent_type=AgentType.UW_DECISION,
            agent_name="UWDecisionAgent",
            findings=[],
            recommendation=agent._build_recommendation(),
        )
        bundle = _make_bundle()
        memo = agent.produce_underwriting_memo(bundle, agent_results, uw_result)
        assert memo.bundle_id == "test-bundle"
        assert memo.insured_name == "Test Corp"


class TestReActAgent:
    def test_fallback_to_deterministic_no_llm_key(self) -> None:
        bundle = _make_bundle(
            risk_profile={"construction_type": "steel", "sprinklered": True},
            coverages=[
                CoverageDetail(
                    coverage_type="Property",
                    limit_amount=1_000_000,
                    deductible=10_000,
                    premium=25_000,
                ),
            ],
            claims=[
                ClaimRecord(
                    claim_id="C1",
                    date_of_loss=date(2024, 1, 1),
                    line_of_business="GL",
                    cause="test",
                    incurred_amount=10_000,
                ),
            ],
        )
        from insureflow.agents.risk_analyst import RiskAnalystAgent

        agent = RiskAnalystAgent()
        result = agent.run(bundle)
        assert result.success
        assert len(result.findings) >= 0

    def test_tool_registry(self) -> None:
        bundle = _make_bundle(insured_name="Test Corp")
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle)
        tools = reg.list_tools()
        assert len(tools) >= 15
        names = [t["name"] for t in tools]
        assert "get_named_insured" in names
        assert "get_loss_run" in names
        assert "compute_claim_frequency" in names

        result = reg.call("get_named_insured")
        assert result == "Test Corp"

    def test_tool_registry_unknown_tool(self) -> None:
        bundle = _make_bundle()
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle)
        result = reg.call("nonexistent_tool")
        assert "error" in result

    def test_tool_get_risk_profile(self) -> None:
        bundle = _make_bundle(risk_profile={"construction_type": "steel", "sprinklered": True})
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle)
        result = reg.call("get_risk_profile")
        assert result is not None
        assert result.get("construction_type") == "steel"

    def test_tool_claim_frequency(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="t",
                incurred_amount=10_000,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 6, 1),
                line_of_business="WC",
                cause="t",
                incurred_amount=20_000,
            ),
        ]
        bundle = _make_bundle(claims=claims)
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle)
        result = reg.call("compute_claim_frequency")
        assert result["frequency"] == 0.4

    def test_tool_large_loss_ratio(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="t",
                incurred_amount=200_000,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 6, 1),
                line_of_business="WC",
                cause="t",
                incurred_amount=50_000,
            ),
        ]
        bundle = _make_bundle(claims=claims)
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle)
        result = reg.call("compute_large_loss_ratio")
        assert result["large_loss_ratio"] == 0.5

    def test_tool_non_disclosed(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="t",
                incurred_amount=10_000,
            ),
        ]
        bundle = _make_bundle(claims=claims, structured_claims=[{"claim_id": "C2"}])
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle)
        result = reg.call("check_non_disclosed_claims")
        assert result["non_disclosed_count"] == 1

    def test_tool_sov_vs_location(self) -> None:
        bundle = _make_bundle(
            locations=[LocationData(address="A", city="C", state="S", zip_code="Z", building_value=1_000_000)],
            sovs=[
                ScheduleOfValues(
                    schedule_type="Building",
                    coverage_type="Property",
                    items=[ScheduleItem(description="Bldg", value=500_000)],
                    total_value=500_000,
                )
            ],
        )
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle)
        result = reg.call("check_sov_vs_location_valuation")
        assert result["ratio"] == 0.5

    def test_tool_coverage_adequacy(self) -> None:
        covs = [
            CoverageDetail(coverage_type="Property", limit_amount=1_000_000, deductible=10_000, premium=25_000),
        ]
        bundle = _make_bundle(
            coverages=covs,
            locations=[
                LocationData(address="A", city="C", state="S", zip_code="Z", building_value=2_000_000),
            ],
        )
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle)
        result = reg.call("check_coverage_adequacy", coverage_type="Property")
        assert result["status"] == "inadequate"

    def test_react_parse_llm_final_answer(self) -> None:
        from insureflow.agents.react_agent import ReActAgent

        agent = ReActAgent()
        parsed = agent._parse_llm_output(
            '{"thought": "done", "action": "final_answer", "findings": [{"title": "Test", "description": "Desc", "severity": "high", "category": "test"}], "summary": "Done"}'
        )
        assert parsed["action"] == "final_answer"
        assert len(parsed["findings"]) == 1

    def test_react_parse_llm_with_code_block(self) -> None:
        from insureflow.agents.react_agent import ReActAgent

        agent = ReActAgent()
        parsed = agent._parse_llm_output('```json\n{"thought": "test", "action": "final_answer", "findings": [], "summary": "ok"}\n```')
        assert parsed["action"] == "final_answer"

    def test_react_parse_llm_malformed(self) -> None:
        from insureflow.agents.react_agent import ReActAgent

        agent = ReActAgent()
        parsed = agent._parse_llm_output("not json at all")
        assert "findings" in parsed

    def test_react_loop_full_multiturn_with_tool_calls(self) -> None:
        # End-to-end: a mocked LLM drives a real multi-step ReAct loop through
        # ReActAgent._react_loop() — tool selection, real tool execution
        # against the bundle, the observation fed back into the next prompt,
        # and a final answer that becomes a real Finding. The existing tests
        # only cover the JSON parser and the tool registry in isolation; none
        # of them exercise the loop mechanics themselves.
        from unittest.mock import MagicMock

        from insureflow.llm.client import LLMClient
        from insureflow.verification.circuit_breaker import get_circuit_breaker

        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="slip and fall",
                incurred_amount=250_000,
            ),
        ]
        bundle = _make_bundle(insured_name="Test Corp", claims=claims)

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.provider = "mock_provider"
        mock_llm.model = "mock_model_react_loop_test"
        mock_llm.api_key = "test-key"
        mock_llm.complete.side_effect = [
            '{"thought": "I need the claims data first", "action": "get_loss_run", "action_input": {}}',
            '{"thought": "checking large-loss concentration", "action": "compute_large_loss_ratio", "action_input": {}}',
            (
                '{"thought": "enough information", "action": "final_answer", '
                '"findings": [{"title": "Large loss concentration", '
                '"description": "One claim exceeds $100K", "severity": "high", '
                '"category": "large_loss", "evidence": ["C1"]}], '
                '"summary": "Elevated large-loss exposure"}'
            ),
        ]

        # Reset (not just construct) the breaker for this exact provider/model
        # key so a prior test's failures elsewhere in the suite can never
        # leave it OPEN and silently skip straight to the deterministic path.
        get_circuit_breaker(name=f"llm:{mock_llm.provider}/{mock_llm.model}", failure_threshold=3, recovery_timeout=60.0).reset()

        agent = LossRunAnalystAgent(llm=mock_llm)
        result = agent.run(bundle)

        assert mock_llm.complete.call_count == 3
        assert result.success is True
        assert len(result.findings) == 1
        assert result.findings[0].title == "Large loss concentration"
        assert result.findings[0].severity == RiskSeverity.HIGH

        # The tool observations must have actually round-tripped back into
        # the conversation the model sees on later steps — not just that the
        # loop terminated after 3 calls for some other reason.
        second_call_prompt = mock_llm.complete.call_args_list[1].args[1]
        third_call_prompt = mock_llm.complete.call_args_list[2].args[1]
        assert "Observation:" in second_call_prompt
        assert "C1" in second_call_prompt  # the claim id from get_loss_run's real result
        assert "large_loss_ratio" in third_call_prompt  # the real result of compute_large_loss_ratio

    def test_react_loop_bails_after_max_steps_without_final_answer(self) -> None:
        # Safety-net mechanic: if the model never emits final_answer, the loop
        # must stop at max_steps (10) rather than looping forever, and must
        # surface that as an error rather than silently succeeding empty.
        from unittest.mock import MagicMock

        from insureflow.llm.client import LLMClient
        from insureflow.verification.circuit_breaker import get_circuit_breaker

        bundle = _make_bundle(insured_name="Test Corp")

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.provider = "mock_provider"
        mock_llm.model = "mock_model_react_loop_max_steps_test"
        mock_llm.api_key = "test-key"
        # Always asks for the same tool, never returns final_answer.
        mock_llm.complete.return_value = '{"thought": "still looking", "action": "get_named_insured", "action_input": {}}'

        get_circuit_breaker(name=f"llm:{mock_llm.provider}/{mock_llm.model}", failure_threshold=3, recovery_timeout=60.0).reset()

        agent = LossRunAnalystAgent(llm=mock_llm)
        result = agent.run(bundle)

        assert mock_llm.complete.call_count == 10
        assert result.success is False
        assert any("max steps" in e.lower() for e in result.errors)

    def _seeded_decision_memory(self, tmp_path: Any, monkeypatch: Any) -> Any:
        """A DecisionMemoryStore pointed at a throwaway file, pre-seeded with
        one org-scoped precedent, wired in as the module-level singleton so
        ToolRegistry's lazy `get_decision_memory()` import picks it up.

        Uses monkeypatch (not a raw assignment) so the real singleton is
        always restored after the test, pass or fail -- this global is
        genuinely shared with production code paths (archive.py, the main
        pipeline), not just other tests.
        """
        import insureflow.privacy.decision_memory as dm
        from insureflow.privacy.decision_memory import DecisionMemoryRecord, DecisionMemoryStore

        # Force the offline hashed-embedding path — deterministic and
        # network-free regardless of the ambient environment's
        # EMBEDDING_BACKEND/API-key/egress config.
        monkeypatch.setenv("EMBEDDING_BACKEND", "local")
        store = DecisionMemoryStore(persist_path=tmp_path / "decision_memory.jsonl")
        store.remember(
            DecisionMemoryRecord(
                org_id="org-x",
                bundle_id="past-1",
                line="commercial_property",
                decision="refer",
                naics="236220",
                state="CA",
                tiv_band="1m-5m",
                construction="wood frame",
                occupancy="habitational",
                loss_count_band="2-3",
                reasons=["three prior losses", "wood frame construction in wildfire zone"],
            )
        )
        monkeypatch.setattr(dm, "_store", store)
        return store

    def test_recall_tool_registered_and_safe_without_org_id(self, tmp_path: Any, monkeypatch: Any) -> None:
        self._seeded_decision_memory(tmp_path, monkeypatch)
        bundle = _make_bundle(insured_name="Test Corp")
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle, insurance_line="commercial_property", org_id=None)
        names = [t["name"] for t in reg.list_tools()]
        assert "recall_similar_past_decisions" in names

        result = reg.call("recall_similar_past_decisions")
        assert result["available"] is False

    def test_recall_tool_returns_real_precedent_with_org_id(self, tmp_path: Any, monkeypatch: Any) -> None:
        self._seeded_decision_memory(tmp_path, monkeypatch)
        bundle = SubmissionBundle(
            bundle_id="current-1",
            structured=StructuredSubmission(
                submission_id="s1",
                named_insured=NamedInsured(legal_name="Test Corp", state_of_residence="CA"),
                risk_profile=RiskProfile(naics_code="236220", construction_type="wood frame", occupancy_type="habitational"),
                locations=[LocationData(address="123 Main", city="LA", state="CA", zip_code="90001", building_value=2_000_000)],
            ),
        )
        from insureflow.agents.react_tools import ToolRegistry

        reg = ToolRegistry(bundle, insurance_line="commercial_property", org_id="org-x")
        result = reg.call("recall_similar_past_decisions", limit=3)
        assert result["available"] is True
        assert result["count"] == 1
        assert result["similar_cases"][0]["bundle_id"] == "past-1"
        assert result["similar_cases"][0]["decision"] == "refer"
        assert "three prior losses" in result["similar_cases"][0]["reasons"]

    def test_react_loop_recalls_past_decisions_and_feeds_observation_back(self, tmp_path: Any, monkeypatch: Any) -> None:
        # End-to-end: the mocked model calls recall_similar_past_decisions
        # mid-loop, and the REAL precedent it returns (not a stub) must
        # round-trip into the next prompt -- this is the actual gap the
        # whole feature exists to close: retrieval feeding agent reasoning,
        # not just a tool that technically exists.
        from unittest.mock import MagicMock

        from insureflow.llm.client import LLMClient
        from insureflow.verification.circuit_breaker import get_circuit_breaker

        self._seeded_decision_memory(tmp_path, monkeypatch)

        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="GL",
                cause="wildfire exposure",
                incurred_amount=50_000,
            ),
        ]
        bundle = _make_bundle(insured_name="Test Corp", claims=claims)

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.provider = "mock_provider"
        mock_llm.model = "mock_model_react_loop_recall_test"
        mock_llm.api_key = "test-key"
        mock_llm.complete.side_effect = [
            '{"thought": "checking for precedent", "action": "recall_similar_past_decisions", "action_input": {"limit": 3}}',
            (
                '{"thought": "found a similar prior referral", "action": "final_answer", '
                '"findings": [{"title": "Similar past case was referred", '
                '"description": "A prior wood-frame CA habitational risk with 3 losses was referred", '
                '"severity": "moderate", "category": "precedent", "evidence": ["past-1"]}], '
                '"summary": "Consistent with a prior referral decision"}'
            ),
        ]

        get_circuit_breaker(name=f"llm:{mock_llm.provider}/{mock_llm.model}", failure_threshold=3, recovery_timeout=60.0).reset()

        agent = LossRunAnalystAgent(llm=mock_llm)
        result = agent.run(bundle, insurance_line="commercial_property", org_id="org-x")

        assert mock_llm.complete.call_count == 2
        assert result.success is True
        assert result.findings[0].title == "Similar past case was referred"

        second_call_prompt = mock_llm.complete.call_args_list[1].args[1]
        assert "Observation:" in second_call_prompt
        assert "past-1" in second_call_prompt  # the real precedent's bundle_id
        assert "wood frame construction in wildfire zone" in second_call_prompt  # its real stored reason


class TestSupervisorAgent:
    def test_full_analysis(self) -> None:
        claims = [
            ClaimRecord(
                claim_id="C1",
                date_of_loss=date(2024, 1, 1),
                line_of_business="General Liability",
                cause="slip and fall",
                incurred_amount=50_000,
                paid_amount=50_000,
                claim_status=ClaimStatus.CLOSED,
            ),
            ClaimRecord(
                claim_id="C2",
                date_of_loss=date(2024, 6, 1),
                line_of_business="Workers Compensation",
                cause="back strain",
                incurred_amount=120_000,
                paid_amount=100_000,
                open_reserve=20_000,
                claim_status=ClaimStatus.OPEN,
            ),
        ]
        covs = [
            CoverageDetail(
                coverage_type="General Liability",
                limit_amount=2_000_000,
                deductible=5_000,
                premium=25_000,
            ),
            CoverageDetail(coverage_type="Property", limit_amount=5_000_000, deductible=25_000, premium=50_000),
            CoverageDetail(
                coverage_type="Commercial Auto",
                limit_amount=1_000_000,
                deductible=10_000,
                premium=30_000,
            ),
        ]
        locs = [
            LocationData(
                address="100 Industrial Blvd",
                city="Oakland",
                state="CA",
                zip_code="94607",
                year_built=1999,
                building_value=18_500_000,
                square_footage=210_000,
                protection_class=3,
            ),
        ]
        bundle = _make_bundle(
            claims=claims,
            coverages=covs,
            locations=locs,
            risk_profile={
                "construction_type": "Steel frame",
                "occupancy_type": "Warehouse distribution",
                "sprinklered": True,
                "protection_class": 3,
                "naics_code": "493110",
            },
        )

        supervisor = SupervisorAgent()
        memo = supervisor.analyze_submission(bundle, parallel=False)

        assert memo.bundle_id == "test-bundle"
        assert memo.decision in (UWDecision.ACCEPT, UWDecision.REFER, UWDecision.DECLINE)
        assert memo.overall_risk_score >= 0
        assert len(memo.agent_results) >= 4
        assert memo.risk_analyst_findings is not None
        assert memo.loss_run_findings is not None
        assert memo.compliance_findings is not None
        assert memo.fraud_findings is not None

        total_findings = sum(len(r.findings) for r in memo.agent_results.values())
        assert total_findings > 0

    def test_structured_output(self) -> None:
        bundle = _make_bundle()
        supervisor = SupervisorAgent()
        output = supervisor.analyze_submission_structured(bundle)
        assert "decision" in output
        assert "overall_risk_score" in output
        assert "key_findings" in output
        assert "agent_results" in output

    def test_parallel_execution(self) -> None:
        bundle = _make_bundle(
            claims=[
                ClaimRecord(
                    claim_id="C1",
                    date_of_loss=date(2024, 1, 1),
                    line_of_business="GL",
                    cause="test",
                    incurred_amount=10_000,
                ),
            ],
            coverages=[
                CoverageDetail(
                    coverage_type="Property",
                    limit_amount=1_000_000,
                    deductible=10_000,
                    premium=25_000,
                ),
            ],
            risk_profile={"sprinklered": True},
        )
        supervisor = SupervisorAgent()
        memo = supervisor.analyze_submission(bundle, parallel=True)
        assert len(memo.agent_results) >= 4

    def test_auto_plan_defaults_to_off_and_changes_nothing(self) -> None:
        # auto_plan=False (the default) must dispatch every agent exactly as
        # before this feature existed -- it's opt-in, not a behavior change
        # for any existing caller.
        bundle = _make_bundle(insured_name="Life Applicant")
        supervisor = SupervisorAgent()
        memo = supervisor.analyze_submission(bundle, insurance_line="life")
        assert "LossRunAnalystAgent" in memo.agent_results
        assert not any("Skipped LossRunAnalystAgent" in n for n in memo.review_notes)

    def test_auto_plan_skips_loss_run_analyst_for_non_property_line(self) -> None:
        bundle = _make_bundle(insured_name="Life Applicant")
        supervisor = SupervisorAgent()
        memo = supervisor.analyze_submission(bundle, insurance_line="life", auto_plan=True)
        assert "LossRunAnalystAgent" not in memo.agent_results
        assert any("Skipped LossRunAnalystAgent" in n for n in memo.review_notes)
        # Everything else still ran -- this skips one agent, not the analysis.
        assert "RiskAnalystAgent" in memo.agent_results
        assert "ComplianceAgent" in memo.agent_results
        assert "FraudDetectionAgent" in memo.agent_results

    def test_auto_plan_records_fraud_ml_skip_reason_for_property_line(self) -> None:
        bundle = _make_bundle(
            insured_name="Small Shop",
            locations=[LocationData(address="A", city="C", state="S", zip_code="Z", building_value=100_000)],
        )
        supervisor = SupervisorAgent()
        memo = supervisor.analyze_submission(bundle, insurance_line="commercial_property", auto_plan=True)
        assert "LossRunAnalystAgent" in memo.agent_results  # property line -- still relevant, still runs
        assert any("lowest materiality band" in n for n in memo.review_notes)


class TestAgentPlanner:
    def test_skips_loss_run_analyst_for_non_property_line(self) -> None:
        from insureflow.agents.planner import AgentPlanner

        bundle = _make_bundle(insured_name="Life Applicant")
        plan = AgentPlanner().plan(bundle, insurance_line="life")
        assert plan.run_loss_run_analyst is False
        assert plan.skip_ml_fraud is False
        assert any("LossRunAnalystAgent" in r for r in plan.reasons)

    def test_skips_fraud_ml_for_low_materiality_property(self) -> None:
        from insureflow.agents.planner import AgentPlanner

        bundle = _make_bundle(
            insured_name="Small Shop",
            locations=[LocationData(address="A", city="C", state="S", zip_code="Z", building_value=100_000)],
        )
        plan = AgentPlanner().plan(bundle, insurance_line="commercial_property")
        assert plan.run_loss_run_analyst is True
        assert plan.skip_ml_fraud is True
        assert any("materiality" in r for r in plan.reasons)

    def test_runs_everything_for_large_property(self) -> None:
        from insureflow.agents.planner import AgentPlanner

        bundle = _make_bundle(
            insured_name="Big Factory",
            locations=[LocationData(address="A", city="C", state="S", zip_code="Z", building_value=5_000_000)],
        )
        plan = AgentPlanner().plan(bundle, insurance_line="commercial_property")
        assert plan.run_loss_run_analyst is True
        assert plan.skip_ml_fraud is False
        assert plan.reasons == []

    def test_runs_everything_when_no_locations_on_a_property_line(self) -> None:
        # No TIV signal to act on -- fail safe to "run everything", never
        # silently skip a check when there's nothing to justify skipping it.
        from insureflow.agents.planner import AgentPlanner

        bundle = _make_bundle(insured_name="Unknown Risk")
        plan = AgentPlanner().plan(bundle, insurance_line="commercial_property")
        assert plan.run_loss_run_analyst is True
        assert plan.skip_ml_fraud is False
