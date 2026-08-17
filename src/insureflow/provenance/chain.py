"""Statement-level provenance chain — links every decision statement to its source.

For every extracted or decision statement, maintains a complete verbatim source
trail:  statement → extracted value → source field → source document → page →
character position → verbatim text.  This is the core of "show where every
statement came from."
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from insureflow.models.provenance import (
    ProvenanceRecord,
    TrustLevel,
    VerbatimCitation,
    VerificationStatus,
)


class StatementCitation(BaseModel):
    """A single statement linked to its verbatim source citation."""

    citation_id: str = Field(default_factory=lambda: f"cit-{uuid4().hex[:8]}")
    statement_text: str = ""
    extracted_value: str = ""
    field_path: str = ""
    citation: Optional[VerbatimCitation] = None
    trust_level: TrustLevel = TrustLevel.UNVERIFIED
    confidence: float = 0.0
    reconciled: bool = False
    contradicting_citations: list[VerbatimCitation] = Field(default_factory=list)
    source_document: str = ""
    source_page: Optional[int] = None
    extraction_method: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class ExaminerReadyCitation(BaseModel):
    """A citation formatted for regulatory examiner consumption."""

    field_name: str = ""
    extracted_value: str = ""
    source_document: str = ""
    source_page: Optional[int] = None
    verbatim_quote: str = ""
    bbox: Optional[list[float]] = None
    character_offset_start: Optional[int] = None
    character_offset_end: Optional[int] = None
    confidence: float = 0.0
    trust_level: str = ""
    verification_status: str = ""
    extraction_method: str = ""
    has_contradictions: bool = False
    contradicting_sources: list[str] = Field(default_factory=list)


class StatementProvenanceChain:
    """Builds and queries statement-level provenance chains."""

    def __init__(self) -> None:
        self._citations: dict[str, list[StatementCitation]] = {}

    def build_chain(
        self,
        provenance: ProvenanceRecord,
        decisions: dict[str, str] | None = None,
        reconciliation: Any = None,
    ) -> dict[str, list[StatementCitation]]:
        """Build complete provenance chain from a ProvenanceRecord."""
        self._citations = {}

        for field_path, nodes in provenance.nodes.items():
            for node in nodes:
                value_str = str(node.value) if node.value else ""
                statement = decisions.get(field_path, value_str) if decisions else value_str

                citation = StatementCitation(
                    statement_text=statement,
                    extracted_value=value_str,
                    field_path=field_path,
                    citation=node.citation,
                    trust_level=node.source.trust_level,
                    confidence=node.confidence,
                    reconciled=node.verification_status == VerificationStatus.VERIFIED,
                    source_document=node.source.source_name,
                    source_page=node.citation.page_number if node.citation else None,
                    extraction_method=node.citation.extraction_method if node.citation else "",
                )

                if field_path not in self._citations:
                    self._citations[field_path] = []
                self._citations[field_path].append(citation)

        # Attach contradicting citations from provenance discrepancies
        self._attach_contradictions(provenance)

        return dict(self._citations)

    def get_citations_for_field(self, field_path: str) -> list[StatementCitation]:
        """Return all citations for a given field path."""
        return list(self._citations.get(field_path, []))

    def get_citations_for_statement(self, statement_text: str) -> list[StatementCitation]:
        """Return citations matching a statement text (substring match)."""
        results: list[StatementCitation] = []
        for citations in self._citations.values():
            for cit in citations:
                if statement_text.lower() in cit.statement_text.lower():
                    results.append(cit)
        return results

    def export_for_examiner(self, field_path: str | None = None) -> list[ExaminerReadyCitation]:
        """Export citations in examiner-ready format."""
        output: list[ExaminerReadyCitation] = []
        target = {field_path: self._citations.get(field_path, [])} if field_path else self._citations

        for fp, citations in target.items():
            for cit in citations:
                output.append(
                    ExaminerReadyCitation(
                        field_name=fp,
                        extracted_value=cit.extracted_value,
                        source_document=cit.source_document,
                        source_page=cit.source_page,
                        verbatim_quote=cit.citation.source_text if cit.citation else "",
                        bbox=cit.citation.bbox if cit.citation else None,
                        character_offset_start=cit.citation.start_char if cit.citation else None,
                        character_offset_end=cit.citation.end_char if cit.citation else None,
                        confidence=cit.confidence,
                        trust_level=cit.trust_level.value,
                        verification_status="verified" if cit.reconciled else "unverified",
                        extraction_method=cit.extraction_method,
                        has_contradictions=bool(cit.contradicting_citations),
                        contradicting_sources=[
                            c.document_id for c in cit.contradicting_citations if c.document_id
                        ],
                    )
                )
        return output

    def all_fields(self) -> list[str]:
        """Return all field paths in the chain."""
        return list(self._citations.keys())

    def total_citations(self) -> int:
        """Return total number of citations across all fields."""
        return sum(len(cits) for cits in self._citations.values())

    def fields_with_contradictions(self) -> list[str]:
        """Return field paths that have contradicting citations."""
        results: list[str] = []
        for fp, citations in self._citations.items():
            for cit in citations:
                if cit.contradicting_citations:
                    results.append(fp)
                    break
        return results

    def _attach_contradictions(self, provenance: ProvenanceRecord) -> None:
        """Find fields with CONTRADICTED nodes and attach them as contradictions."""
        for field_path, nodes in provenance.nodes.items():
            if field_path not in self._citations:
                continue
            contradicted = [
                n for n in nodes if n.verification_status == VerificationStatus.CONTRADICTED
            ]
            if not contradicted:
                continue
            for cit in self._citations[field_path]:
                for bad in contradicted:
                    if bad.citation and bad.node_id != cit.citation_id:
                        cit.contradicting_citations.append(bad.citation)
