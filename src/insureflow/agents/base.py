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
            oracle_failures=self._oracle_failures if hasattr(self, "_oracle_failures") else [],
        )

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        raise NotImplementedError

    def _add_finding(self, finding: Finding) -> None:
        self._findings.append(finding)

    def _calculate_risk_score(self) -> float:
        """Calibrated risk score: severity-weighted average with volume amplification and category penalties.

        - Severity weights: critical=1.0, high=0.75, moderate=0.5, low=0.2
        - Volume amplification: log2(1 + count) / 6 caps at ~0.5x boost for large finding sets
        - Category penalties: fraud_detection/moral_hazard findings amplify the score
        - Confidence adjustment: higher-confidence findings weigh more
        - No artificial 0.8 cap — the volume amp + category penalty naturally bound the score
        """
        if not self._findings:
            return 0.0  # Consistent default: no findings = no risk (was 0.5)

        severity_weights = {"critical": 1.0, "high": 0.75, "moderate": 0.5, "low": 0.2}
        high_risk_categories = {"fraud_detection", "moral_hazard", "selection", "adverse_selection"}

        weighted_sum = 0.0
        confidence_sum = 0.0
        high_risk_count = 0
        total_weight = 0.0

        for f in self._findings:
            sev_weight = severity_weights.get(f.severity.value, 0.5)
            conf = getattr(f, "confidence", None) or 0.7  # default 70% if not set
            conf_weight = 0.5 + conf * 0.5  # range [0.5, 1.0]
            effective_weight = sev_weight * conf_weight
            weighted_sum += effective_weight
            confidence_sum += conf
            total_weight += 1.0
            if f.category in high_risk_categories:
                high_risk_count += 1

        if total_weight == 0:
            return 0.0

        base_score = weighted_sum / total_weight

        # Volume amplification: log2(1 + count) / 6 → max ~0.5x boost at 63 findings
        import math
        volume_amp = math.log2(1.0 + total_weight) / 6.0

        # Category penalty: +0.1 per high-risk category finding (capped at +0.3)
        category_penalty = min(0.3, high_risk_count * 0.1)

        # Average confidence factor: low-confidence findings reduce score slightly
        avg_confidence = confidence_sum / total_weight
        confidence_factor = 0.85 + 0.15 * avg_confidence  # range [0.85, 1.0]

        score = (base_score + volume_amp + category_penalty) * confidence_factor
        return min(1.0, max(0.0, score))

    def _build_recommendation(self) -> Optional[Recommendation]:
        return None

    def _build_summary(self) -> str:
        if self._errors:
            return f"{self.agent_name}: {len(self._errors)} error(s)"
        return f"{self.agent_name}: {len(self._findings)} finding(s), risk score {self._calculate_risk_score():.2f}"

    def _get_sources(self, bundle: SubmissionBundle) -> list[str]:
        return bundle.all_sources()
