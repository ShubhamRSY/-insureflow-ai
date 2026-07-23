from __future__ import annotations

from typing import Any

from insureflow.agents.react_agent import ReActAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle


class FraudDetectionAgent(ReActAgent):
    agent_type = AgentType.FRAUD_DETECTION
    agent_name = "FraudDetectionAgent"
    prompt_key = "fraud_detection"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        self._check_non_disclosed_losses(bundle)
        self._check_valuation_discrepancies(bundle)
        self._check_entity_consistency(bundle)
        self._check_recent_loss_cluster(bundle)
        self._ml_fraud_scoring(bundle)

    def _check_non_disclosed_losses(self, bundle: SubmissionBundle) -> None:
        loss_run = self.tools.get_loss_run(bundle)
        if not loss_run or not loss_run.claims:
            return

        structured_claims = []
        if bundle.structured and bundle.structured.financial:
            structured_claims = bundle.structured.financial.prior_losses

        non_disclosed = self.tools.find_non_disclosed_losses(loss_run.claims, structured_claims)
        if non_disclosed:
            self._add_finding(
                Finding(
                    title="Non-disclosed claims detected",
                    description=f"{len(non_disclosed)} claim(s) in loss run not found in structured submission",
                    severity=RiskSeverity.HIGH,
                    category="non_disclosure",
                    evidence=[f"{c.claim_id}: ${c.incurred_amount:,.0f} ({c.date_of_loss})" for c in non_disclosed],
                )
            )

        for c in loss_run.claims:
            text = f"{c.cause} {c.notes} {c.description}".lower()
            if "not disclosed" in text:
                self._add_finding(
                    Finding(
                        title="Applicant acknowledged non-disclosure in loss run notes",
                        description=f"{c.claim_id}: {c.cause[:100]}",
                        severity=RiskSeverity.CRITICAL,
                        category="intentional_non_disclosure",
                        evidence=[c.notes, c.cause, f"Incurred: ${c.incurred_amount:,.0f}"],
                    )
                )

    def _check_valuation_discrepancies(self, bundle: SubmissionBundle) -> None:
        locations = self.tools.get_locations(bundle)
        sovs = self.tools.get_sovs(bundle)

        if not locations or not sovs:
            return

        sov_total = sum(s.total_value for s in sovs)
        loc_total = self.tools.total_insurable_value(locations)

        if loc_total > 0 and sov_total > 0:
            ratio = sov_total / loc_total
            if ratio < 0.6:
                self._add_finding(
                    Finding(
                        title="Significant SOV vs location valuation gap",
                        description=f"SOV ${sov_total:,.0f} vs location values ${loc_total:,.0f} ({ratio:.0%})",
                        severity=RiskSeverity.HIGH,
                        category="valuation_mismatch",
                        field_path="schedule_of_values",
                        evidence=[
                            f"Location total: ${loc_total:,.0f}",
                            f"SOV total: ${sov_total:,.0f}",
                        ],
                    )
                )
            elif ratio > 1.4:
                self._add_finding(
                    Finding(
                        title="SOV significantly exceeds location values",
                        description=f"SOV ${sov_total:,.0f} exceeds location values ${loc_total:,.0f} ({ratio:.0%})",
                        severity=RiskSeverity.MODERATE,
                        category="valuation_mismatch",
                        field_path="schedule_of_values",
                    )
                )

    def _check_entity_consistency(self, bundle: SubmissionBundle) -> None:
        names_seen: set[str] = set()
        if bundle.structured and bundle.structured.named_insured:
            names_seen.add(bundle.structured.named_insured.legal_name.lower().strip())

        for u_doc in bundle.unstructured:
            for field_list in u_doc.extracted_fields.values():
                for ef in field_list:
                    if "insured" in ef.field_name.lower() or "name" in ef.field_name.lower():
                        names_seen.add(ef.value.lower().strip())

        if len(names_seen) > 1:
            self._add_finding(
                Finding(
                    title="Inconsistent entity names across documents",
                    description=f"Found {len(names_seen)} different name variations",
                    severity=RiskSeverity.MODERATE,
                    category="entity_mismatch",
                    evidence=list(names_seen),
                )
            )

    def _check_recent_loss_cluster(self, bundle: SubmissionBundle) -> None:
        loss_run = self.tools.get_loss_run(bundle)
        if not loss_run or len(loss_run.claims) < 3:
            return

        sorted_claims = sorted(loss_run.claims, key=lambda c: c.date_of_loss)
        recent = sorted_claims[-3:]
        dates = [c.date_of_loss for c in recent]

        if len(dates) >= 3:
            span = (dates[-1] - dates[0]).days
            if span <= 180:
                self._add_finding(
                    Finding(
                        title="Cluster of recent claims",
                        description=f"3 claims in last {span} days",
                        severity=RiskSeverity.MODERATE,
                        category="claim_cluster",
                        evidence=[f"{c.claim_id}: {c.date_of_loss}" for c in recent],
                    )
                )

    def _ml_fraud_scoring(self, bundle: SubmissionBundle) -> None:
        """Run ML fraud anomaly detection on submission features."""
        from insureflow.agents.tools import MLTools

        tiv = 0.0
        prior_claims = 0

        if bundle.structured:
            for loc in bundle.structured.locations:
                tiv += (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
            if bundle.structured.risk_profile:
                prior_claims = len(bundle.structured.risk_profile.prior_claims)

        if tiv == 0:
            return

        try:
            result = MLTools.predict_fraud(
                tiv=tiv,
                loss_ratio=0.5,
                prior_claims_count=prior_claims,
            )
        except Exception:
            return

        if "error" in result:
            return

        prob = result.get("fraud_probability", 0)
        risk_level = result.get("risk_level", "low")
        patterns = result.get("flagged_patterns", [])

        if risk_level in ("high", "critical"):
            sev = RiskSeverity.CRITICAL if risk_level == "critical" else RiskSeverity.HIGH
            self._add_finding(
                Finding(
                    title="ML fraud anomaly detected",
                    description=f"ML fraud probability: {prob:.1%}, risk level: {risk_level}",
                    severity=sev,
                    category="ml_fraud",
                    source_value=prob,
                    evidence=patterns or [f"Anomaly score: {result.get('anomaly_score', 0):.4f}"],
                )
            )
        elif risk_level == "medium":
            self._add_finding(
                Finding(
                    title="ML fraud model flagged elevated risk",
                    description=f"ML fraud probability: {prob:.1%}, risk level: {risk_level}",
                    severity=RiskSeverity.MODERATE,
                    category="ml_fraud",
                    source_value=prob,
                )
            )
