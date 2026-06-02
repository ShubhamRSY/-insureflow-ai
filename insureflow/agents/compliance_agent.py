from __future__ import annotations

from typing import Any

from insureflow.agents.react_agent import ReActAgent
from insureflow.models.agents import AgentType, Finding, Recommendation, RiskSeverity
from insureflow.models.submissions import CoverageDetail, SubmissionBundle


class ComplianceAgent(ReActAgent):
    agent_type = AgentType.COMPLIANCE_AGENT
    agent_name = "ComplianceAgent"
    prompt_key = "compliance_agent"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        coverages = self.tools.get_coverages(bundle)
        if not coverages:
            self._add_finding(Finding(
                title="No coverage data available",
                description="Cannot verify coverage adequacy without coverage data",
                severity=RiskSeverity.HIGH,
                category="data_quality",
            ))
            return

        locations = self.tools.get_locations(bundle)
        total_iv = self.tools.total_insurable_value(locations)

        for cov in coverages:
            self._assess_sublimits(cov)
            self._assess_limit_adequacy(cov, total_iv)
            self._assess_deductible(cov)
            self._assess_endorsements(cov)

        self._assess_coverage_gaps(coverages)
        self._assess_named_insured(bundle)

    def _assess_sublimits(self, cov: CoverageDetail) -> None:
        high_sublimit_ratio_fields = []
        for sub_name, sub_limit in cov.sublimits.items():
            if cov.limit_amount > 0:
                ratio = sub_limit / cov.limit_amount
                if ratio < 0.1:
                    high_sublimit_ratio_fields.append(
                        f"{sub_name}: ${sub_limit:,.0f} ({ratio:.0%} of limit)"
                    )
        if high_sublimit_ratio_fields:
            self._add_finding(Finding(
                title="Restrictive sublimits detected",
                description=f"{cov.coverage_type}: {'; '.join(high_sublimit_ratio_fields)}",
                severity=RiskSeverity.MODERATE,
                category="sublimits",
                field_path=f"coverage.{cov.coverage_type}.sublimits",
                evidence=high_sublimit_ratio_fields,
            ))

    def _assess_limit_adequacy(self, cov: CoverageDetail, total_iv: float) -> None:
        if total_iv == 0:
            return
        ratio, status = self.tools.coverage_adequacy(cov, total_iv)
        if status == "inadequate":
            self._add_finding(Finding(
                title=f"Inadequate {cov.coverage_type} limit",
                description=f"Limit ${cov.limit_amount:,.0f} is {ratio:.0%} of total insurable value ${total_iv:,.0f}",
                severity=RiskSeverity.HIGH,
                category="limit_adequacy",
                field_path=f"coverage.{cov.coverage_type}.limit_amount",
                source_value=cov.limit_amount,
                recommended_value=total_iv,
            ))
        elif status == "marginal":
            self._add_finding(Finding(
                title=f"Marginal {cov.coverage_type} limit",
                description=f"Limit ${cov.limit_amount:,.0f} is {ratio:.0%} of TIV — consider increase",
                severity=RiskSeverity.MODERATE,
                category="limit_adequacy",
                field_path=f"coverage.{cov.coverage_type}.limit_amount",
                source_value=cov.limit_amount,
            ))

    def _assess_deductible(self, cov: CoverageDetail) -> None:
        if cov.limit_amount > 0:
            d_ratio = cov.deductible / cov.limit_amount
            if d_ratio > 0.1:
                self._add_finding(Finding(
                    title=f"High {cov.coverage_type} deductible",
                    description=f"${cov.deductible:,.0f} ({d_ratio:.0%} of limit)",
                    severity=RiskSeverity.MODERATE,
                    category="deductible",
                    field_path=f"coverage.{cov.coverage_type}.deductible",
                    source_value=cov.deductible,
                ))

    def _assess_endorsements(self, cov: CoverageDetail) -> None:
        if not cov.endorsements:
            return
        restricted_keywords = ("exclusion", "limitation", "restriction", "waiver")
        for end in cov.endorsements:
            elower = end.lower()
            if any(kw in elower for kw in restricted_keywords):
                self._add_finding(Finding(
                    title=f"Restrictive endorsement on {cov.coverage_type}",
                    description=end,
                    severity=RiskSeverity.MODERATE,
                    category="endorsement",
                    field_path=f"coverage.{cov.coverage_type}.endorsements",
                    evidence=([end] if isinstance(end, str) else end),
                ))

    def _assess_coverage_gaps(self, coverages: list[CoverageDetail]) -> None:
        cov_types = [c.coverage_type.lower() for c in coverages]
        expected = {
            "general liability": "General Liability",
            "property": "Property",
            "auto": "Commercial Auto",
        }
        covered = set()
        for ct in cov_types:
            for key, label in expected.items():
                if key in ct:
                    covered.add(key)
        missing = [expected[k] for k in expected if k not in covered]
        if missing:
            self._add_finding(Finding(
                title="Potential coverage gaps",
                description=f"Missing or unidentified: {', '.join(missing)}",
                severity=RiskSeverity.MODERATE,
                category="coverage_gaps",
                evidence=missing,
            ))

    def _assess_named_insured(self, bundle: SubmissionBundle) -> None:
        insured = self.tools.get_named_insured(bundle)
        if not insured or insured == bundle.bundle_id:
            self._add_finding(Finding(
                title="Named insured not identified",
                description="Unable to extract named insured from submission",
                severity=RiskSeverity.HIGH,
                category="data_quality",
            ))

    def _build_recommendation(self) -> Recommendation | None:
        high_sev = [f for f in self._findings if f.severity == RiskSeverity.HIGH]
        mod_sev = [f for f in self._findings if f.severity == RiskSeverity.MODERATE]
        conditions = []
        for f in high_sev:
            conditions.append(f"Resolve: {f.title} — {f.description[:80]}")
        for f in mod_sev[:3]:
            conditions.append(f"Review: {f.title} — {f.description[:80]}")
        if conditions:
            return Recommendation(
                action="review_conditions",
                rationale=f"{len(high_sev)} high-severity, {len(mod_sev)} moderate-severity compliance findings",
                conditions=conditions,
            )
        return None
