"""Regression tests: the core agent swarm (RiskAnalystAgent, LossRunAnalystAgent,
ComplianceAgent, FraudDetectionAgent) and the ReAct tool registry/prompt/finding
filter must never fabricate a P&C-only finding (missing locations, missing
coverages, missing loss run data, missing schedule of values) for a submission
on a line that structurally has none of those concepts — life, health, general,
and the commercial specialty lines (D&O, trade credit, E&O, key person).
"""

from __future__ import annotations

from insureflow.agents.compliance_agent import ComplianceAgent
from insureflow.agents.loss_run_analyst import LossRunAnalystAgent
from insureflow.agents.react_agent import ReActAgent
from insureflow.agents.react_tools import ToolRegistry
from insureflow.models.agents import AgentType
from insureflow.models.submissions import (
    FinancialData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
    SubmissionStatus,
)

P_AND_C_KEYWORDS = (
    "location",
    "coverage schedule",
    "coverage limit",
    "loss run",
    "schedule of values",
    "statement of values",
)


def _life_bundle(insured_name: str = "Priya Nair") -> SubmissionBundle:
    """A structurally life-shaped bundle: no coverages, no locations, no loss
    run — exactly what every real life submission looks like, since those
    fields are P&C concepts that don't exist on a life application."""
    return SubmissionBundle(
        bundle_id="life-test-bundle",
        status=SubmissionStatus.COMPLETED,
        structured=StructuredSubmission(
            submission_id="life-test-sub",
            named_insured=NamedInsured(legal_name=insured_name),
            coverages=[],
            locations=[],
            risk_profile=RiskProfile(),
            financial=FinancialData(),
            schedule_of_values=[],
        ),
    )


def _finding_titles(agent_result: object) -> list[str]:
    return [f.title for f in agent_result.findings]  # type: ignore[attr-defined]


class TestLossRunAnalystAgentLobScoping:
    def test_no_findings_on_life_line(self) -> None:
        result = LossRunAnalystAgent().run(_life_bundle(), insurance_line="life")
        assert result.findings == []

    def test_still_flags_missing_loss_run_on_property_line(self) -> None:
        result = LossRunAnalystAgent().run(_life_bundle(), insurance_line="commercial_property")
        titles = _finding_titles(result)
        assert any("loss run" in t.lower() for t in titles)

    def test_still_flags_missing_loss_run_when_line_unresolved(self) -> None:
        # No insurance_line passed at all — must preserve prior (property-like) behavior.
        result = LossRunAnalystAgent().run(_life_bundle())
        titles = _finding_titles(result)
        assert any("loss run" in t.lower() for t in titles)


class TestComplianceAgentLobScoping:
    def test_no_coverage_finding_on_life_line(self) -> None:
        result = ComplianceAgent().run(_life_bundle(), insurance_line="life")
        titles = [t.lower() for t in _finding_titles(result)]
        assert not any("coverage" in t for t in titles)

    def test_named_insured_check_still_runs_on_life_line(self) -> None:
        bundle = _life_bundle(insured_name="")
        result = ComplianceAgent().run(bundle, insurance_line="life")
        titles = [t.lower() for t in _finding_titles(result)]
        assert any("named insured" in t for t in titles)

    def test_still_flags_missing_coverage_on_property_line(self) -> None:
        result = ComplianceAgent().run(_life_bundle(), insurance_line="commercial_property")
        titles = [t.lower() for t in _finding_titles(result)]
        assert any("coverage" in t for t in titles)


class TestNonPropertyLinesTaxonomy:
    def test_commercial_specialty_lines_are_non_property(self) -> None:
        from insureflow.rating.models import is_non_property_line

        for line in ("directors_and_officers", "trade_credit", "errors_and_omissions", "key_person", "life", "health", "general"):
            assert is_non_property_line(line), f"{line} should be scoped as non-property"

    def test_property_lines_are_not_non_property(self) -> None:
        from insureflow.rating.models import is_non_property_line

        for line in ("commercial_property", "general_liability", "workers_comp", "business_owners_policy", "personal_homeowners"):
            assert not is_non_property_line(line)

    def test_unresolved_line_is_not_treated_as_non_property(self) -> None:
        from insureflow.rating.models import is_non_property_line

        assert not is_non_property_line(None)
        assert not is_non_property_line("")


