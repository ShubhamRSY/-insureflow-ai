from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.oracles.aplus_client import APlusClient
from insureflow.oracles.bureau_client import CreditBureauClient
from insureflow.oracles.cat_model_client import CatastropheModelClient
from insureflow.oracles.clue_client import CLUEClient
from insureflow.oracles.ncci_client import NCCIClient
from insureflow.oracles.osha_client import OSHAClient
from insureflow.oracles.public_records_client import PublicRecordsClient
from insureflow.oracles.rating_agency_client import CreditRatingAgencyClient


class OracleAgent(BaseAgent):
    """Agent that queries external data sources (CLUE, A-PLUS, NCCI, CAT models,
    credit bureau, public records, OSHA, rating agencies) to catch hidden claims
    history, property losses, workers comp experience, catastrophe exposure,
    financial distress, litigation, workplace-safety, and credit risk."""

    agent_type = AgentType.ORACLE_AGENT
    agent_name = "OracleAgent"

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

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        if not self._live_oracles_ok():
            return
        for findings in (
            self._query_clue(bundle),
            self._query_aplus(bundle),
            self._query_ncci(bundle),
            self._model_catastrophe_risk(bundle),
            self._query_bureau(bundle),
            self._query_public_records(bundle),
            self._query_osha(bundle),
            self._query_rating_agency(bundle),
        ):
            for f in findings:
                self._add_finding(f)

    def _live_oracles_ok(self) -> bool:
        """Desk+ fail closed: never return simulated 'clean history' at paid prices."""
        from insureflow.billing.plan import current_plan

        plan = current_plan()
        if not plan.require_live_oracles:
            return True
        simulated: list[str] = []
        for name, client in (
            ("CLUE", self.clue),
            ("A-PLUS", self.aplus),
            ("NCCI", self.ncci),
            ("CAT", self.cat_model),
            ("Bureau", self.bureau),
            ("PublicRecords", self.public_records),
            ("OSHA", self.osha),
            ("RatingAgency", self.rating_agency),
        ):
            mode = ""
            if hasattr(client, "_resolved_mode"):
                try:
                    mode = str(client._resolved_mode() or "")
                except Exception:
                    mode = "unknown"
            if mode != "live":
                simulated.append(f"{name}:{mode or 'simulated'}")
        if not simulated:
            return True
        self._add_finding(
            Finding(
                title="Live oracles required for this plan",
                description=(
                    f"{plan.plan_id.title()} does not allow simulated oracle feeds while charging Desk+ prices. "
                    "Point CLUE / NCCI / A+ / CAT at vendor sandboxes (not integrations.rytera.ai) or stay on Pilot. "
                    f"Not live: {', '.join(simulated)}."
                ),
                severity=RiskSeverity.CRITICAL,
                category="oracle_posture",
                evidence=simulated,
            )
        )
        return False

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
            findings.append(
                Finding(
                    title="CLUE query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

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
            unverified = (
                bool(getattr(result, "synthetic", False))
                or getattr(result, "mode", "")
                in {
                    "simulated",
                    "gateway_synthetic",
                }
                or self.clue._resolved_mode() != "live"
            )
            if unverified:
                findings.append(
                    Finding(
                        title="CLUE: External verification unavailable (synthetic/simulated)",
                        description=(f"CLUE response for {insured_name} is synthetic or simulated — do not treat as a verified clean loss history. Configure live LexisNexis credentials."),
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
                        evidence=["synthetic=true" if getattr(result, "synthetic", False) else f"mode={self.clue._resolved_mode()}"],
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
            findings.append(
                Finding(
                    title="A-PLUS query failed",
                    description=result.error,
                    severity=RiskSeverity.MODERATE,
                    category="external_oracle",
                )
            )
            return findings

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
            unverified = self.aplus._resolved_mode() != "live" or bool(getattr(result, "synthetic", False))
            if unverified:
                findings.append(
                    Finding(
                        title="A-PLUS: External verification unavailable (synthetic/simulated)",
                        description=(f"A-PLUS response for {insured_name} is synthetic or simulated — do not treat as a verified clean property history."),
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
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

        if result.synthetic or self.bureau._resolved_mode() != "live":
            findings.append(
                Finding(
                    title="BUREAU: External verification unavailable (synthetic/simulated)",
                    description="Credit bureau response is synthetic or simulated — do not treat as a verified clean credit profile.",
                    severity=RiskSeverity.HIGH,
                    category="external_oracle",
                    evidence=[f"mode={result.mode or self.bureau._resolved_mode()}"],
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
            unverified = self.public_records._resolved_mode() != "live" or bool(result.synthetic)
            if unverified:
                findings.append(
                    Finding(
                        title="PUBLIC RECORDS: External verification unavailable (synthetic/simulated)",
                        description="Public-record search is synthetic or simulated — do not treat as a verified clean record.",
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
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
            unverified = self.osha._resolved_mode() != "live" or bool(result.synthetic)
            if unverified:
                findings.append(
                    Finding(
                        title="OSHA: External verification unavailable (synthetic/simulated)",
                        description="OSHA inspection search is synthetic or simulated — do not treat as a verified clean safety record.",
                        severity=RiskSeverity.HIGH,
                        category="external_oracle",
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

        if result.synthetic or self.rating_agency._resolved_mode() != "live":
            findings.append(
                Finding(
                    title="RATING: External verification unavailable (synthetic/simulated)",
                    description="Rating-agency response is synthetic or simulated — do not treat as a verified rating.",
                    severity=RiskSeverity.HIGH,
                    category="external_oracle",
                    evidence=[f"mode={result.mode or self.rating_agency._resolved_mode()}"],
                )
            )

        return findings
