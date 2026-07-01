from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentResult, AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.oracles.ncci_codes import get_ncci_description, is_high_risk_ncci_class
from insureflow.rag.guidelines import builtin_carrier_appetite_rules


class AppetiteFilterResult:
    """Result of the fast-fail appetite filter check."""

    def __init__(
        self,
        passed: bool,
        findings: list[Finding],
        reason: str = "",
        needs_uw_referral: bool = False,
    ) -> None:
        self.passed = passed
        self.findings = findings
        self.reason = reason
        self.needs_uw_referral = needs_uw_referral

    def to_agent_result(self, processing_time_ms: float) -> AgentResult:
        severity = RiskSeverity.CRITICAL if not self.passed else RiskSeverity.LOW
        return AgentResult(
            agent_type=AgentType.APPETITE_FILTER,
            agent_name="AppetiteFilterAgent",
            success=self.passed or self.needs_uw_referral,
            findings=self.findings,
            risk_score=0.0 if self.passed else 0.9,
            risk_severity=severity,
            summary=self.reason
            or ("Appetite check passed" if self.passed else "Risk out of appetite"),
            processing_time_ms=round(processing_time_ms, 1),
            data_sources_used=["carrier_appetite_guidelines"],
        )


class AppetiteFilterAgent(BaseAgent):
    agent_type = AgentType.APPETITE_FILTER
    agent_name = "AppetiteFilterAgent"

    def __init__(self) -> None:
        super().__init__()
        self.rules = builtin_carrier_appetite_rules()

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        result = self.check_appetite(bundle)
        if not result.passed:
            for f in result.findings:
                self._add_finding(f)

    def check_appetite(self, bundle: SubmissionBundle) -> AppetiteFilterResult:
        findings: list[Finding] = []

        findings.extend(self._check_naics(bundle))
        findings.extend(self._check_geography(bundle))
        findings.extend(self._check_minimum_tiv(bundle))
        findings.extend(self._check_maximum_tiv(bundle))
        findings.extend(self._check_loss_ratio(bundle))
        findings.extend(self._check_entity_restrictions(bundle))
        findings.extend(self._check_minimum_premium(bundle))
        findings.extend(self._check_years_in_business(bundle))
        findings.extend(self._check_prior_carrier_cancellation(bundle))
        findings.extend(self._check_ncci_class_code(bundle))

        critical = [f for f in findings if f.severity == RiskSeverity.CRITICAL]
        high = [f for f in findings if f.severity == RiskSeverity.HIGH]

        if critical:
            reason = "; ".join(f.title for f in critical)
            return AppetiteFilterResult(passed=False, findings=findings, reason=reason)
        if high:
            reason = "; ".join(f.title for f in high)
            return AppetiteFilterResult(
                passed=False, findings=findings, reason=reason, needs_uw_referral=True
            )

        return AppetiteFilterResult(
            passed=True, findings=findings, reason="All appetite checks passed"
        )

    def _check_naics(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        naics = ""
        if bundle.structured and bundle.structured.risk_profile:
            naics = bundle.structured.risk_profile.naics_code or ""
        if not naics and bundle.structured:
            for doc in bundle.unstructured:
                for fields in doc.extracted_fields.get("naics_code", []):
                    naics = fields.value
                    break
        excluded_prefixes = ("7211", "1133", "2131", "4821", "4911", "9211")
        if naics and naics.startswith(excluded_prefixes):
            findings.append(
                Finding(
                    title="Excluded NAICS code",
                    description=f"NAICS {naics} falls in an excluded industry category per carrier appetite",
                    severity=RiskSeverity.CRITICAL,
                    category="carrier_appetite",
                    field_path="risk_profile.naics_code",
                    source_value=naics,
                )
            )
        elif naics:
            preferred_prefixes = ("44", "45", "53", "54", "56", "62", "72", "81")
            if not naics.startswith(preferred_prefixes):
                findings.append(
                    Finding(
                        title="Non-preferred NAICS code",
                        description=f"NAICS {naics} is not in the preferred industry list — requires UW review",
                        severity=RiskSeverity.HIGH,
                        category="carrier_appetite",
                        field_path="risk_profile.naics_code",
                        source_value=naics,
                    )
                )
        return findings

    def _check_geography(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        locations = self.tools.get_locations(bundle)
        for loc in locations:
            state = (loc.state or "").upper()
            zip_code = (loc.zip_code or "").strip()
            if state == "FL":
                try:
                    zip_int = int(zip_code[:5]) if zip_code else 0
                    if 32000 <= zip_int <= 34999:
                        findings.append(
                            Finding(
                                title="Coastal Florida location — out of appetite",
                                description=f"{loc.city}, FL {zip_code} is in a coastal CAT-excluded zone",
                                severity=RiskSeverity.CRITICAL,
                                category="carrier_appetite",
                                field_path="location.zip_code",
                                source_value=zip_code,
                            )
                        )
                except ValueError:
                    pass
            elif state == "TX":
                try:
                    zip_int = int(zip_code[:5]) if zip_code else 0
                    if 77500 <= zip_int <= 78500:
                        findings.append(
                            Finding(
                                title="Coastal Texas location — out of appetite",
                                description=f"{loc.city}, TX {zip_code} is in a coastal CAT-excluded zone",
                                severity=RiskSeverity.CRITICAL,
                                category="carrier_appetite",
                                field_path="location.zip_code",
                                source_value=zip_code,
                            )
                        )
                except ValueError:
                    pass
            elif state == "HI":
                findings.append(
                    Finding(
                        title="Hawaii location — out of appetite",
                        description="Hawaii is ineligible for new business per carrier appetite",
                        severity=RiskSeverity.CRITICAL,
                        category="carrier_appetite",
                        field_path="location.state",
                        source_value="HI",
                    )
                )
        return findings

    def _check_minimum_tiv(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        locations = self.tools.get_locations(bundle)
        for loc in locations:
            tiv = (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
            if 0 < tiv < 50_000:
                findings.append(
                    Finding(
                        title="TIV below minimum threshold",
                        description=f"Location TIV ${tiv:,.0f} is below the $50,000 minimum per carrier appetite",
                        severity=RiskSeverity.HIGH,
                        category="carrier_appetite",
                        field_path="location",
                        source_value=tiv,
                    )
                )
        return findings

    def _check_maximum_tiv(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        locations = self.tools.get_locations(bundle)
        for loc in locations:
            tiv = (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
            if tiv > 25_000_000:
                findings.append(
                    Finding(
                        title="TIV exceeds maximum threshold",
                        description=f"Location TIV ${tiv:,.0f} exceeds the $25M maximum — facultative reinsurance required",
                        severity=RiskSeverity.CRITICAL,
                        category="carrier_appetite",
                        field_path="location",
                        source_value=tiv,
                        recommended_value=25_000_000,
                    )
                )
        return findings

    def _check_loss_ratio(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        loss_run = self.tools.get_loss_run(bundle)
        if loss_run and loss_run.loss_ratios:
            max_lr = max(loss_run.loss_ratios.values())
            if max_lr > 0.80:
                findings.append(
                    Finding(
                        title="Loss ratio exceeds appetite threshold",
                        description=f"5-year loss ratio of {max_lr:.0%} exceeds the 80% maximum for new business",
                        severity=RiskSeverity.CRITICAL,
                        category="carrier_appetite",
                        field_path="financial.loss_run.loss_ratios",
                        source_value=max_lr,
                    )
                )
            elif max_lr > 0.65:
                findings.append(
                    Finding(
                        title="Loss ratio requires UW referral",
                        description=f"5-year loss ratio of {max_lr:.0%} exceeds the 65% referral threshold",
                        severity=RiskSeverity.HIGH,
                        category="carrier_appetite",
                        field_path="financial.loss_run.loss_ratios",
                        source_value=max_lr,
                    )
                )
        return findings

    def _check_entity_restrictions(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        if bundle.structured and bundle.structured.named_insured:
            name = (bundle.structured.named_insured.legal_name or "").lower()
            entity_type = (bundle.structured.named_insured.entity_type or "").lower()
            restricted_terms = ["government", "usda", "federal", "state of", "county of", "city of"]
            if any(t in name for t in restricted_terms) or entity_type == "government":
                findings.append(
                    Finding(
                        title="Government entity — out of standard appetite",
                        description=f"'{bundle.structured.named_insured.legal_name}' is a government entity and requires specialized underwriting",
                        severity=RiskSeverity.HIGH,
                        category="carrier_appetite",
                        field_path="named_insured.entity_type",
                        source_value=entity_type or name,
                    )
                )
        return findings

    def _check_minimum_premium(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        premium = 0.0
        if bundle.structured:
            for cov in bundle.structured.coverages:
                premium += cov.premium
        if 0 < premium < 2_500:
            findings.append(
                Finding(
                    title="Estimated premium below minimum threshold",
                    description=f"Estimated annual premium ${premium:,.0f} is below the $2,500 minimum per carrier appetite (APT-002)",
                    severity=RiskSeverity.HIGH,
                    category="carrier_appetite",
                    field_path="coverages.premium",
                    source_value=premium,
                )
            )
        elif premium > 250_000:
            findings.append(
                Finding(
                    title="Estimated premium exceeds maximum threshold",
                    description=f"Estimated annual premium ${premium:,.0f} exceeds the $250,000 maximum without facultative reinsurance approval (APT-002)",
                    severity=RiskSeverity.HIGH,
                    category="carrier_appetite",
                    field_path="coverages.premium",
                    source_value=premium,
                )
            )
        return findings

    def _check_years_in_business(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        for doc in bundle.unstructured:
            for fields in doc.extracted_fields.get("year_founded", []):
                try:
                    founded = int(fields.value)
                    from datetime import date

                    years = date.today().year - founded
                    if years < 2:
                        findings.append(
                            Finding(
                                title="Entity fewer than 2 years in business",
                                description=f"Founded {founded} ({years} years) — minimum 2 years required per carrier appetite (APT-005)",
                                severity=RiskSeverity.HIGH,
                                category="carrier_appetite",
                                field_path="financial.years_in_business",
                                source_value=years,
                            )
                        )
                except (ValueError, TypeError):
                    pass
        return findings

    def _check_prior_carrier_cancellation(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        text_sources: list[str] = []
        if bundle.structured and bundle.structured.raw_xml:
            text_sources.append(bundle.structured.raw_xml)
        if bundle.structured and bundle.structured.raw_json:
            text_sources.append(bundle.structured.raw_json)
        for doc in bundle.unstructured:
            text_sources.append(doc.raw_text)
        cancellation_terms = ["cancelled", "non-renewed", "nonrenewed", "declined", "prior carrier"]
        seen = set()
        for text in text_sources:
            text_lower = text.lower()
            for term in cancellation_terms:
                if term in text_lower and term not in seen:
                    seen.add(term)
                    findings.append(
                        Finding(
                            title="Prior carrier cancellation or non-renewal detected",
                            description=f"Submission contains reference to '{term}' — prior cancellation/non-renewal within 3 years is ineligible (APT-008)",
                            severity=RiskSeverity.CRITICAL,
                            category="carrier_appetite",
                            evidence=[term],
                        )
                    )
        return findings

    def _check_ncci_class_code(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        ncci_class = ""
        if bundle.structured and bundle.structured.risk_profile:
            ncci_class = bundle.structured.risk_profile.ncci_class_code or ""
        if not ncci_class:
            for doc in bundle.unstructured:
                for fields in doc.extracted_fields.get("ncci_class_code", []):
                    ncci_class = fields.value
                    break
        if not ncci_class:
            return findings

        desc = get_ncci_description(ncci_class)
        if is_high_risk_ncci_class(ncci_class):
            findings.append(
                Finding(
                    title="High-risk NCCI class code",
                    description=f"NCCI class {ncci_class} ({desc}) is in a high-risk category — requires UW referral",
                    severity=RiskSeverity.HIGH,
                    category="carrier_appetite",
                    field_path="risk_profile.ncci_class_code",
                    source_value=ncci_class,
                )
            )
        return findings
