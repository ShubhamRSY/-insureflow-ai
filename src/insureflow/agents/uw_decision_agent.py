from __future__ import annotations

from typing import Any

from insureflow.agents.base import NOISE_CATEGORIES
from insureflow.agents.react_agent import ReActAgent
from insureflow.models.agents import AgentResult, AgentType, Finding, Recommendation, RiskSeverity, UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle

# ── Decision policy thresholds ──────────────────────────────────────────────
# See docs/underwriting_decision_policy.md for the rationale. Single edit
# point: change a tier's boundary here, not by hunting inline literals.
SEVERITY_WEIGHTS = {"critical": 1.0, "high": 0.75, "moderate": 0.5, "low": 0.2}
REFER_AGGREGATE_SCORE_THRESHOLD = 0.7  # any high finding OR score >= this -> REFER
SURCHARGE_ELIGIBLE_SCORE_THRESHOLD = 0.6  # frequency/severity surcharge only applies above this
HARD_DECLINE_CLAIM_FREQUENCY_PER_YEAR = 10.0  # claim frequency at/above this is an automatic DECLINE
FREQUENCY_SURCHARGE_MODERATE_THRESHOLD = 1.5  # claims/yr
FREQUENCY_SURCHARGE_MODERATE_PCT = 10.0
FREQUENCY_SURCHARGE_HIGH_THRESHOLD = 3.0  # claims/yr
FREQUENCY_SURCHARGE_HIGH_BASE_PCT = 15.0
FREQUENCY_SURCHARGE_HIGH_PER_CLAIM_PCT = 15.0
SEVERITY_SURCHARGE_MODERATE_THRESHOLD = 75_000.0  # avg claim severity, $
SEVERITY_SURCHARGE_MODERATE_PCT = 5.0
SEVERITY_SURCHARGE_HIGH_THRESHOLD = 200_000.0  # avg claim severity, $
SEVERITY_SURCHARGE_HIGH_BASE_PCT = 10.0
SEVERITY_SURCHARGE_HIGH_PER_DOLLAR_DIVISOR = 20_000.0
MAX_TOTAL_SURCHARGE_PCT = 100.0


