"""Verbatim citation extraction — bridges spatial data to provenance.

For every extracted field, extracts the exact sentence/paragraph from the source
document that supports the value, and produces a VerbatimCitation linked to the
ProvenanceNode.  This closes the gap between ExtractedField's spatial metadata
(page/bbox/char) and the provenance audit trail.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from insureflow.models.provenance import ProvenanceNode, ProvenanceRecord, VerbatimCitation


class QuoteResult(BaseModel):
    """A verbatim quote extracted around an extracted value."""

    text: str = ""
    page_number: Optional[int] = None
    bbox: Optional[list[float]] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    confidence: float = 0.0


def _sentence_window(text: str, value: str, window_chars: int = 200) -> str:
    """Return the sentence-level context around the first occurrence of ``value``."""
    idx = text.find(value)
    if idx == -1:
        value_lower = value.lower()
        idx = text.lower().find(value_lower)
        if idx == -1:
            return ""
    # Expand window generously, then trim to sentence boundaries in full text.
    start = max(0, idx - window_chars)
    end = min(len(text), idx + len(value) + window_chars)
    # Walk backwards from idx to find sentence start
    sent_start = start
    for i in range(idx, start, -1):
        if text[i] in ".!?\n" and i < idx:
            sent_start = i + 1
            break
    # Walk forwards from end of value to find sentence end
    val_end = idx + len(value)
    sent_end = end
    for i in range(val_end, min(end, len(text))):
        if text[i] in ".!?\n":
            sent_end = i + 1
            break
    snippet = text[sent_start:sent_end].strip()
    return snippet if snippet else text[start:end].strip()


def extract_source_quote(
    raw_text: str,
    value: str,
    bbox: list[float] | None = None,
    page: int | None = None,
    window_chars: int = 200,
) -> QuoteResult:
    """Find the verbatim text around the extracted value in the source document."""
    quote_text = _sentence_window(raw_text, value, window_chars)
    if not quote_text:
        return QuoteResult(text="", page_number=page, bbox=bbox, confidence=0.0)

    # Compute confidence based on exact match vs fuzzy
    exact = value in raw_text
    confidence = 0.95 if exact else 0.6

    # Try to compute char offsets
    idx = raw_text.find(quote_text)
    start_char = idx if idx >= 0 else None
    end_char = (idx + len(quote_text)) if idx >= 0 else None

    return QuoteResult(
        text=quote_text,
        page_number=page,
        bbox=bbox,
        start_char=start_char,
        end_char=end_char,
        confidence=confidence,
    )


def quote_for_field(
    field_name: str,
    value: Any,
    raw_text: str,
    page_number: int | None = None,
    bbox: list[float] | None = None,
    source_ref: str = "",
) -> QuoteResult:
    """Build a QuoteResult for a single extracted field value."""
    str_value = str(value) if value else ""
    if not str_value or not raw_text:
        return QuoteResult(page_number=page_number, bbox=bbox)
    return extract_source_quote(raw_text, str_value, bbox, page_number)


def enrich_citations(
    record: ProvenanceRecord,
    raw_text_map: dict[str, str],
    *,
    source_ref_map: dict[str, str] | None = None,
) -> ProvenanceRecord:
    """Enrich every ProvenanceNode's citation with verbatim text from raw sources.

    ``raw_text_map`` maps document_id (or source_name) to raw document text.
    Nodes whose citation is already populated with source_text are skipped.
    """
    source_ref_map = source_ref_map or {}
    for field_path, nodes in record.nodes.items():
        for node in nodes:
            if node.citation and node.citation.source_text:
                continue
            raw_text = _resolve_raw_text(node, raw_text_map, source_ref_map)
            if not raw_text:
                continue
            value_str = str(node.value) if node.value else ""
            if not value_str:
                continue
            quote = extract_source_quote(
                raw_text,
                value_str,
                bbox=node.citation.bbox if node.citation else None,
                page=node.citation.page_number if node.citation else None,
            )
            if node.citation is None:
                node.citation = VerbatimCitation(
                    document_id=node.source.source_id,
                    document_type=node.source.source_name,
                    page_number=quote.page_number,
                    bbox=quote.bbox,
                    start_char=quote.start_char,
                    end_char=quote.end_char,
                    source_text=quote.text,
                    confidence=quote.confidence,
                )
            else:
                node.citation.source_text = quote.text
                node.citation.start_char = quote.start_char
                node.citation.end_char = quote.end_char
                node.citation.confidence = max(node.citation.confidence, quote.confidence)
    return record


def _resolve_raw_text(
    node: ProvenanceNode,
    raw_text_map: dict[str, str],
    source_ref_map: dict[str, str],
) -> str:
    """Find the raw text for a node from available maps."""
    doc_id = node.source.source_id
    if doc_id in raw_text_map:
        return raw_text_map[doc_id]
    source_name = node.source.source_name
    if source_name in raw_text_map:
        return raw_text_map[source_name]
    ref = source_ref_map.get(doc_id, "")
    if ref and ref in raw_text_map:
        return raw_text_map[ref]
    return ""
