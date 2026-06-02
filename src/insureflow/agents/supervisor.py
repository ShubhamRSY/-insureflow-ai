from __future__ import annotations

import json
import time
from typing import Any, Optional

from insureflow.agents.base import BaseAgent
from insureflow.agents.compliance_agent import ComplianceAgent
from insureflow.agents.fraud_detection_agent import FraudDetectionAgent
from insureflow.agents.loss_run_analyst import LossRunAnalystAgent
from insureflow.agents.risk_analyst import RiskAnalystAgent
from insureflow.agents.uw_decision_agent import UWDecisionAgent
from insureflow.llm.client import LLMClient
from insureflow.models.agents import (
    AgentResult,
    AgentType,
    UnderwritingMemo,
)
from insureflow.models.submissions import SubmissionBundle

CONFLICT_RESOLUTION_PROMPT = """You are a senior underwriting supervisor. Review the findings from multiple specialist agents and resolve conflicts.

Agent findings:

{agent_findings}

Identify:
1. Any direct conflicts between agents (e.g., one says low risk, another says high risk for the same aspect)
2. Findings that should be escalated in severity due to cross-agent patterns
3. Findings that should be reduced in severity because they're mitigated by another agent's findings

For each conflict found, describe the resolution.

Return JSON:
{{"conflicts_resolved": [{{"between": [str], "issue": str, "resolution": str, "severity_adjustment": str}}], "escalated_findings": [str], "mitigated_findings": [str]}}
"""


class SupervisorAgent(BaseAgent):
    agent_type = AgentType.SUPERVISOR
    agent_name = "SupervisorAgent"

    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        super().__init__()
        self.llm = llm or LLMClient(model_tier="expensive")
        self.risk_analyst = RiskAnalystAgent()
        self.loss_run_analyst = LossRunAnalystAgent()
        self.compliance_agent = ComplianceAgent()
        self.fraud_detection = FraudDetectionAgent()
        self.uw_decision = UWDecisionAgent()

    def analyze_submission(
        self,
        bundle: SubmissionBundle,
        parallel: bool = True,
    ) -> UnderwritingMemo:
        start = time.time()

        if parallel:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                risk_future = pool.submit(self.risk_analyst.run, bundle)
                loss_future = pool.submit(self.loss_run_analyst.run, bundle)
                comp_future = pool.submit(self.compliance_agent.run, bundle)
                fraud_future = pool.submit(self.fraud_detection.run, bundle)
                agent_results = [
                    risk_future.result(),
                    loss_future.result(),
                    comp_future.result(),
                    fraud_future.result(),
                ]
        else:
            agent_results = [
                self.risk_analyst.run(bundle),
                self.loss_run_analyst.run(bundle),
                self.compliance_agent.run(bundle),
                self.fraud_detection.run(bundle),
            ]

        conflict_resolution = self._resolve_conflicts(agent_results)

        agents_map = {ar.agent_name: ar for ar in agent_results}
        uw_result = self.uw_decision.run(bundle, agent_results=agents_map)
        agent_results.append(uw_result)

        memo = self.uw_decision.produce_underwriting_memo(
            bundle, agent_results, uw_result
        )

        if conflict_resolution:
            memo.review_notes.extend(conflict_resolution)

        elapsed = time.time() - start
        self._add_timing_to_memo(memo, agent_results, elapsed)

        return memo

    def analyze_submission_structured(
        self,
        bundle: SubmissionBundle,
    ) -> dict[str, Any]:
        memo = self.analyze_submission(bundle)
        return {
            "bundle_id": memo.bundle_id,
            "insured_name": memo.insured_name,
            "decision": memo.decision.value,
            "overall_risk_score": memo.overall_risk_score,
            "overall_risk_severity": memo.overall_risk_severity.value,
            "summary": memo.summary,
            "key_findings": [
                {
                    "title": f.title,
                    "severity": f.severity.value,
                    "category": f.category,
                    "description": f.description,
                }
                for f in memo.key_findings[:15]
            ],
            "conditions": memo.conditions,
            "human_review_required": memo.human_review_required,
            "human_review_reasons": memo.human_review_reasons,
            "agent_results": {
                name: {
                    "risk_score": r.risk_score,
                    "findings_count": len(r.findings),
                    "errors": r.errors,
                    "summary": r.summary,
                }
                for name, r in memo.agent_results.items()
            },
        }

    def _resolve_conflicts(self, results: list[AgentResult]) -> list[str]:
        if not self.llm.api_key:
            return self._resolve_conflicts_deterministic(results)

        try:
            findings_text = ""
            for r in results:
                findings_text += f"\n{r.agent_name} (risk score: {r.risk_score:.2f}):\n"
                for f in r.findings:
                    findings_text += f"  - [{f.severity.value}] {f.title}: {f.description[:100]}\n"

            raw = self.llm.complete(
                CONFLICT_RESOLUTION_PROMPT,
                findings_text,
            )

            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            notes = []
            for c in parsed.get("conflicts_resolved", []):
                between = " vs ".join(c.get("between", []))
                notes.append(
                    f"[CONFLICT RESOLVED] {between}: {c.get('issue', '')} → "
                    f"{c.get('resolution', '')} ({c.get('severity_adjustment', 'no change')})"
                )
            for f in parsed.get("escalated_findings", []):
                notes.append(f"[ESCALATED] {f}")
            for f in parsed.get("mitigated_findings", []):
                notes.append(f"[MITIGATED] {f}")
            return notes
        except Exception as e:
            return [f"Conflict resolution note: LLM processing failed ({type(e).__name__})"]

    def _resolve_conflicts_deterministic(self, results: list[AgentResult]) -> list[str]:
        notes = []
        severity_map = {"critical": 4, "high": 3, "moderate": 2, "low": 1}

        for i, r1 in enumerate(results):
            for r2 in results[i + 1:]:
                for f1 in r1.findings:
                    for f2 in r2.findings:
                        if f1.category == f2.category:
                            s1 = severity_map.get(f1.severity.value, 0)
                            s2 = severity_map.get(f2.severity.value, 0)
                            if abs(s1 - s2) >= 2:
                                notes.append(
                                    f"[CONFLICT RESOLVED] {r1.agent_name} vs {r2.agent_name}: "
                                    f"Category '{f1.category}' — "
                                    f"{r1.agent_name} says {f1.severity.value}, "
                                    f"{r2.agent_name} says {f2.severity.value}. "
                                    f"Using higher severity: {max(f1.severity.value, f2.severity.value)}"
                                )
        return notes

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        pass

    def _add_timing_to_memo(
        self,
        memo: UnderwritingMemo,
        results: list[AgentResult],
        total_elapsed: float,
    ) -> None:
        timing_note = f"Total agentic analysis: {total_elapsed:.1f}s | "
        timing_note += " | ".join(
            f"{r.agent_name}: {r.processing_time_ms:.0f}ms"
            for r in results
        )
        memo.review_notes.append(timing_note)
