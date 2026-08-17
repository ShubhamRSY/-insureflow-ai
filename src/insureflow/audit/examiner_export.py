"""DOI/NAIC examination export — structured regulator-ready packages.

Produces formatted exports for state Department of Insurance examinations,
NAIC Market Regulation Handbook workpapers, and rate-filing justification
packages.  Every statement is linked to its verbatim source citation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from insureflow.models.provenance import ProvenanceRecord
from insureflow.provenance.chain import StatementProvenanceChain


class FieldCitationReport(BaseModel):
    """Per-field source citation report for examiner consumption."""

    field_name: str = ""
    extracted_value: str = ""
    source_document: str = ""
    source_page: Optional[int] = None
    verbatim_quote: str = ""
    bbox: Optional[list[float]] = None
    character_offsets: Optional[list[int]] = None
    confidence: float = 0.0
    trust_level: str = ""
    verification_status: str = ""
    extraction_method: str = ""
    has_contradictions: bool = False
    contradicting_sources: list[str] = Field(default_factory=list)
    reconciled_value: str = ""


class RateFilingJustification(BaseModel):
    """Rate filing justification with source citations for each component."""

    rate_component: str = ""
    amount: float = 0.0
    source_document: str = ""
    source_page: Optional[int] = None
    verbatim_quote: str = ""
    confidence: float = 0.0
    regulatory_basis: str = ""  # adequate | not_excessive | not_discriminatory


class DecisionDefensePackage(BaseModel):
    """Decision defense package for adverse-action or examination response."""

    decision: str = ""
    decision_date: str = ""
    overall_confidence: float = 0.0
    field_citations: list[FieldCitationReport] = Field(default_factory=list)
    findings: list[dict[str, str]] = Field(default_factory=list)
    routing_tier: str = ""
    abstention_occurred: bool = False
    abstention_reasons: list[str] = Field(default_factory=list)
    guardian_flags: list[str] = Field(default_factory=list)


class NAICWorkpaper(BaseModel):
    """NAIC examination workpaper entry."""

    workpaper_id: str = ""
    examination_area: str = ""
    finding: str = ""
    source_citations: list[FieldCitationReport] = Field(default_factory=list)
    risk_rating: str = "low"
    examiner_notes: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


class ExaminerExportEngine:
    """Produces regulator-ready export packages with full source citations."""

    def __init__(self) -> None:
        self._chain = StatementProvenanceChain()

    def export_field_citation_report(
        self,
        provenance: ProvenanceRecord,
        reconciliation: Any = None,
    ) -> list[FieldCitationReport]:
        """For every field, show where it came from with verbatim citations."""
        self._chain.build_chain(provenance)
        reports: list[FieldCitationReport] = []

        reconciled_values: dict[str, str] = {}
        if reconciliation and hasattr(reconciliation, "field_reconciliation"):
            for fp, data in reconciliation.field_reconciliation.items():
                if isinstance(data, dict):
                    reconciled_values[fp] = str(data.get("resolved_value", ""))

        for field_path in self._chain.all_fields():
            citations = self._chain.get_citations_for_field(field_path)
            for cit in citations:
                char_offsets = None
                if cit.citation and cit.citation.start_char is not None and cit.citation.end_char is not None:
                    char_offsets = [cit.citation.start_char, cit.citation.end_char]

                reports.append(
                    FieldCitationReport(
                        field_name=field_path,
                        extracted_value=cit.extracted_value,
                        source_document=cit.source_document,
                        source_page=cit.source_page,
                        verbatim_quote=cit.citation.source_text if cit.citation else "",
                        bbox=cit.citation.bbox if cit.citation else None,
                        character_offsets=char_offsets,
                        confidence=cit.confidence,
                        trust_level=cit.trust_level.value,
                        verification_status="verified" if cit.reconciled else "unverified",
                        extraction_method=cit.extraction_method,
                        has_contradictions=bool(cit.contradicting_citations),
                        contradicting_sources=[
                            c.document_id for c in cit.contradicting_citations if c.document_id
                        ],
                        reconciled_value=reconciled_values.get(field_path, ""),
                    )
                )

        return reports

    def export_decision_defense_package(
        self,
        provenance: ProvenanceRecord,
        decision: str = "",
        confidence: float = 0.0,
        findings: list[Any] | None = None,
        routing_decision: Any = None,
        abstention_verdict: Any = None,
        reconciliation: Any = None,
    ) -> DecisionDefensePackage:
        """Build a defense package explaining a decision with per-finding citations."""
        field_citations = self.export_field_citation_report(provenance, reconciliation)

        findings_dicts: list[dict[str, str]] = []
        if findings:
            for f in findings:
                findings_dicts.append(
                    {
                        "title": getattr(f, "title", ""),
                        "description": getattr(f, "description", ""),
                        "severity": getattr(f, "severity", ""),
                        "field_path": getattr(f, "field_path", ""),
                    }
                )

        abstained = False
        abstention_reasons: list[str] = []
        if abstention_verdict and hasattr(abstention_verdict, "abstain"):
            abstained = abstention_verdict.abstain
            if hasattr(abstention_verdict, "reasons"):
                abstention_reasons = [str(r) for r in abstention_verdict.reasons]

        routing_tier = ""
        if routing_decision and hasattr(routing_decision, "tier"):
            routing_tier = str(routing_decision.tier.value) if hasattr(routing_decision.tier, "value") else str(routing_decision.tier)

        guardian_flags: list[str] = []
        if findings:
            guardian_flags = [
                getattr(f, "description", "")
                for f in findings
                if getattr(f, "severity", "") in ("error", "critical")
            ]

        return DecisionDefensePackage(
            decision=decision,
            decision_date=datetime.now(tz=timezone.utc).isoformat(),
            overall_confidence=confidence,
            field_citations=field_citations,
            findings=findings_dicts,
            routing_tier=routing_tier,
            abstention_occurred=abstained,
            abstention_reasons=abstention_reasons,
            guardian_flags=guardian_flags,
        )

    def export_naic_workpapers(
        self,
        provenance: ProvenanceRecord,
        reconciliation: Any = None,
    ) -> list[NAICWorkpaper]:
        """Export NAIC examination format workpapers."""
        field_citations = self.export_field_citation_report(provenance, reconciliation)

        workpapers: list[NAICWorkpaper] = []
        wp_id = 1

        # Group citations by field category
        categories: dict[str, list[FieldCitationReport]] = {}
        for fc in field_citations:
            category = fc.field_name.split(".")[0] if "." in fc.field_name else "general"
            if category not in categories:
                categories[category] = []
            categories[category].append(fc)

        for category, citations in categories.items():
            low_conf = [c for c in citations if c.confidence < 0.7]
            contradicted = [c for c in citations if c.has_contradictions]
            risk = "high" if contradicted else ("medium" if low_conf else "low")

            finding = f"{len(citations)} fields in '{category}' category"
            if contradicted:
                finding += f" — {len(contradicted)} have contradicting sources"
            if low_conf:
                finding += f" — {len(low_conf)} below confidence threshold"

            workpapers.append(
                NAICWorkpaper(
                    workpaper_id=f"WP-{wp_id:03d}",
                    examination_area=category,
                    finding=finding,
                    source_citations=citations,
                    risk_rating=risk,
                )
            )
            wp_id += 1

        return workpapers

    def export_rate_filing_justification(
        self,
        rate_components: list[dict[str, Any]],
        provenance: ProvenanceRecord | None = None,
    ) -> list[RateFilingJustification]:
        """Export rate filing justification with source citations per component."""
        self._chain.build_chain(provenance) if provenance else None

        results: list[RateFilingJustification] = []
        for comp in rate_components:
            component_name = comp.get("name", "")
            amount = comp.get("amount", 0.0)
            source = comp.get("source", "")
            regulatory_basis = comp.get("regulatory_basis", "")

            # Try to find matching citations
            verbatim = ""
            page = None
            conf = 0.0
            if provenance:
                citations = self._chain.get_citations_for_statement(str(amount))
                if citations:
                    best = max(citations, key=lambda c: c.confidence)
                    verbatim = best.citation.source_text if best.citation else ""
                    page = best.source_page
                    conf = best.confidence

            results.append(
                RateFilingJustification(
                    rate_component=component_name,
                    amount=amount,
                    source_document=source,
                    source_page=page,
                    verbatim_quote=verbatim,
                    confidence=conf,
                    regulatory_basis=regulatory_basis,
                )
            )

        return results
