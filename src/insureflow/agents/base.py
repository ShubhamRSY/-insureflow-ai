from __future__ import annotations

import time
from typing import Any, Optional

from insureflow.agents.tools import UnderwritingTools
from insureflow.models.agents import AgentResult, AgentType, Finding, Recommendation
from insureflow.models.submissions import SubmissionBundle


class BaseAgent:
    agent_type: AgentType
    agent_name: str = "base"

    def __init__(self, tools: Optional[UnderwritingTools] = None) -> None:
        self.tools = tools or UnderwritingTools()
        self._findings: list[Finding] = []
        self._errors: list[str] = []

    def run(self, bundle: SubmissionBundle, **kwargs: Any) -> AgentResult:
        start = time.time()
        self._findings = []
        self._errors = []

        try:
            self._analyze(bundle, **kwargs)
        except Exception as e:
            self._errors.append(f"{type(e).__name__}: {e}")

        elapsed = (time.time() - start) * 1000
        severity = self.tools.assess_overall_severity(self._findings)
        return AgentResult(
            agent_type=self.agent_type,
            agent_name=self.agent_name,
            findings=self._findings,
            risk_score=self._calculate_risk_score(),
            risk_severity=severity,
            recommendation=self._build_recommendation(),
            summary=self._build_summary(),
            errors=self._errors,
            processing_time_ms=round(elapsed, 1),
            success=len(self._errors) == 0,
            data_sources_used=self._get_sources(bundle),
        )

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        raise NotImplementedError

    def _add_finding(self, finding: Finding) -> None:
        self._findings.append(finding)

    def _calculate_risk_score(self) -> float:
        if not self._findings:
            return 0.5
        weights = {"critical": 1.0, "high": 0.75, "moderate": 0.5, "low": 0.2}
        scores = [weights.get(f.severity.value, 0.5) for f in self._findings]
        return min(1.0, sum(scores) / len(scores) * 0.8)

    def _build_recommendation(self) -> Optional[Recommendation]:
        return None

    def _build_summary(self) -> str:
        if self._errors:
            return f"{self.agent_name}: {len(self._errors)} error(s)"
        return (f"{self.agent_name}: {len(self._findings)} finding(s), "
                f"risk score {self._calculate_risk_score():.2f}")

    def _get_sources(self, bundle: SubmissionBundle) -> list[str]:
        return bundle.all_sources()
