"""Life Insurance hub catalog + LOB detection."""

from __future__ import annotations

from insureflow.insurance.commercial_lobs import flatten_coverage_documents, flatten_line_documents
from insureflow.insurance.life_lobs import (
    LIFE_BASE_PACKET,
    LIFE_CATEGORIES,
    LIFE_LINES,
    get_life_coverage,
    get_life_line,
    life_hub_payload,
    life_taxonomy_tree,
    list_life_categories,
    list_life_lines,
    resolve_life_checklist_lob,
)
from insureflow.insurance.package_checklist import CATALOGS, detect_lob, package_checklist


def test_full_life_taxonomy_shape():
    assert len(LIFE_CATEGORIES) == 7
    assert len(LIFE_LINES) >= 35
    cats = {c["id"] for c in LIFE_CATEGORIES}
    assert cats == {
        "term",
        "whole",
        "universal",
        "endowment",
        "ulip",
        "money_back",
        "annuity",
    }
    for line in LIFE_LINES:
        assert line["category_id"] in cats
        assert len(line["documents"]) >= len(LIFE_BASE_PACKET), line["id"]
        assert len(line["additional_documents"]) <= len(line["documents"]), line["id"]
        assert line["uw_focus"]
        assert line["insurance_line"] == "life"
        assert line["checklist_lob"]
        for cov in line.get("coverages") or []:
            assert isinstance(cov, dict), line["id"]
            assert cov.get("id")
            assert cov.get("name")
            assert isinstance(cov.get("documents"), list)
            assert len(cov["documents"]) >= 1, f"{line['id']}.{cov.get('id')}"


def test_life_live_vs_catalog_split():
    live = [ln for ln in LIFE_LINES if ln.get("status") == "live"]
    catalog = [ln for ln in LIFE_LINES if ln.get("status") == "catalog"]
    assert {ln["id"] for ln in live} >= {"level_term", "mortgage_life", "rop_term", "group_term_life"}
    assert {ln["id"] for ln in catalog} >= {"traditional_whole_life", "indexed_universal_life", "variable_universal_life", "immediate_annuity"}
    hub = life_hub_payload()
    assert hub["stats"]["live_count"] == len(live)
    assert hub["stats"]["catalog_count"] == len(catalog)
    assert hub["stats"]["product_count"] == len(LIFE_LINES)


def test_live_lines_still_present():
    live_slugs = {ln["slug"] for ln in list_life_lines(status="live")}
    assert {
        "level-term",
        "mortgage-life",
        "credit-life",
        "return-of-premium-term",
        "group-term-life",
    } <= live_slugs
    catalog_slugs = {ln["slug"] for ln in list_life_lines(status="catalog")}
    assert {
        "traditional-whole-life",
        "indexed-universal-life",
        "variable-universal-life",
        "immediate-annuity",
    } <= catalog_slugs


def test_hub_payload_has_taxonomy_and_stats():
    hub = life_hub_payload()
    assert hub["segment"] == "personal_life"
    assert hub["title"] == "Life Insurance"
    assert len(hub["base_packet"]) == len(LIFE_BASE_PACKET)
    assert LIFE_BASE_PACKET[0].startswith("Government-issued photo ID")
    assert LIFE_BASE_PACKET[1] == "Social Security Number (SSN)"
    assert len(hub["uw_responsibilities"]) >= 6
    assert hub["stats"]["category_count"] == 7
    assert hub["stats"]["product_count"] == len(LIFE_LINES)
    assert len(hub["taxonomy"]) == 7
    assert len(hub["lines"]) == len(LIFE_LINES)
    assert len(hub["categories"]) == 7
    sample = hub["lines"][0]
    assert "all_documents" in sample
    assert isinstance(sample["coverages"], list)


def test_taxonomy_tree_nests_coverages():
    tree = life_taxonomy_tree()
    universal_cat = next(c for c in tree if c["id"] == "universal")
    assert universal_cat["product_count"] >= 4
    iul = next(p for p in universal_cat["products"] if p["id"] == "indexed_universal_life")
    assert len(iul["coverages"]) >= 2
    for cov in iul["coverages"]:
        assert cov["id"]
        assert isinstance(cov["documents"], list)
        assert len(cov["documents"]) >= 1


