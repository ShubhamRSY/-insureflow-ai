"""Commercial Insurance hub catalog + LOB detection."""

from __future__ import annotations

from insureflow.insurance.commercial_lobs import (
    BASE_PACKET,
    COMMERCIAL_CATEGORIES,
    COMMERCIAL_LINES,
    commercial_hub_payload,
    commercial_taxonomy_tree,
    flatten_line_documents,
    get_commercial_line,
    list_commercial_categories,
    list_commercial_lines,
)
from insureflow.insurance.package_checklist import CATALOGS, detect_lob, package_checklist


def test_full_commercial_taxonomy_shape():
    assert len(COMMERCIAL_CATEGORIES) == 7
    assert len(COMMERCIAL_LINES) >= 40
    cats = {c["id"] for c in COMMERCIAL_CATEGORIES}
    assert cats == {
        "property",
        "liability",
        "workforce",
        "auto",
        "financial",
        "specialty",
        "package",
    }
    for line in COMMERCIAL_LINES:
        assert line["category_id"] in cats
        assert len(line["documents"]) >= 6, line["id"]
        assert line["uw_focus"]
        assert line["insurance_line"]
        assert line["checklist_lob"]
        for cov in line.get("coverages") or []:
            assert isinstance(cov, dict), line["id"]
            assert cov.get("id")
            assert cov.get("name")
            assert isinstance(cov.get("documents"), list)
            assert len(cov["documents"]) >= 1, f"{line['id']}.{cov.get('id')}"


def test_live_lines_still_present():
    live_slugs = {ln["slug"] for ln in list_commercial_lines(status="live")}
    assert {
        "property-bi",
        "do",
        "workers-comp",
        "trade-credit",
        "eo",
        "key-person",
        "general-liability",
        "umbrella",
        "bop",
    } <= live_slugs


def test_hub_payload_has_taxonomy_and_stats():
    hub = commercial_hub_payload()
    assert hub["segment"] == "business_commercial"
    assert len(hub["base_packet"]) == len(BASE_PACKET)
    assert BASE_PACKET[0].startswith("Completed ACORD")
    assert len(hub["uw_responsibilities"]) == 6
    assert hub["stats"]["category_count"] == 7
    assert hub["stats"]["product_count"] == len(COMMERCIAL_LINES)
    assert len(hub["taxonomy"]) == 7
    assert len(hub["lines"]) == len(COMMERCIAL_LINES)
    assert len(hub["categories"]) == 7
    sample = hub["lines"][0]
    assert "all_documents" in sample
    assert isinstance(sample["coverages"], list)


def test_taxonomy_tree_nests_coverages():
    tree = commercial_taxonomy_tree()
    property_cat = next(c for c in tree if c["id"] == "property")
    assert property_cat["product_count"] >= 8
    crime = next(p for p in property_cat["products"] if p["id"] == "crime")
    assert len(crime["coverages"]) >= 4
    assert any("Employee Dishonesty" in c["name"] for c in crime["coverages"])
    for cov in crime["coverages"]:
        assert cov["id"]
        assert isinstance(cov["documents"], list)
        assert len(cov["documents"]) >= 1


def test_flatten_line_documents_includes_coverage_docs():
    prop = get_commercial_line("property_bi")
    assert prop is not None
    flat = flatten_line_documents(prop)
    assert len(flat) >= len(prop["documents"])
    assert "Statement of Values (SOV) — per-location address, construction, occupancy, protection, exposure (COPE)" in flat
    assert "Structure replacement cost appraisal" in flat
    assert "Inventory/asset list with values" in flat
    # de-duplicated
    assert len(flat) == len(set(flat))
    assert prop["all_documents"] == flat


def test_get_line_by_slug_and_id():
    by_slug = get_commercial_line("workers-comp")
    assert by_slug is not None
    assert by_slug["checklist_lob"] == "workers_comp"
    assert len(by_slug["documents"]) >= 6
    assert "all_documents" in by_slug

    by_id = get_commercial_line("property_bi")
    assert by_id is not None
    assert by_id["slug"] == "property-bi"
    assert isinstance(by_id["coverages"][0], dict)
    assert by_id["coverages"][0]["id"] == "building_structure"

    cyber = get_commercial_line("cyber_liability")
    assert cyber is not None
    assert cyber["category_id"] == "liability"
    assert cyber["status"] == "catalog"

    assert get_commercial_line("not-a-line") is None


def test_category_filters():
    auto_lines = list_commercial_lines(category_id="auto")
    assert len(auto_lines) >= 5
    assert all(l["category_id"] == "auto" for l in auto_lines)
    cats = list_commercial_categories()
    auto_cat = next(c for c in cats if c["id"] == "auto")
    assert auto_cat["product_count"] == len(auto_lines)


def test_each_checklist_lob_has_catalog():
    for line in COMMERCIAL_LINES:
        lob = line["checklist_lob"]
        assert lob in CATALOGS, f"missing catalog for {line['id']} → {lob}"
        flat = flatten_line_documents(line)
        result = package_checklist([], lob=lob)
        assert result["completeness_pct"] == 0.0
        assert len(result["missing"]) == len(flat), f"{line['id']} → {lob}"
        assert len(result["missing"]) >= 5


def test_detect_lob_commercial_keywords():
    assert detect_lob("ACORD 130 workers compensation payroll", "") == "workers_comp"
    assert detect_lob("trade credit accounts receivable aging", "") == "trade_credit"
    assert detect_lob("errors and omissions professional liability", "") == "eo"
    assert detect_lob("key person insurance buy-sell", "") == "key_person"
    assert detect_lob("", "workers_comp") == "workers_comp"
    assert detect_lob("cyber liability ransomware security questionnaire", "") == "cyber"
    assert detect_lob("builders risk course of construction", "") == "builders_risk"
    assert detect_lob("employment practices epli wrongful termination", "") == "epli"
    assert detect_lob("surety bond performance bond", "") == "surety"
    assert detect_lob("", "cyber_liability") == "cyber"


def test_package_checklist_empty_template():
    for lob in ("property", "do", "workers_comp", "trade_credit", "eo", "key_person", "cyber", "bop"):
        result = package_checklist([], lob=lob)
        assert result["present"] == []
        assert len(result["missing"]) >= 5
        assert result["completeness_pct"] == 0.0
