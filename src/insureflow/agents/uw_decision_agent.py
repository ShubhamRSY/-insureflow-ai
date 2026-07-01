from __future__ import annotations

from typing import Any

from insureflow.agents.react_agent import ReActAgent
from insureflow.models.agents import (
    AgentResult,
    AgentType,
    Finding,
    Recommendation,
    RiskSeverity,
    UnderwritingMemo,
    UWDecision,
)
from insureflow.models.submissions import SubmissionBundle


class UWDecisionAgent(ReActAgent):
    agent_type = AgentType.UW_DECISION
    agent_name = "UWDecisionAgent"
    prompt_key = "uw_decision"

    def __init__(self) -> None:
        from insureflow.llm.client import LLMClient
        super().__init__(llm=LLMClient(model_tier="expensive"))
        self._agent_results: dict[str, AgentResult] = {}

    def run(
        self, bundle: SubmissionBundle, **kwargs: Any
    ) -> AgentResult:
        self._agent_results = kwargs.get("agent_results", {})
        return super().run(bundle, **kwargs)

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        all_findings: list[Finding] = []
        for agent_type, result in self._agent_results.items():
            all_findings.extend(result.findings)

        if not all_findings:
            self._add_finding(Finding(
                title="No findings from specialist agents",
                description="All agents returned clean results — standard risk",
                severity=RiskSeverity.LOW,
                category="synthesis",
            ))
            return

        high_crit = [
            f for f in all_findings
            if f.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)
        ]
        moderate = [
            f for f in all_findings if f.severity == RiskSeverity.MODERATE
        ]

        if any(f.severity == RiskSeverity.CRITICAL for f in high_crit):
            self._add_finding(Finding(
                title="Critical findings require declination",
                description=f"{sum(1 for f in high_crit if f.severity == RiskSeverity.CRITICAL)} critical finding(s)",
                severity=RiskSeverity.CRITICAL,
                category="uw_decision",
                evidence=[f.title for f in high_crit if f.severity == RiskSeverity.CRITICAL],
            ))

        score = self._calculate_aggregate_risk(all_findings)
        if score >= 0.7:
            self._add_finding(Finding(
                title="Elevated aggregate risk score",
                description=f"Aggregate risk score {score:.2f} — "
                            f"{len(high_crit)} high/critical + {len(moderate)} moderate findings",
                severity=RiskSeverity.HIGH,
                category="uw_decision",
            ))

    def _calculate_aggregate_risk(self, findings: list[Finding]) -> float:
        if not findings:
            return 0.0
        weights = {"critical": 1.0, "high": 0.75, "moderate": 0.5, "low": 0.2}
        scores = [weights.get(f.severity.value, 0.5) for f in findings]
        return min(1.0, sum(scores) / len(scores))

    def _build_recommendation(self) -> Recommendation | None:
        has_critical = any(
            f.severity == RiskSeverity.CRITICAL for f in self._findings
        )
        has_high = any(
            f.severity == RiskSeverity.HIGH for f in self._findings
        )
        score = self._calculate_aggregate_risk(self._findings)

        if has_critical:
            return Recommendation(
                action="decline",
                rationale=f"Critical findings present. Aggregate risk score: {score:.2f}",
                conditions=[],
            )
        if has_high or score >= 0.7:
            return Recommendation(
                action="refer",
                rationale=f"Aggregate risk score: {score:.2f}. {sum(1 for f in self._findings if f.severity == RiskSeverity.HIGH)} high-severity findings require UW review.",
                suggested_premium_modification=1.15 if score > 0.6 else None,
                conditions=[
                    f.title for f in self._findings
                    if f.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
                ],
            )
        return Recommendation(
            action="accept",
            rationale=f"Acceptable risk profile. Aggregate risk score: {score:.2f}. No high-severity findings.",
            conditions=[
                f.title for f in self._findings if f.severity == RiskSeverity.MODERATE
            ],
        )

    def produce_underwriting_memo(
        self,
        bundle: SubmissionBundle,
        agent_results: list[AgentResult],
        uw_decision_result: AgentResult,
    ) -> UnderwritingMemo:
        all_findings = []
        for ar in agent_results:
            all_findings.extend(ar.findings)
        all_findings.extend(uw_decision_result.findings)

        rec = uw_decision_result.recommendation
        decision = UWDecision.REFER
        if rec:
            if rec.action == "accept":
                decision = UWDecision.ACCEPT
            elif rec.action == "decline":
                decision = UWDecision.DECLINE

        score = self._calculate_aggregate_risk(all_findings)
        severity = self.tools.assess_overall_severity(all_findings)

        results_map = {ar.agent_name: ar for ar in agent_results}
        results_map[uw_decision_result.agent_name] = uw_decision_result

        return UnderwritingMemo(
            bundle_id=bundle.bundle_id,
            insured_name=self.tools.get_named_insured(bundle),
            decision=decision,
            overall_risk_score=score,
            overall_risk_severity=severity,
            summary=self._build_memo_summary(decision, score, all_findings),
            key_findings=all_findings[:10],
            risk_analyst_findings=self._agent_findings(agent_results, "RiskAnalystAgent"),
            loss_run_findings=self._agent_findings(agent_results, "LossRunAnalystAgent"),
            compliance_findings=self._agent_findings(agent_results, "ComplianceAgent"),
            fraud_findings=self._agent_findings(agent_results, "FraudDetectionAgent"),
            recommendation=rec,
            conditions=rec.conditions if rec else [],
            review_notes=self._build_review_notes(all_findings),
            human_review_required=decision in (UWDecision.REFER, UWDecision.DECLINE),
            human_review_reasons=[
                f.title for f in all_findings
                if f.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
            ],
            agent_results=results_map,
        )

    def _build_memo_summary(
        self, decision: UWDecision, score: float, findings: list[Finding]
    ) -> str:
        sev_counts: dict[str, int] = {}
        for f in findings:
            sev_counts[f.severity.value] = sev_counts.get(f.severity.value, 0) + 1
        critical = sev_counts.get("critical", 0)
        high = sev_counts.get("high", 0)
        total = len(findings)
        action = decision.value.upper()
        pct = int(round(score * 100))
        narrative = (
            f"Underwriting recommendation is {action} based on {total} findings "
            f"across risk, loss history, compliance, and fraud analysis. "
            f"Aggregate risk score is {pct}/100."
        )
        if critical or high:
            narrative += f" {critical + high} finding(s) require elevated attention."
        return narrative

    def _agent_findings(
        self, results: list[AgentResult], name: str
    ) -> list[Finding]:
        for r in results:
            if r.agent_name == name:
                return r.findings
        return []

    def _build_review_notes(self, findings: list[Finding]) -> list[str]:
        notes = []
        for f in findings:
            if f.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL):
                notes.append(f"[{f.severity.value.upper()}] {f.title}: {f.description[:120]}")
        for f in findings:
            if f.severity == RiskSeverity.MODERATE and len(notes) < 15:
                notes.append(f"[MODERATE] {f.title}: {f.description[:120]}")
        return notes