def test_flatten_line_documents_includes_coverage_docs():
    term = get_life_line("level_term")
    assert term is not None
    flat = flatten_line_documents(term)
    assert len(flat) >= len(term["documents"])
    assert "Completed life insurance application" in flat
    assert len(flat) == len(set(flat))
    assert term["all_documents"] == flat


def test_flatten_coverage_documents_excludes_sibling_coverages():
    term = get_life_line("level_term")
    assert term is not None
    ten = flatten_coverage_documents(term, "level_term_10")
    thirty = flatten_coverage_documents(term, "level_term_30")
    full = flatten_line_documents(term)
    assert "Paramedical exam report (required above ~$100K–$250K)" in thirty
    assert "Paramedical exam report (required above ~$100K–$250K)" not in ten
    assert len(ten) < len(full)
    assert len(thirty) <= len(full)


def test_resolve_life_coverage_id_to_product():
    assert resolve_life_checklist_lob("level_term_10") == "level_term"
    assert resolve_life_checklist_lob("10-Year Level Term") == "level_term"
    line, cov = get_life_coverage("level_term", "level_term_10")
    assert line is not None and cov is not None
    assert cov["id"] == "level_term_10"
    line_only, cov_only = get_life_coverage(None, "level_term_20")
    assert line_only is not None and cov_only is not None
    assert line_only["checklist_lob"] == "level_term"
    assert cov_only["id"] == "level_term_20"


def test_package_checklist_scopes_to_life_coverage():
    ten = package_checklist([], lob="level_term", coverage_id="level_term_10")
    thirty = package_checklist([], lob="level_term", coverage_id="level_term_30")
    assert ten["lob"] == "level_term"
    assert ten["coverage_id"] == "level_term_10"
    assert thirty["coverage_id"] == "level_term_30"
    assert any("Paramedical" in m for m in thirty["missing"])
    assert not any("Paramedical" in m for m in ten["missing"])


def test_get_line_by_slug_and_id():
    by_slug = get_life_line("traditional-whole-life")
    assert by_slug is not None
    assert by_slug["checklist_lob"] == "traditional_whole_life"
    assert len(by_slug["documents"]) >= len(LIFE_BASE_PACKET)
    assert "all_documents" in by_slug

    by_id = get_life_line("indexed_universal_life")
    assert by_id is not None
    assert by_id["slug"] == "indexed-universal-life"
    assert isinstance(by_id["coverages"][0], dict)
    assert by_id["coverages"][0]["id"] == "indexed_account"

    by_checklist_lob = get_life_line("mortgage_life")
    assert by_checklist_lob is not None
    assert by_checklist_lob["category_id"] == "term"

    assert get_life_line("not-a-line") is None


def test_base_packet_is_included_in_every_line():
    base_set = set(LIFE_BASE_PACKET)
    for line in LIFE_LINES:
        assert base_set <= set(line["documents"]), line["id"]
        assert base_set.isdisjoint(set(line["additional_documents"])), line["id"]


def test_category_filters():
    term_lines = list_life_lines(category_id="term")
    assert len(term_lines) >= 5
    assert all(line["category_id"] == "term" for line in term_lines)
    cats = list_life_categories()
    term_cat = next(c for c in cats if c["id"] == "term")
    assert term_cat["product_count"] == len(term_lines)


def test_each_checklist_lob_has_catalog():
    for line in LIFE_LINES:
        lob = line["checklist_lob"]
        assert lob in CATALOGS, f"missing catalog for {line['id']} → {lob}"
        flat = flatten_line_documents(line)
        result = package_checklist([], lob=lob)
        assert result["completeness_pct"] == 0.0
        assert len(result["missing"]) == len(flat), f"{line['id']} → {lob}"
        assert len(result["missing"]) >= 5


def test_detect_lob_life_keywords():
    assert detect_lob("term life insurance face amount beneficiary designation paramedical", "") == "life"
    assert detect_lob("whole life application insured", "") == "life"
    assert detect_lob("", "traditional_whole_life") == "traditional_whole_life"
    assert detect_lob("", "life") == "life"


def test_life_underwriting_path_present():
    from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
    from insureflow.underwriting.life_medical import underwrite_life

    bundle = SubmissionBundle(
        bundle_id="life-test",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                document_type="life_application",
                raw_text="Term life application. Age 45. Nonsmoker. BMI 26.",
            )
        ],
    )
    decision = underwrite_life(bundle)
    assert decision.decision.value in {"accept", "conditional_accept", "refer", "decline"}
    assert decision.underwriting_class
