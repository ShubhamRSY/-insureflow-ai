"""Citation accuracy verification — checks that claimed citations are grounded.

Verifies that the claimed page/bbox/verbatim text actually exists in the source
document.  This closes the gap between citation_gate (which checks presence) and
the need for accuracy verification.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from insureflow.models.provenance import ProvenanceNode, ProvenanceRecord, VerbatimCitation


class CitationVerificationResult(BaseModel):
    """Result of verifying a single citation against source text."""

    node_id: str = ""
    field_path: str = ""
    verified: bool = False
    text_found: bool = False
    page_match: bool = False
    bbox_in_bounds: bool = False
    char_offsets_valid: bool = False
    confidence: float = 0.0
    issues: list[str] = Field(default_factory=list)


class CitationVerificationReport(BaseModel):
    """Aggregated citation verification results for a provenance record."""

    total_citations: int = 0
    verified_count: int = 0
    failed_count: int = 0
    pass_rate: float = 0.0
    results: list[CitationVerificationResult] = Field(default_factory=list)
    fields_with_failures: list[str] = Field(default_factory=list)


def verify_text_found(citation: VerbatimCitation, raw_text: str) -> tuple[bool, float]:
    """Verify that the claimed source_text appears in the raw document text."""
    if not citation.source_text:
        return False, 0.0
    if citation.source_text in raw_text:
        return True, 0.95
    if citation.source_text.lower() in raw_text.lower():
        return True, 0.8
    return False, 0.0


def verify_page_number(citation: VerbatimCitation, page_count: int | None) -> bool:
    """Verify that the claimed page number is within the document."""
    if citation.page_number is None:
        return True  # no page claimed, nothing to verify
    if page_count is None:
        return True  # unknown document length, can't disprove
    return 1 <= citation.page_number <= page_count


def verify_bbox_in_bounds(citation: VerbatimCitation) -> bool:
    """Verify that the bbox is a valid normalized box."""
    if citation.bbox is None:
        return True  # no bbox claimed
    if len(citation.bbox) != 4:
        return False
    x0, y0, x1, y1 = citation.bbox
    if not (0.0 <= x0 <= 1.0 and 0.0 <= y0 <= 1.0 and 0.0 <= x1 <= 1.0 and 0.0 <= y1 <= 1.0):
        return False
    return x0 <= x1 and y0 <= y1


def verify_char_offsets(citation: VerbatimCitation, raw_text: str) -> tuple[bool, str]:
    """Verify that the claimed character offsets match the source text."""
    if citation.start_char is None or citation.end_char is None:
        return True, ""
    if citation.start_char < 0 or citation.end_char > len(raw_text):
        return False, f"offsets [{citation.start_char},{citation.end_char}] exceed text length {len(raw_text)}"
    if citation.start_char >= citation.end_char:
        return False, f"start_char {citation.start_char} >= end_char {citation.end_char}"
    if citation.source_text:
        actual = raw_text[citation.start_char : citation.end_char]
        if citation.source_text[:50] not in actual:
            return False, "source_text does not match text at claimed offsets"
    return True, ""


def verify_single_citation(
    node: ProvenanceNode,
    raw_text: str,
    page_count: int | None = None,
) -> CitationVerificationResult:
    """Verify all aspects of a single citation."""
    result = CitationVerificationResult(
        node_id=node.node_id,
        field_path=node.field_path,
    )

    if node.citation is None:
        result.issues.append("no citation present")
        return result

    citation = node.citation
    text_ok, text_conf = verify_text_found(citation, raw_text)
    page_ok = verify_page_number(citation, page_count)
    bbox_ok = verify_bbox_in_bounds(citation)
    offsets_ok, offsets_msg = verify_char_offsets(citation, raw_text)

    result.text_found = text_ok
    result.page_match = page_ok
    result.bbox_in_bounds = bbox_ok
    result.char_offsets_valid = offsets_ok

    if not text_ok:
        result.issues.append("verbatim text not found in source document")
    if not page_ok:
        result.issues.append(f"page {citation.page_number} out of range (1-{page_count})")
    if not bbox_ok:
        result.issues.append("bbox is out of bounds or malformed")
    if not offsets_ok:
        result.issues.append(offsets_msg)

    result.verified = text_ok and page_ok and bbox_ok and offsets_ok
    result.confidence = text_conf if text_ok else 0.0
    return result


def verify_all_citations(
    record: ProvenanceRecord,
    raw_text_map: dict[str, str],
    page_count_map: dict[str, int] | None = None,
) -> CitationVerificationReport:
    """Verify every citation in a ProvenanceRecord against source text."""
    page_count_map = page_count_map or {}
    report = CitationVerificationReport()
    failed_fields: set[str] = set()

    for field_path, nodes in record.nodes.items():
        for node in nodes:
            if node.citation is None:
                continue
            report.total_citations += 1
            raw_text = raw_text_map.get(
                node.source.source_id,
                raw_text_map.get(node.source.source_name, ""),
            )
            page_count = page_count_map.get(node.source.source_id)
            result = verify_single_citation(node, raw_text, page_count)
            report.results.append(result)
            if result.verified:
                report.verified_count += 1
            else:
                report.failed_count += 1
                failed_fields.add(field_path)

    report.pass_rate = (
        report.verified_count / report.total_citations if report.total_citations > 0 else 0.0
    )
    report.fields_with_failures = sorted(failed_fields)
    return report
