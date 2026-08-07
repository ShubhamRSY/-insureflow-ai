"""Commercial Insurance hub catalog + LOB detection."""

from __future__ import annotations

from insureflow.insurance.commercial_lobs import (
    BASE_PACKET,
    COMMERCIAL_LINES,
    commercial_hub_payload,
    get_commercial_line,
    list_commercial_lines,
)
from insureflow.insurance.package_checklist import detect_lob, package_checklist


def test_six_commercial_lines():
    lines = list_commercial_lines()
    assert len(lines) == 6
    slugs = {ln["slug"] for ln in lines}
    assert slugs == {"property-bi", "do", "workers-comp", "trade-credit", "eo", "key-person"}


def test_hub_payload_has_base_packet_and_uw():
    hub = commercial_hub_payload()
    assert hub["segment"] == "business_commercial"
    assert len(hub["base_packet"]) == len(BASE_PACKET)
    assert len(hub["uw_responsibilities"]) == 6
    assert len(hub["lines"]) == 6


def test_get_line_by_slug_and_id():
    by_slug = get_commercial_line("workers-comp")
    assert by_slug is not None
    assert by_slug["checklist_lob"] == "workers_comp"
    assert len(by_slug["documents"]) >= 8

    by_id = get_commercial_line("property_bi")
    assert by_id is not None
    assert by_id["slug"] == "property-bi"

    assert get_commercial_line("not-a-line") is None


def test_each_line_has_document_pack():
    for line in COMMERCIAL_LINES:
        assert len(line["documents"]) >= 8, line["id"]
        assert line["uw_focus"]
        assert line["insurance_line"]


def test_detect_lob_commercial_keywords():
    assert detect_lob("ACORD 130 workers compensation payroll", "") == "workers_comp"
    assert detect_lob("trade credit accounts receivable aging", "") == "trade_credit"
    assert detect_lob("errors and omissions professional liability", "") == "eo"
    assert detect_lob("key person insurance buy-sell", "") == "key_person"
    assert detect_lob("", "workers_comp") == "workers_comp"


def test_package_checklist_empty_template():
    for lob in ("property", "do", "workers_comp", "trade_credit", "eo", "key_person"):
        result = package_checklist([], lob=lob)
        assert result["present"] == []
        assert len(result["missing"]) >= 5
        assert result["completeness_pct"] == 0.0