class UWDecisionAgent(ReActAgent):
    agent_type = AgentType.UW_DECISION
    agent_name = "UWDecisionAgent"
    prompt_key = "uw_decision"

    def __init__(self) -> None:
        from insureflow.llm.client import LLMClient

        super().__init__(llm=LLMClient(model_tier="expensive"))
        self._agent_results: dict[str, AgentResult] = {}

    def run(self, bundle: SubmissionBundle, **kwargs: Any) -> AgentResult:
        self._agent_results = kwargs.get("agent_results", {})
        return super().run(bundle, **kwargs)

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        all_findings: list[Finding] = []
        for agent_type, result in self._agent_results.items():
            all_findings.extend(result.findings)

        if not all_findings:
            self._add_finding(
                Finding(
                    title="No findings from specialist agents",
                    description="All agents returned clean results — standard risk",
                    severity=RiskSeverity.LOW,
                    category="synthesis",
                )
            )
            return

        high_crit = [f for f in all_findings if f.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)]
        moderate = [f for f in all_findings if f.severity == RiskSeverity.MODERATE]

        if any(f.severity == RiskSeverity.CRITICAL for f in high_crit):
            self._add_finding(
                Finding(
                    title="Critical findings require UW review",
                    description=f"{sum(1 for f in high_crit if f.severity == RiskSeverity.CRITICAL)} critical finding(s)",
                    severity=RiskSeverity.CRITICAL,
                    category="uw_decision",
                    evidence=[f.title for f in high_crit if f.severity == RiskSeverity.CRITICAL],
                )
            )

        score = self._calculate_aggregate_risk(all_findings)
        if score >= REFER_AGGREGATE_SCORE_THRESHOLD:
            self._add_finding(
                Finding(
                    title="Elevated aggregate risk score",
                    description=f"Aggregate risk score {score:.2f} — {len(high_crit)} high/critical + {len(moderate)} moderate findings",
                    severity=RiskSeverity.HIGH,
                    category="uw_decision",
                )
            )

    def _calculate_aggregate_risk(self, findings: list[Finding]) -> float:
        """Calibrated aggregate risk score — consistent with BaseAgent._calculate_risk_score.

        Environmental findings (NOISE_CATEGORIES) are excluded entirely — they're
        data-availability noise, not underwriting risk, and independently force
        REFER via dedicated pipeline handling. Volume amplification only counts
        MODERATE+ findings, and is capped together with the category penalty at
        +0.25 so pile-up effects nudge the score without dominating it.
        """
        high_risk_categories = {"fraud_detection", "moral_hazard", "selection", "adverse_selection"}
        scored = [f for f in findings if f.category not in NOISE_CATEGORIES]
        if not scored:
            return 0.0

        weighted_sum = 0.0
        high_risk_count = 0
        volume_count = 0.0
        total_weight = 0.0

        for f in scored:
            sev_weight = SEVERITY_WEIGHTS.get(f.severity.value, 0.5)
            conf = getattr(f, "confidence", None) or 0.7
            conf_weight = 0.5 + conf * 0.5
            weighted_sum += sev_weight * conf_weight
            total_weight += 1.0
            if f.severity.value != "low":
                volume_count += 1.0
            if f.category in high_risk_categories:
                high_risk_count += 1

        if total_weight == 0:
            return 0.0

        base_score = weighted_sum / total_weight

        import math

        volume_amp = math.log2(1.0 + volume_count) / 6.0
        category_penalty = min(0.3, high_risk_count * 0.1)
        pileup_bonus = min(0.25, volume_amp + category_penalty)

        score = base_score + pileup_bonus
        return min(1.0, max(0.0, score))

    def _build_recommendation(self) -> Recommendation | None:
        has_critical = any(f.severity == RiskSeverity.CRITICAL for f in self._findings)
        has_high = any(f.severity == RiskSeverity.HIGH for f in self._findings)
        has_moderate = any(f.severity == RiskSeverity.MODERATE for f in self._findings)
        score = self._calculate_aggregate_risk(self._findings)

        frequency_val = 0.0
        severity_val = 0.0
        for f in self._findings:
            if f.category == "frequency" and f.source_value is not None:
                frequency_val = float(f.source_value)
            if f.category == "severity" and f.source_value is not None:
                severity_val = float(f.source_value)

        freq_surcharge = 0.0
        if frequency_val > FREQUENCY_SURCHARGE_HIGH_THRESHOLD:
            freq_surcharge = FREQUENCY_SURCHARGE_HIGH_BASE_PCT + (frequency_val - FREQUENCY_SURCHARGE_HIGH_THRESHOLD) * FREQUENCY_SURCHARGE_HIGH_PER_CLAIM_PCT
        elif frequency_val > FREQUENCY_SURCHARGE_MODERATE_THRESHOLD:
            freq_surcharge = FREQUENCY_SURCHARGE_MODERATE_PCT

        sev_surcharge = 0.0
        if severity_val > SEVERITY_SURCHARGE_HIGH_THRESHOLD:
            sev_surcharge = SEVERITY_SURCHARGE_HIGH_BASE_PCT + (severity_val - SEVERITY_SURCHARGE_HIGH_THRESHOLD) / SEVERITY_SURCHARGE_HIGH_PER_DOLLAR_DIVISOR
        elif severity_val > SEVERITY_SURCHARGE_MODERATE_THRESHOLD:
            sev_surcharge = SEVERITY_SURCHARGE_MODERATE_PCT

        total_surcharge = min(freq_surcharge + sev_surcharge, MAX_TOTAL_SURCHARGE_PCT)

        if frequency_val >= HARD_DECLINE_CLAIM_FREQUENCY_PER_YEAR:
            return Recommendation(
                action="decline",
                rationale=f"Extreme claim frequency: {frequency_val:.1f} claims/year indicates systemic operational issues. Aggregate risk score: {score:.2f}.",
                conditions=[f"Claim frequency of {frequency_val:.1f}/yr exceeds maximum acceptable threshold ({HARD_DECLINE_CLAIM_FREQUENCY_PER_YEAR:.0f}/yr)."],
            )

        if has_critical:
            # Critical findings need licensed UW eyes — hard declines belong to
            # appetite / moral-hazard / selection gates, not every data-quality flag.
            return Recommendation(
                action="refer",
                rationale=f"Critical findings present — refer to licensed UW. Aggregate risk score: {score:.2f}",
                conditions=[f.title for f in self._findings if f.severity == RiskSeverity.CRITICAL],
            )

        if has_high or score >= REFER_AGGREGATE_SCORE_THRESHOLD:
            return Recommendation(
                action="refer",
                rationale=f"Aggregate risk score: {score:.2f}. {sum(1 for f in self._findings if f.severity == RiskSeverity.HIGH)} high-severity findings require UW review.",
                suggested_premium_modification=total_surcharge if total_surcharge > 0 and score > SURCHARGE_ELIGIBLE_SCORE_THRESHOLD else None,
                conditions=[f.title for f in self._findings if f.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)],
            )

        if has_moderate:
            moderate = [f for f in self._findings if f.severity == RiskSeverity.MODERATE]
            return Recommendation(
                action="conditional_accept",
                rationale=f"Aggregate risk score: {score:.2f}. {len(moderate)} moderate finding(s) require subjectivities before bind. Issuing conditional quote.",
                conditions=[f"SUBJECT TO: {f.field_path or f.category} — {f.title}: {f.description[:120]}" for f in moderate],
                suggested_premium_modification=total_surcharge if total_surcharge > 0 else None,
            )

        return Recommendation(
            action="accept",
            rationale=f"Acceptable risk profile. Aggregate risk score: {score:.2f}. No findings requiring conditions.",
            conditions=[],
        )

    def produce_underwriting_memo(
        self,
        bundle: SubmissionBundle,
        agent_results: list[AgentResult],
        uw_decision_result: AgentResult,
    ) -> UnderwritingMemo:
        all_findings = []
        for ar in agent_results:
            # Callers commonly append uw_decision_result into agent_results
            # before calling this (for timing/summary display) *and* pass it
            # again as uw_decision_result below — skip it here so its
            # findings aren't double-counted into the risk score.
            if ar is uw_decision_result or ar.agent_name == uw_decision_result.agent_name:
                continue
            all_findings.extend(ar.findings)
        all_findings.extend(uw_decision_result.findings)

        rec = uw_decision_result.recommendation
        decision = UWDecision.REFER
        if rec:
            if rec.action == "accept":
                decision = UWDecision.ACCEPT
            elif rec.action == "conditional_accept":
                decision = UWDecision.CONDITIONAL_ACCEPT
            elif rec.action == "decline":
                decision = UWDecision.DECLINE

        score = self._calculate_aggregate_risk(all_findings)
        severity = self.tools.assess_overall_severity(all_findings)

        results_map = {ar.agent_name: ar for ar in agent_results}
        results_map[uw_decision_result.agent_name] = uw_decision_result

        # Preserve all CRITICAL/HIGH findings; truncate only lower severities
        critical_high = [f for f in all_findings if f.severity in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)]
        other = [f for f in all_findings if f.severity not in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)]
        key_findings = critical_high + other[: max(0, 20 - len(critical_high))]

        return UnderwritingMemo(
            bundle_id=bundle.bundle_id,
            insured_name=self.tools.get_named_insured(bundle),
            decision=decision,
            overall_risk_score=score,
            overall_risk_severity=severity,
            summary=self._build_memo_summary(decision, score, all_findings),
            key_findings=key_findings,
            risk_analyst_findings=self._agent_findings(agent_results, "RiskAnalystAgent"),
            loss_run_findings=self._agent_findings(agent_results, "LossRunAnalystAgent"),
            compliance_findings=self._agent_findings(agent_results, "ComplianceAgent"),
            fraud_findings=self._agent_findings(agent_results, "FraudDetectionAgent"),
            recommendation=rec,
            conditions=rec.conditions if rec else [],
            review_notes=self._build_review_notes(all_findings),
            human_review_required=decision in (UWDecision.REFER, UWDecision.DECLINE, UWDecision.CONDITIONAL_ACCEPT),
            human_review_reasons=[f.title for f in all_findings if f.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)],
            agent_results=results_map,
        )

    def _build_memo_summary(self, decision: UWDecision, score: float, findings: list[Finding]) -> str:
        from insureflow.underwriting.memo_sync import build_memo_summary

        return build_memo_summary(decision, score, findings)

    def _agent_findings(self, results: list[AgentResult], name: str) -> list[Finding]:
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
