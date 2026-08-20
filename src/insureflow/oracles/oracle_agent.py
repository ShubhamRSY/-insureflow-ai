from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, OracleFailure, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.oracles.aplus_client import APlusClient
from insureflow.oracles.bureau_client import CreditBureauClient
from insureflow.oracles.cat_model_client import CatastropheModelClient
from insureflow.oracles.clue_client import CLUEClient
from insureflow.oracles.mvr_client import MVRClient, extract_drivers
from insureflow.oracles.ncci_client import NCCIClient
from insureflow.oracles.osha_client import OSHAClient
from insureflow.oracles.public_records_client import PublicRecordsClient
from insureflow.oracles.rating_agency_client import CreditRatingAgencyClient
from insureflow.oracles.telematics_client import CyberScanClient, TelematicsClient, extract_domain, extract_vin


class OracleAgent(BaseAgent):
    """Agent that queries external data sources (CLUE, A-PLUS, NCCI, CAT models,
    credit bureau, public records, OSHA, rating agencies) to catch hidden claims
    history, property losses, workers comp experience, catastrophe exposure,
    financial distress, litigation, workplace-safety, and credit risk."""

    agent_type = AgentType.ORACLE_AGENT
    agent_name = "OracleAgent"

    CRITICAL_ORACLES = frozenset({"CLUE", "A-PLUS", "NCCI", "CAT"})

    def __init__(
        self,
        clue_client: CLUEClient | None = None,
        aplus_client: APlusClient | None = None,
        ncci_client: NCCIClient | None = None,
        cat_model: CatastropheModelClient | None = None,
        bureau_client: CreditBureauClient | None = None,
        public_records_client: PublicRecordsClient | None = None,
        osha_client: OSHAClient | None = None,
        rating_agency_client: CreditRatingAgencyClient | None = None,
        mvr_client: MVRClient | None = None,
        telematics_client: TelematicsClient | None = None,
        cyber_scan_client: CyberScanClient | None = None,
    ) -> None:
        super().__init__()
        self.clue = clue_client or CLUEClient()
        self.aplus = aplus_client or APlusClient()
        self.ncci = ncci_client or NCCIClient()
        self.cat_model = cat_model or CatastropheModelClient()
        self.bureau = bureau_client or CreditBureauClient()
        self.public_records = public_records_client or PublicRecordsClient()
        self.osha = osha_client or OSHAClient()
        self.rating_agency = rating_agency_client or CreditRatingAgencyClient()
        self.mvr = mvr_client or MVRClient()
        self.telematics = telematics_client or TelematicsClient()
        self.cyber_scan = cyber_scan_client or CyberScanClient()
        self.last_ncci_emod: float | None = None
        self.last_mvr_cleared: bool | None = None
        self._oracle_failures: list[OracleFailure] = []

    def _record_oracle_failure(
        self,
        oracle_name: str,
        status: str,
        error_code: str = "",
        error_message: str = "",
        query_completed: bool = False,
        mode: str = "",
        is_critical: bool = True,
        retry_count: int = 0,
    ) -> None:
        """Record a structured oracle failure for pipeline REFER decisions."""
        self._oracle_failures.append(
            OracleFailure(
                oracle_name=oracle_name,
                status=status,
                error_code=error_code,
                error_message=error_message,
                timestamp=datetime.now(),
                query_completed=query_completed,
                mode=mode,
                is_critical=is_critical,
                retry_count=retry_count,
            )
        )

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        self.last_ncci_emod = None
        self.last_mvr_cleared = None
        self._oracle_failures = []
        line = str(kwargs.get("insurance_line") or "")
        queries = [
            self._query_clue(bundle),
            self._query_aplus(bundle),
            self._query_ncci(bundle),
            self._model_catastrophe_risk(bundle),
            self._query_bureau(bundle),
            self._query_public_records(bundle),
            self._query_osha(bundle),
            self._query_rating_agency(bundle),
        ]
        if self._should_query_mvr(bundle, line):
            queries.append(self._query_mvr(bundle))
        if self._should_query_telematics(bundle, line):
            queries.append(self._query_telematics(bundle))
        if self._should_query_cyber(bundle, line):
            queries.append(self._query_cyber_scan(bundle))
        for findings in queries:
            for f in findings:
                self._add_finding(f)

    def _identity(self, bundle: SubmissionBundle) -> tuple[str, str, str]:
        insured_name = self.tools.get_named_insured(bundle)
        address = ""
        tax_id = ""
        if bundle.structured:
            if bundle.structured.named_insured:
                tax_id = bundle.structured.named_insured.tax_id or ""
            if bundle.structured.locations:
                loc = bundle.structured.locations[0]
                address = f"{loc.address}, {loc.city}, {loc.state} {loc.zip_code}"
        return insured_name, tax_id, address

    def _query_clue(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        insured_name = self.tools.get_named_insured(bundle)
        if not insured_name or insured_name == bundle.bundle_id:
            return findings

        address = ""
        tax_id = ""
        if bundle.structured:
            if bundle.structured.named_insured:
                tax_id = bundle.structured.named_insured.tax_id or ""
            if bundle.structured.locations:
                loc = bundle.structured.locations[0]
                address = f"{loc.address}, {loc.city}, {loc.state} {loc.zip_code}"

        result = self.clue.query_by_name_and_address(insured_name, address, tax_id)

        if result.error:
            self._record_oracle_failure(
                oracle_name="CLUE",
                status="error",
                error_code="CLUE_QUERY_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.clue._resolved_mode(),
                is_critical=True,
            )
            findings.append(
                Finding(
                    title="CLUE query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

        if result.synthetic or self.clue._resolved_mode() != "live":
            self._record_oracle_failure(
                oracle_name="CLUE",
                status="error",
                error_code="CLUE_NOT_LIVE",
                error_message=f"CLUE query did not complete in live mode (mode={self.clue._resolved_mode()})",
                query_completed=result.query_completed,
                mode=result.mode or self.clue._resolved_mode(),
                is_critical=True,
            )

        if result.total_claims_found > 0:
            for record in result.records:
                sev = RiskSeverity.CRITICAL if record.current_status == "open" and record.paid_amount > 50_000 else RiskSeverity.HIGH
                findings.append(
                    Finding(
                        title=f"CLUE: {record.loss_type.replace('_', ' ').title()} claim found ({record.current_status})",
                        description=f"Paid ${record.paid_amount:,.0f} on {record.date_of_loss} — {record.description[:120]}",
                        severity=sev,
                        category="external_oracle",
                        evidence=[
                            f"CLUE Claim: {record.claim_id}",
                            f"Status: {record.current_status}",
                            f"Paid: ${record.paid_amount:,.0f}",
                        ],
                    )
                )

        if result.has_prior_litigation:
            findings.append(
                Finding(
                    title="CLUE: Prior litigation history detected",
                    description="External database shows prior litigation involving this insured",
                    severity=RiskSeverity.CRITICAL,
                    category="external_oracle",
                )
            )

        if result.has_prior_cancellation:
            findings.append(
                Finding(
                    title="CLUE: Prior cancellation / non-renewal history",
                    description="External database shows prior carrier cancellation or non-renewal",
                    severity=RiskSeverity.CRITICAL,
                    category="external_oracle",
                )
            )

        if result.total_claims_found == 0:
            unverified = self.clue._resolved_mode() != "live"
            if unverified:
                findings.append(
                    Finding(
                        title="CLUE: External verification unavailable",
                        description=(f"CLUE query for {insured_name} did not complete in live mode (mode={self.clue._resolved_mode()}). Configure live LexisNexis credentials."),
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
                        evidence=[f"mode={self.clue._resolved_mode()}"],
                    )
                )
            else:
                findings.append(
                    Finding(
                        title="CLUE: Clean external loss history",
                        description=f"No claims found in CLUE database for {insured_name}",
                        severity=RiskSeverity.LOW,
                        category="external_oracle",
                    )
                )

        return findings

    def _query_aplus(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        insured_name = self.tools.get_named_insured(bundle)
        if not insured_name or insured_name == bundle.bundle_id:
            return findings

        address = ""
        tax_id = ""
        if bundle.structured:
            if bundle.structured.named_insured:
                tax_id = bundle.structured.named_insured.tax_id or ""
            if bundle.structured.locations:
                loc = bundle.structured.locations[0]
                address = f"{loc.address}, {loc.city}, {loc.state} {loc.zip_code}"

        result = self.aplus.query_by_property(insured_name, address, tax_id)

        if result.error:
            self._record_oracle_failure(
                oracle_name="A-PLUS",
                status="error",
                error_code="APLUS_QUERY_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.aplus._resolved_mode(),
                is_critical=True,
            )
            findings.append(
                Finding(
                    title="A-PLUS query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

        if self.aplus._resolved_mode() != "live":
            self._record_oracle_failure(
                oracle_name="A-PLUS",
                status="error",
                error_code="APLUS_NOT_LIVE",
                error_message=f"A-PLUS query did not complete in live mode (mode={self.aplus._resolved_mode()})",
                query_completed=result.query_completed,
                mode=result.mode or self.aplus._resolved_mode(),
                is_critical=True,
            )

        if result.total_claims_found > 0:
            for record in result.records:
                sev = RiskSeverity.CRITICAL if record.current_status == "open" and record.paid_amount > 100_000 else RiskSeverity.HIGH
                findings.append(
                    Finding(
                        title=f"A-PLUS: {record.claim_type.value.replace('_', ' ').title()} property claim ({record.current_status})",
                        description=f"Paid ${record.paid_amount:,.0f} on {record.date_of_loss} — {record.description[:120]}",
                        severity=sev,
                        category="external_oracle",
                        evidence=[
                            f"A-PLUS Claim: {record.claim_id}",
                            f"Status: {record.current_status}",
                            f"Type: {record.claim_type.value}",
                            f"Paid: ${record.paid_amount:,.0f}",
                        ],
                    )
                )

        if result.has_repeated_property_claims:
            findings.append(
                Finding(
                    title="A-PLUS: Repeated property claims pattern",
                    description=f"{result.total_claims_found} property claims on file — indicates potential habitational or maintenance issues",
                    severity=RiskSeverity.HIGH,
                    category="external_oracle",
                )
            )

        if result.has_arson_or_fraud_flag:
            findings.append(
                Finding(
                    title="A-PLUS: Arson or fraud flag on record",
                    description="Property loss database contains an arson or fraud indicator for this insured",
                    severity=RiskSeverity.CRITICAL,
                    category="external_oracle",
                )
            )

        if result.total_claims_found == 0:
            unverified = self.aplus._resolved_mode() != "live"
            if unverified:
                findings.append(
                    Finding(
                        title="A-PLUS: External verification unavailable",
                        description=(f"A-PLUS query for {insured_name} did not complete in live mode (mode={self.aplus._resolved_mode()})."),
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
                        evidence=[f"mode={self.aplus._resolved_mode()}"],
                    )
                )
            else:
                findings.append(
                    Finding(
                        title="A-PLUS: Clean property loss history",
                        description=f"No property claims found in A-PLUS database for {insured_name}",
                        severity=RiskSeverity.LOW,
                        category="external_oracle",
                    )
                )

        return findings

    def _query_ncci(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        insured_name = self.tools.get_named_insured(bundle)
        if not insured_name:
            return findings

        fein = ""
        if bundle.structured and bundle.structured.named_insured:
            fein = bundle.structured.named_insured.tax_id or ""

        result = self.ncci.query_by_fein(fein, insured_name)

        if result.error:
            self._record_oracle_failure(
                oracle_name="NCCI",
                status="error",
                error_code="NCCI_QUERY_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.ncci._resolved_mode(),
                is_critical=True,
            )
            findings.append(
                Finding(
                    title="NCCI query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

        for mod in result.experience_mods:
            band = mod.risk_band
            if band == "critical":
                findings.append(
                    Finding(
                        title=f"NCCI: Critical experience mod ({mod.mod_factor:.3f})",
                        description=(
                            f"Class {mod.class_code} ({mod.class_code_description}): "
                            f"mod {mod.mod_factor:.3f} — "
                            f"actual losses ${result.total_actual_losses:,.0f} "
                            f"vs expected ${result.total_expected_losses:,.0f}"
                        ),
                        severity=RiskSeverity.CRITICAL,
                        category="external_oracle",
                        field_path="oracles.ncci",
                        source_value=mod.mod_factor,
                        evidence=[
                            f"Mod factor: {mod.mod_factor}",
                            f"Class: {mod.class_code}",
                            f"Band: {band}",
                        ],
                    )
                )
            elif band == "high":
                findings.append(
                    Finding(
                        title=f"NCCI: High experience mod ({mod.mod_factor:.3f})",
                        description=f"Class {mod.class_code}: mod {mod.mod_factor:.3f} — debit mod indicates above-average loss experience",
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
                        field_path="oracles.ncci",
                        source_value=mod.mod_factor,
                    )
                )
            elif band == "moderate":
                findings.append(
                    Finding(
                        title=f"NCCI: Average experience mod ({mod.mod_factor:.3f})",
                        description=f"Class {mod.class_code}: mod {mod.mod_factor:.3f} — within normal range",
                        severity=RiskSeverity.LOW,
                        category="external_oracle",
                        source_value=mod.mod_factor,
                    )
                )
            else:
                findings.append(
                    Finding(
                        title=f"NCCI: Favorable experience mod ({mod.mod_factor:.3f})",
                        description=f"Class {mod.class_code}: mod {mod.mod_factor:.3f} — credit mod indicates below-average loss experience",
                        severity=RiskSeverity.LOW,
                        category="external_oracle",
                        source_value=mod.mod_factor,
                    )
                )

        worst = result.worst_mod
        if worst is not None:
            self.last_ncci_emod = float(worst.mod_factor)

        return findings

    def _model_catastrophe_risk(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        locations = self.tools.get_locations(bundle)
        if not locations:
            return findings

        loc_dicts = []
        for loc in locations:
            loc_dicts.append(
                {
                    "address": loc.address,
                    "city": loc.city,
                    "state": loc.state,
                    "zip_code": loc.zip_code,
                    "building_value": loc.building_value,
                    "contents_value": loc.contents_value,
                    "bi_value": loc.bi_value,
                }
            )

        cat_result = self.cat_model.model_submission(loc_dicts)
        if cat_result.error:
            self._record_oracle_failure(
                oracle_name="CAT",
                status="error",
                error_code="CAT_MODEL_FAILED",
                error_message=cat_result.error,
                query_completed=cat_result.query_completed,
                mode=cat_result.mode or self.cat_model._resolved_mode(),
                is_critical=True,
            )
            findings.append(
                Finding(
                    title="CAT model query failed",
                    description=cat_result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

        for exposure in cat_result.exposures:
            band = exposure.risk_band
            if band in ("critical", "high"):
                findings.append(
                    Finding(
                        title=f"CAT: {exposure.city}, {exposure.state} — {band.upper()} catastrophe risk",
                        description=f"Combined CAT score: {exposure.combined_cat_score:.0%} | "
                        f"Primary threat: {exposure.max_threat.title()} | "
                        f"PML 100yr: ${exposure.estimated_pml_100yr:,.0f} | "
                        f"AAL: ${exposure.estimated_aal:,.0f}/yr",
                        severity=RiskSeverity.HIGH if band == "high" else RiskSeverity.CRITICAL,
                        category="external_oracle",
                        field_path="oracles.cat_model",
                        evidence=[
                            f"Hurricane: {exposure.hurricane_risk_score:.0%}",
                            f"Earthquake: {exposure.earthquake_risk_score:.0%}",
                            f"Wildfire: {exposure.wildfire_risk_score:.0%}",
                            f"Flood: {exposure.flood_risk_score:.0%}",
                            f"Coastal: {exposure.in_coastal_zone}",
                            f"Wildfire zone: {exposure.in_wildfire_zone}",
                        ],
                    )
                )

        return findings

    def _query_bureau(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        insured_name, tax_id, _ = self._identity(bundle)
        if not insured_name or insured_name == bundle.bundle_id:
            return findings

        result = self.bureau.query_by_tax_id(tax_id, insured_name)
        if result.error:
            self._record_oracle_failure(
                oracle_name="Bureau",
                status="error",
                error_code="BUREAU_QUERY_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.bureau._resolved_mode(),
                is_critical=False,
            )
            findings.append(
                Finding(
                    title="Credit bureau query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

        band = result.risk_band
        if band == "critical":
            findings.append(
                Finding(
                    title=f"BUREAU: Critical credit profile ({result.paydex_score})",
                    description=(
                        f"Paydex {result.paydex_score} | financial strength {result.financial_strength_rating or 'NR'} | "
                        f"12-mo failure probability {result.failure_risk_score:.0%} | "
                        f"{result.number_of_derogatory_trades} derogatory trade(s)"
                        f"{' — BANKRUPTCY INDICATOR' if result.has_bankruptcy_indicator else ''}"
                    ),
                    severity=RiskSeverity.CRITICAL,
                    category="external_oracle",
                    field_path="oracles.bureau",
                    source_value=result.failure_risk_score,
                    evidence=[
                        f"Paydex: {result.paydex_score}",
                        f"Failure risk: {result.failure_risk_score:.0%}",
                        f"Derogatory trades: {result.number_of_derogatory_trades}",
                    ],
                )
            )
        elif band == "high":
            findings.append(
                Finding(
                    title=f"BUREAU: Elevated credit risk (Paydex {result.paydex_score})",
                    description=(f"Below-investment-grade trade credit profile; 12-mo failure probability {result.failure_risk_score:.0%}."),
                    severity=RiskSeverity.HIGH,
                    category="external_oracle",
                    field_path="oracles.bureau",
                    source_value=result.failure_risk_score,
                )
            )
        elif band == "moderate":
            findings.append(
                Finding(
                    title=f"BUREAU: Moderate credit profile (Paydex {result.paydex_score})",
                    description="Trade credit profile is workable but not top-tier; verify with financial statements.",
                    severity=RiskSeverity.LOW,
                    category="external_oracle",
                    field_path="oracles.bureau",
                    source_value=result.paydex_score,
                )
            )
        else:
            findings.append(
                Finding(
                    title=f"BUREAU: Strong credit profile (Paydex {result.paydex_score})",
                    description=f"Financial strength {result.financial_strength_rating or 'NR'}; failure probability {result.failure_risk_score:.0%}.",
                    severity=RiskSeverity.LOW,
                    category="external_oracle",
                    field_path="oracles.bureau",
                    source_value=result.paydex_score,
                )
            )

        if self.bureau._resolved_mode() != "live":
            findings.append(
                Finding(
                    title="BUREAU: External verification unavailable",
                    description=f"Credit bureau query did not complete in live mode (mode={self.bureau._resolved_mode()}).",
                    severity=RiskSeverity.HIGH,
                    category="external_oracle",
                    evidence=[f"mode={self.bureau._resolved_mode()}"],
                )
            )

        return findings

    def _query_public_records(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        insured_name, tax_id, address = self._identity(bundle)
        if not insured_name or insured_name == bundle.bundle_id:
            return findings

        result = self.public_records.query_by_entity(insured_name, tax_id, address)
        if result.error:
            self._record_oracle_failure(
                oracle_name="PublicRecords",
                status="error",
                error_code="PUBLIC_RECORDS_QUERY_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.public_records._resolved_mode(),
                is_critical=False,
            )
            findings.append(
                Finding(
                    title="Public records query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

        for rec in result.records:
            if rec.record_type == "bankruptcy":
                findings.append(
                    Finding(
                        title=f"PUBLIC RECORDS: Bankruptcy filing ({rec.jurisdiction})",
                        description=rec.description or f"Bankruptcy recorded in {rec.jurisdiction}",
                        severity=RiskSeverity.CRITICAL,
                        category="external_oracle",
                        field_path="oracles.public_records",
                        evidence=[f"Record: {rec.record_id}", f"Status: {rec.status}"],
                    )
                )
            elif rec.record_type == "judgment":
                sev = RiskSeverity.HIGH if rec.is_active or rec.amount >= 100_000 else RiskSeverity.MODERATE
                findings.append(
                    Finding(
                        title=f"PUBLIC RECORDS: {'Active' if rec.is_active else 'Satisfied'} judgment ({rec.jurisdiction})",
                        description=(f"${rec.amount:,.0f} — {rec.plaintiff or 'plaintiff'} vs {rec.defendant or insured_name}. {rec.description}"),
                        severity=sev,
                        category="external_oracle",
                        field_path="oracles.public_records",
                        source_value=rec.amount,
                        evidence=[f"Amount: ${rec.amount:,.0f}", f"Status: {rec.status}", f"Filed: {rec.filed_at}"],
                    )
                )
            elif rec.record_type == "lien":
                sev = RiskSeverity.HIGH if rec.is_active else RiskSeverity.MODERATE
                findings.append(
                    Finding(
                        title=f"PUBLIC RECORDS: {'Active' if rec.is_active else 'Released'} lien ({rec.jurisdiction})",
                        description=rec.description or f"${rec.amount:,.0f} lien in {rec.jurisdiction}",
                        severity=sev,
                        category="external_oracle",
                        field_path="oracles.public_records",
                        source_value=rec.amount,
                    )
                )
            elif rec.record_type == "ucc":
                findings.append(
                    Finding(
                        title=f"PUBLIC RECORDS: UCC financing statement ({rec.jurisdiction})",
                        description=rec.description or f"Security interest filed in {rec.jurisdiction}",
                        severity=RiskSeverity.MODERATE,
                        category="external_oracle",
                        field_path="oracles.public_records",
                        source_value=rec.amount,
                    )
                )

        if result.total_records_found == 0:
            unverified = self.public_records._resolved_mode() != "live"
            if unverified:
                findings.append(
                    Finding(
                        title="PUBLIC RECORDS: External verification unavailable",
                        description=f"Public-record query did not complete in live mode (mode={self.public_records._resolved_mode()}).",
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
                        evidence=[f"mode={self.public_records._resolved_mode()}"],
                    )
                )
            else:
                findings.append(
                    Finding(
                        title="PUBLIC RECORDS: Clean record",
                        description=f"No judgments, liens, UCC filings, or bankruptcy for {insured_name}",
                        severity=RiskSeverity.LOW,
                        category="external_oracle",
                    )
                )

        return findings

    def _query_osha(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        insured_name, tax_id, _ = self._identity(bundle)
        if not insured_name or insured_name == bundle.bundle_id:
            return findings

        naics = ""
        if bundle.structured and bundle.structured.risk_profile:
            naics = bundle.structured.risk_profile.naics_code or ""

        result = self.osha.query_by_entity(insured_name, tax_id, naics)
        if result.error:
            self._record_oracle_failure(
                oracle_name="OSHA",
                status="error",
                error_code="OSHA_QUERY_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.osha._resolved_mode(),
                is_critical=False,
            )
            findings.append(
                Finding(
                    title="OSHA query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

        for v in result.violations:
            sev = RiskSeverity.CRITICAL if v.violation_type == "willful" else RiskSeverity.HIGH if v.violation_type == "repeat" else RiskSeverity.MODERATE
            findings.append(
                Finding(
                    title=f"OSHA: {v.violation_type.upper()} violation ({v.violation_type})",
                    description=(f"${v.penalty:,.0f} penalty — {v.description}. {'Open inspection' if not v.closed else 'Closed inspection'}."),
                    severity=sev,
                    category="external_oracle",
                    field_path="oracles.osha",
                    source_value=v.penalty,
                    evidence=[
                        f"Violation: {v.violation_id}",
                        f"Inspection: {v.inspection_number}",
                        f"Type: {v.violation_type}",
                        f"Penalty: ${v.penalty:,.0f}",
                        f"Status: {'open' if not v.closed else 'closed'}",
                    ],
                )
            )

        if result.total_violations == 0:
            unverified = self.osha._resolved_mode() != "live"
            if unverified:
                findings.append(
                    Finding(
                        title="OSHA: External verification unavailable",
                        description=f"OSHA inspection query did not complete in live mode (mode={self.osha._resolved_mode()}).",
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
                        evidence=[f"mode={self.osha._resolved_mode()}"],
                    )
                )
            else:
                findings.append(
                    Finding(
                        title="OSHA: Clean safety record",
                        description=f"No violations found for {insured_name}",
                        severity=RiskSeverity.LOW,
                        category="external_oracle",
                    )
                )

        return findings

    def _query_rating_agency(self, bundle: SubmissionBundle) -> list[Finding]:
        findings: list[Finding] = []
        insured_name, tax_id, _ = self._identity(bundle)
        if not insured_name or insured_name == bundle.bundle_id:
            return findings

        result = self.rating_agency.query_by_entity(insured_name, tax_id)
        if result.error:
            self._record_oracle_failure(
                oracle_name="RatingAgency",
                status="error",
                error_code="RATING_AGENCY_QUERY_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.rating_agency._resolved_mode(),
                is_critical=False,
            )
            findings.append(
                Finding(
                    title="Rating agency query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

        band = result.risk_band
        if result.not_rated:
            findings.append(
                Finding(
                    title="RATING: Issuer not rated",
                    description=f"No public issuer rating found for {insured_name} via {result.agency}.",
                    severity=RiskSeverity.LOW,
                    category="external_oracle",
                    field_path="oracles.rating_agency",
                )
            )
        elif band == "critical":
            findings.append(
                Finding(
                    title=f"RATING: Distressed credit rating ({result.issuer_rating})",
                    description=f"Issuer rated {result.issuer_rating} with {result.outlook} outlook{', ' + result.watch if result.watch else ''}.",
                    severity=RiskSeverity.CRITICAL,
                    category="external_oracle",
                    field_path="oracles.rating_agency",
                    source_value=result.issuer_rating,
                )
            )
        elif band == "high":
            findings.append(
                Finding(
                    title=f"RATING: Sub-investment-grade credit rating ({result.issuer_rating})",
                    description=(f"Speculative-grade issuer rating {result.issuer_rating} ({result.outlook} outlook){', ' + result.watch if result.watch else ''}."),
                    severity=RiskSeverity.HIGH,
                    category="external_oracle",
                    field_path="oracles.rating_agency",
                    source_value=result.issuer_rating,
                )
            )
        else:
            findings.append(
                Finding(
                    title=f"RATING: Investment-grade credit rating ({result.issuer_rating})",
                    description=f"Issuer rated {result.issuer_rating} with {result.outlook} outlook.",
                    severity=RiskSeverity.LOW,
                    category="external_oracle",
                    field_path="oracles.rating_agency",
                    source_value=result.issuer_rating,
                )
            )

        if self.rating_agency._resolved_mode() != "live":
            findings.append(
                Finding(
                    title="RATING: External verification unavailable",
                    description=f"Rating-agency query did not complete in live mode (mode={self.rating_agency._resolved_mode()}).",
                    severity=RiskSeverity.HIGH,
                    category="external_oracle",
                    evidence=[f"mode={self.rating_agency._resolved_mode()}"],
                )
            )

        return findings

    def _should_query_mvr(self, bundle: SubmissionBundle, line: str) -> bool:
        key = (line or "").lower()
        if any(tok in key for tok in ("auto", "fleet", "vehicle", "motor")):
            return True
        from insureflow.underwriting.personal_lines import _blob

        blob = _blob(bundle)
        return bool(extract_drivers(blob) or re.search(r"\b(?:mvr|fleet|power unit|commercial auto|driver)\b", blob, re.I))

    def _query_mvr(self, bundle: SubmissionBundle) -> list[Finding]:
        from insureflow.underwriting.personal_lines import _blob

        blob = _blob(bundle)
        drivers = extract_drivers(blob)
        if not drivers:
            insured = self.tools.get_named_insured(bundle)
            if insured:
                drivers = [insured]
        findings: list[Finding] = []
        if not drivers:
            findings.append(
                Finding(
                    title="MVR: no drivers identified",
                    description="Commercial auto requires named drivers / MVRs — none found on the package.",
                    severity=RiskSeverity.CRITICAL,
                    category="external_oracle",
                    field_path="oracles.mvr",
                )
            )
            self.last_mvr_cleared = False
            return findings

        any_major = False
        synthetic = False
        for name in drivers[:8]:
            result = self.mvr.query_driver(name)
            synthetic = synthetic or result.synthetic or result.mode != "live"
            if result.error:
                self._record_oracle_failure(
                    oracle_name="MVR",
                    status="error",
                    error_code="MVR_QUERY_FAILED",
                    error_message=result.error,
                    query_completed=result.query_completed,
                    mode=result.mode or self.mvr._resolved_mode(),
                    is_critical=False,
                )
                findings.append(
                    Finding(
                        title=f"MVR query failed ({name})",
                        description=result.error,
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
                        field_path="oracles.mvr",
                    )
                )
                any_major = True
                continue
            if result.synthetic:
                findings.append(
                    Finding(
                        title=f"MVR unverified ({name})",
                        description="Simulated MVR is not a clean driving record. Connect a live MVR vendor or upload MVRs.",
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
                        field_path="oracles.mvr",
                    )
                )
                any_major = True
                continue
            if result.has_major or result.total_points >= 6:
                any_major = True
                findings.append(
                    Finding(
                        title=f"MVR adverse ({name})",
                        description=f"{result.total_points} points, {result.accidents} accident(s), {result.suspensions} suspension(s)",
                        severity=RiskSeverity.CRITICAL if result.has_major else RiskSeverity.HIGH,
                        category="external_oracle",
                        field_path="oracles.mvr",
                    )
                )
            else:
                findings.append(
                    Finding(
                        title=f"MVR clear ({name})",
                        description="No major violations on live MVR.",
                        severity=RiskSeverity.LOW,
                        category="external_oracle",
                        field_path="oracles.mvr",
                    )
                )
        self.last_mvr_cleared = not any_major and not synthetic
        return findings

    def _should_query_telematics(self, bundle: SubmissionBundle, line: str) -> bool:
        key = (line or "").lower()
        if any(tok in key for tok in ("auto", "fleet", "vehicle", "motor", "ubi")):
            return True
        from insureflow.underwriting.personal_lines import _blob

        blob = _blob(bundle)
        return bool(extract_vin(blob) or re.search(r"\b(?:telematics|annual mileage|odometer|vin)\b", blob, re.I))

    def _query_telematics(self, bundle: SubmissionBundle) -> list[Finding]:
        from insureflow.underwriting.personal_lines import _blob

        blob = _blob(bundle)
        vin = extract_vin(blob)
        stated = None
        match = re.search(r"annual\s+mileage\s*[:=]\s*([\d,]+)", blob, re.I)
        if match:
            try:
                stated = float(match.group(1).replace(",", ""))
            except ValueError:
                stated = None
        findings: list[Finding] = []
        if not vin:
            findings.append(
                Finding(
                    title="Telematics: no VIN on the file",
                    description="Connected-car audit needs a VIN. None found — cannot compare stated mileage to a feed.",
                    severity=RiskSeverity.HIGH,
                    category="telematics",
                    field_path="oracles.telematics",
                )
            )
            return findings
        result = self.telematics.query_vehicle(vin, stated_mileage=stated)
        if result.error:
            self._record_oracle_failure(
                oracle_name="Telematics",
                status="error",
                error_code="TELEMATICS_QUERY_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.telematics._resolved_mode(),
                is_critical=False,
            )
            findings.append(
                Finding(
                    title="Telematics query failed",
                    description=result.error,
                    severity=RiskSeverity.HIGH,
                    category="telematics",
                    field_path="oracles.telematics",
                )
            )
            return findings
        if result.synthetic:
            findings.append(
                Finding(
                    title="Telematics unverified",
                    description="Simulated telematics is not a clean driving score. Connect a live connected-car feed or we will not pretend the mileage matches.",
                    severity=RiskSeverity.HIGH,
                    category="telematics",
                    field_path="oracles.telematics",
                    evidence=[f"vin={vin}", f"mode={result.mode}"],
                )
            )
            return findings
        if stated is not None and result.annual_mileage is not None:
            delta = abs(result.annual_mileage - stated) / max(stated, 1.0)
            if delta >= 0.25:
                findings.append(
                    Finding(
                        title="Stated mileage does not match the car",
                        description=f"Application says {stated:,.0f} miles/year; connected-car feed says {result.annual_mileage:,.0f} ({delta:.0%} apart).",
                        severity=RiskSeverity.CRITICAL if delta >= 0.5 else RiskSeverity.HIGH,
                        category="telematics",
                        field_path="oracles.telematics",
                    )
                )
        if result.hard_brake_per_1k is not None and result.hard_brake_per_1k >= 8:
            findings.append(
                Finding(
                    title="Hard-brake rate elevated",
                    description=f"{result.hard_brake_per_1k:.1f} hard brakes per 1,000 miles on the live feed.",
                    severity=RiskSeverity.HIGH,
                    category="telematics",
                    field_path="oracles.telematics",
                )
            )
        if not findings:
            findings.append(
                Finding(
                    title="Telematics consistent",
                    description="Live connected-car feed does not contradict the application.",
                    severity=RiskSeverity.LOW,
                    category="telematics",
                    field_path="oracles.telematics",
                )
            )
        return findings

    def _should_query_cyber(self, bundle: SubmissionBundle, line: str) -> bool:
        key = (line or "").lower()
        if "cyber" in key:
            return True
        from insureflow.underwriting.personal_lines import _blob

        blob = _blob(bundle)
        return bool(re.search(r"\b(?:cyber|mfa|multi-factor|vulnerability scan)\b", blob, re.I))

    def _query_cyber_scan(self, bundle: SubmissionBundle) -> list[Finding]:
        from insureflow.underwriting.personal_lines import _blob

        blob = _blob(bundle)
        domain = extract_domain(blob)
        claims_mfa = bool(re.search(r"\b(?:mfa|multi-factor|2fa)\b.{0,40}\b(?:yes|enabled|in place)\b", blob, re.I))
        findings: list[Finding] = []
        if not domain:
            findings.append(
                Finding(
                    title="Cyber scan: no domain on the file",
                    description="An outside vulnerability scan needs a domain. None found.",
                    severity=RiskSeverity.HIGH,
                    category="cyber_scan",
                    field_path="oracles.cyber_scan",
                )
            )
            return findings
        result = self.cyber_scan.query_domain(domain)
        if result.error:
            self._record_oracle_failure(
                oracle_name="CyberScan",
                status="error",
                error_code="CYBER_SCAN_FAILED",
                error_message=result.error,
                query_completed=result.query_completed,
                mode=result.mode or self.cyber_scan._resolved_mode(),
                is_critical=False,
            )
            findings.append(
                Finding(
                    title="Cyber scan query failed",
                    description=result.error,
                    severity=RiskSeverity.HIGH,
                    category="cyber_scan",
                    field_path="oracles.cyber_scan",
                )
            )
            return findings
        if result.synthetic:
            findings.append(
                Finding(
                    title="Cyber scan unverified",
                    description="Simulated scan is not a clean security posture. Connect a live scanner or we will not rubber-stamp the questionnaire.",
                    severity=RiskSeverity.HIGH,
                    category="cyber_scan",
                    field_path="oracles.cyber_scan",
                    evidence=[f"domain={domain}", f"mode={result.mode}"],
                )
            )
            return findings
        if result.critical_findings and result.critical_findings >= 1:
            findings.append(
                Finding(
                    title="Live scan found critical exposures",
                    description=f"{result.critical_findings} critical finding(s) on {domain}.",
                    severity=RiskSeverity.CRITICAL,
                    category="cyber_scan",
                    field_path="oracles.cyber_scan",
                )
            )
        if claims_mfa and result.mfa_observed is False:
            findings.append(
                Finding(
                    title="Questionnaire says MFA; the scan does not see it",
                    description=f"{domain} claimed multi-factor authentication; the live scan did not observe it.",
                    severity=RiskSeverity.HIGH,
                    category="cyber_scan",
                    field_path="oracles.cyber_scan",
                )
            )
        if not findings:
            findings.append(
                Finding(
                    title="Cyber scan consistent",
                    description="Live vulnerability scan does not contradict the questionnaire.",
                    severity=RiskSeverity.LOW,
                    category="cyber_scan",
                    field_path="oracles.cyber_scan",
                )
            )
        return findings