class TestToolRegistryLobScoping:
    def test_property_only_tools_excluded_for_life(self) -> None:
        registry = ToolRegistry(_life_bundle(), insurance_line="life")
        names = {t["name"] for t in registry.list_tools()}
        for excluded in ("get_locations", "get_coverages", "get_loss_run", "get_sovs", "check_coverage_adequacy", "check_sov_vs_location_valuation"):
            assert excluded not in names

    def test_universal_tools_still_present_for_life(self) -> None:
        registry = ToolRegistry(_life_bundle(), insurance_line="life")
        names = {t["name"] for t in registry.list_tools()}
        assert "get_named_insured" in names
        assert "get_all_structured_data" in names

    def test_property_only_tools_present_for_property_line(self) -> None:
        registry = ToolRegistry(_life_bundle(), insurance_line="commercial_property")
        names = {t["name"] for t in registry.list_tools()}
        assert "get_locations" in names
        assert "get_coverages" in names
        assert "get_loss_run" in names

    def test_property_only_tools_present_when_line_unresolved(self) -> None:
        registry = ToolRegistry(_life_bundle())
        names = {t["name"] for t in registry.list_tools()}
        assert "get_locations" in names


class _FakeReActAgent(ReActAgent):
    agent_type = AgentType.COMPLIANCE_AGENT
    agent_name = "FakeReActAgent"
    prompt_key = "compliance_agent"


class TestReActGenerationTimeFilter:
    def test_drops_pc_only_finding_on_life_line(self) -> None:
        agent = _FakeReActAgent()
        agent._findings = []
        agent.bundle = _life_bundle()
        agent._insurance_line = "life"
        agent._process_final_answer(
            {
                "findings": [
                    {"title": "Missing Locations", "description": "no insured locations available", "severity": "critical", "category": "data_quality"},
                    {"title": "Missing Coverages", "description": "no coverages available", "severity": "critical", "category": "data_quality"},
                    {"title": "Missing Loss Run Data", "description": "no loss run data available", "severity": "critical", "category": "data_quality"},
                ]
            }
        )
        assert agent._findings == []

    def test_keeps_genuine_finding_on_life_line(self) -> None:
        agent = _FakeReActAgent()
        agent._findings = []
        agent.bundle = _life_bundle()
        agent._insurance_line = "life"
        agent._process_final_answer(
            {
                "findings": [
                    {"title": "MIB check not performed", "description": "order a bureau report", "severity": "high", "category": "compliance"},
                ]
            }
        )
        assert len(agent._findings) == 1
        assert agent._findings[0].title == "MIB check not performed"

    def test_keeps_pc_finding_on_property_line(self) -> None:
        agent = _FakeReActAgent()
        agent._findings = []
        agent.bundle = _life_bundle()
        agent._insurance_line = "commercial_property"
        agent._process_final_answer({"findings": [{"title": "Missing Locations", "description": "no insured locations available", "severity": "critical", "category": "data_quality"}]})
        assert len(agent._findings) == 1


class TestEndToEndLifeSubmissionNeverProducesPcFindings:
    def test_life_submission_findings_have_no_pc_titles(self) -> None:
        bundle = _life_bundle()
        results = [
            LossRunAnalystAgent().run(bundle, insurance_line="life"),
            ComplianceAgent().run(bundle, insurance_line="life"),
        ]
        for result in results:
            for f in result.findings:
                blob = f"{f.title} {f.description}".lower()
                assert not any(kw in blob for kw in P_AND_C_KEYWORDS), f"P&C-only finding leaked on life line: {f.title}"
