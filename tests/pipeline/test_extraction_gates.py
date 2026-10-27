from __future__ import annotations

import llm_extract


DOCS = {"application.md": "Named Insured: Example LLC\nPremises: 100 Main St\nEffective Date: 2026-01-01\n"}


def field(**kw):
    base = {"field_id": "premises_address", "value": "100 Main St", "source": "application.md", "quote": "Premises: 100 Main St", "confidence": 0.95}
    base.update(kw)
    return llm_extract.accept_field(base, DOCS)


def test_a_cited_value_is_kept():
    row = field()
    assert row["value"] == "100 Main St"
    assert row["needs_review"] is False
    assert row["start"] is not None and row["end"] is not None


def test_a_quote_not_in_the_document_is_dropped():
    row = field(quote="Premises: 9 Elsewhere Rd")
    assert row["value"] is None
    assert row["reason"] == llm_extract.REASON_QUOTE.format("application.md")


def test_a_value_not_in_its_quote_is_dropped():
    row = field(value="200 Other St")
    assert row["value"] is None
    assert row["reason"] == llm_extract.REASON_VALUE


def test_a_low_confidence_typed_value_is_dropped():
    row = field(confidence=0.4)
    assert row["value"] is None
    assert "under" in row["reason"]


def test_a_date_is_stored_as_iso():
    row = field(field_id="effective_date", value="1/1/26", quote="Effective Date: 2026-01-01")
    assert row["value"] == "2026-01-01"


def test_a_scan_number_is_kept_for_review():
    docs = {"scan.png": "Total insured value 1,000,000"}
    row = llm_extract.accept_field(
        {"field_id": "tiv_building", "value": "$1,000,000", "source": "scan.png", "quote": "Total insured value 1,000,000", "confidence": 0.9},
        docs,
        {"scan.png": 0.9},
    )
    assert row["value"] == "$1,000,000"
    assert row["needs_review"] is True
    assert row["reason"] == llm_extract.REASON_SCAN


def test_a_scan_date_with_matching_digits_is_kept_for_review_with_the_p067_reason():
    docs = {"scan.png": "Loss run valued through 2025-03-31"}
    row = llm_extract.accept_field(
        {"field_id": "loss_run_valued_through", "value": "2025-03-31", "source": "scan.png", "quote": "Loss run valued through 2025-03-31", "confidence": 0.9},
        docs,
        {"scan.png": 0.6},
    )
    assert row["value"] == "2025-03-31"
    assert row["needs_review"] is True
    assert row["reason"] == llm_extract.REASON_SCAN_DATE_REVIEW


def test_a_no_known_loss_loss_run_is_not_a_date():
    docs = {"loss-runs.md": "No known losses as of 3/31/25"}
    row = llm_extract.accept_field(
        {"field_id": "loss_run_valued_through", "value": "2025-03-31", "source": "loss-runs.md", "quote": "No known losses as of 3/31/25", "confidence": 0.95},
        docs,
    )
    assert row["value"] is None
