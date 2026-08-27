from __future__ import annotations

import time
from typing import Any, Optional

from insureflow.agents.tools import UnderwritingTools
from insureflow.models.agents import AgentResult, AgentType, Finding, Recommendation
from insureflow.models.submissions import SubmissionBundle

# Data-availability noise, not underwriting risk signal: an oracle being down or a
# figure failing hallucination-grounding says nothing about this applicant's risk.
# Excluded from risk-score arithmetic in both BaseAgent and UWDecisionAgent; still
# shown to the underwriter and still forces REFER via dedicated pipeline handling.
NOISE_CATEGORIES = {"oracle_failure", "external_oracle", "hallucination"}


class BaseAgent:
    agent_type: AgentType
    agent_name: str = "base"

    def __init__(self, tools: Optional[UnderwritingTools] = None) -> None:
        self.tools = tools or UnderwritingTools()
        self._findings: list[Finding] = []
        self._errors: list[str] = []
        self.bundle: Optional[SubmissionBundle] = None

    def run(self, bundle: SubmissionBundle, **kwargs: Any) -> AgentResult:
        start = time.time()
        self._findings = []
        self._errors = []
        self.bundle = bundle

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
        self._attribute_finding(finding)
        self._findings.append(finding)

    def _attribute_finding(self, finding: Finding) -> None:
        """Backfill provenance (source_document/extraction_method/confidence)
        so a reviewer never sees a blank attribution line.

        Per-field confidence/notes (real extraction signal from the ACORD/JSON
        parsers, keyed by dotted field_path) take priority when the finding
        names a specific field and hasn't already been given an explicit,
        non-default confidence. Everything else falls back to a bundle-level
        source/method — coarser, but never empty.
        """
        bundle = self.bundle
        if bundle is None:
            return
        structured = bundle.structured

        if finding.field_path and structured:
            real_confidence = structured.field_confidence.get(finding.field_path)
            if real_confidence is not None and finding.confidence == 0.8:
                finding.confidence = real_confidence
            note = structured.field_notes.get(finding.field_path)
            if note and not finding.extraction_method:
                finding.extraction_method = "structured_parser"
                if not finding.evidence:
                    finding.evidence = [note]

        if not finding.source_document:
            if structured and structured.source:
                finding.source_document = structured.source
            elif bundle.unstructured:
                finding.source_document = bundle.unstructured[0].source or bundle.unstructured[0].document_type
            else:
                finding.source_document = "submission package"

        if not finding.extraction_method:
            finding.extraction_method = "structured_parser" if structured else "llm_extraction"

    def _calculate_risk_score(self) -> float:
        """Calibrated risk score: severity-weighted average plus a capped pile-up bonus.

        - Severity weights: critical=1.0, high=0.75, moderate=0.5, low=0.2
        - Environmental findings (oracle_failure/external_oracle/hallucination) are
          data-availability noise, not underwriting risk signal — they're excluded
          from the score entirely. They still appear in findings and independently
          force REFER via dedicated pipeline handling; they must not also inflate
          the score toward DECLINE on files that are otherwise clean.
        - Volume amplification (log2(1 + count) / 6) only counts MODERATE+ findings
          — routine LOW-severity/informational findings (reinsurance summaries,
          portfolio stats, clean OFAC screens) fire on nearly every submission and
          must not read as a "pile-up of problems".
        - volume_amp + category_penalty together are capped at +0.15 so pile-up
          effects can nudge the score but never dominate the severity average,
          and a file with only a couple of genuine findings (not a real
          pile-up) stays comfortably clear of the 0.85 decline threshold
          instead of riding the edge, where ordinary run-to-run variance in
          confidence/thread scheduling can tip a clean file over it.
        - Confidence adjustment: higher-confidence findings weigh more.
        """
        severity_weights = {"critical": 1.0, "high": 0.75, "moderate": 0.5, "low": 0.2}
        high_risk_categories = {"fraud_detection", "moral_hazard", "selection", "adverse_selection"}

        scored = [f for f in self._findings if f.category not in NOISE_CATEGORIES]
        if not scored:
            return 0.0  # Consistent default: no findings = no risk (was 0.5)

        weighted_sum = 0.0
        confidence_sum = 0.0
        high_risk_count = 0
        volume_count = 0.0
        total_weight = 0.0

        for f in scored:
            sev_weight = severity_weights.get(f.severity.value, 0.5)
            conf = getattr(f, "confidence", None) or 0.7  # default 70% if not set
            conf_weight = 0.5 + conf * 0.5  # range [0.5, 1.0]
            effective_weight = sev_weight * conf_weight
            weighted_sum += effective_weight
            confidence_sum += conf
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

        # Category penalty: +0.1 per high-risk category finding (capped at +0.3)
        category_penalty = min(0.3, high_risk_count * 0.1)

        # Pile-up bonus: volume + category together nudge the score, never dominate it
        pileup_bonus = min(0.15, volume_amp + category_penalty)

        # Average confidence factor: low-confidence findings reduce score slightly
        avg_confidence = confidence_sum / total_weight
        confidence_factor = 0.85 + 0.15 * avg_confidence  # range [0.85, 1.0]

        score = (base_score + pileup_bonus) * confidence_factor
        return min(1.0, max(0.0, score))

    def _build_recommendation(self) -> Optional[Recommendation]:
        return None

    def _build_summary(self) -> str:
        if self._errors:
            return f"{self.agent_name}: {len(self._errors)} error(s)"
        return f"{self.agent_name}: {len(self._findings)} finding(s), risk score {self._calculate_risk_score():.2f}"

    def _get_sources(self, bundle: SubmissionBundle) -> list[str]:
        return bundle.all_sources()
