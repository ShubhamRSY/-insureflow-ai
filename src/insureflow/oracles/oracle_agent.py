from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.oracles.aplus_client import APlusClient
from insureflow.oracles.cat_model_client import CatastropheModelClient
from insureflow.oracles.clue_client import CLUEClient
from insureflow.oracles.ncci_client import NCCIClient


class OracleAgent(BaseAgent):
    """Agent that queries external data sources (CLUE, A-PLUS, NCCI, CAT models)
    to catch hidden claims history, property losses, workers comp experience, and catastrophe exposure."""

    agent_type = AgentType.ORACLE_AGENT
    agent_name = "OracleAgent"

    def __init__(
        self,
        clue_client: CLUEClient | None = None,
        aplus_client: APlusClient | None = None,
        ncci_client: NCCIClient | None = None,
        cat_model: CatastropheModelClient | None = None,
    ) -> None:
        super().__init__()
        self.clue = clue_client or CLUEClient()
        self.aplus = aplus_client or APlusClient()
        self.ncci = ncci_client or NCCIClient()
        self.cat_model = cat_model or CatastropheModelClient()

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        clues = self._query_clue(bundle)
        for f in clues:
            self._add_finding(f)

        aplus_findings = self._query_aplus(bundle)
        for f in aplus_findings:
            self._add_finding(f)

        ncci_findings = self._query_ncci(bundle)
        for f in ncci_findings:
            self._add_finding(f)

        cat_findings = self._model_catastrophe_risk(bundle)
        for f in cat_findings:
            self._add_finding(f)

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
                sev = (
                    RiskSeverity.CRITICAL
                    if record.current_status == "open" and record.paid_amount > 50_000
                    else RiskSeverity.HIGH
                )
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
                sev = (
                    RiskSeverity.CRITICAL
                    if record.current_status == "open" and record.paid_amount > 100_000
                    else RiskSeverity.HIGH
                )
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
                        description=f"Class {mod.class_code} ({mod.class_code_description}): mod {mod.mod_factor:.3f} — actual losses ${result.total_actual_losses:,.0f} vs expected ${result.total_expected_losses:,.0f}",
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
