"""General / Non-Life hub catalog + LOB detection."""

from __future__ import annotations

from typing import Any

from insureflow.insurance.commercial_lobs import flatten_line_documents
from insureflow.insurance.general_lobs import (
    GENERAL_CATEGORIES,
    GENERAL_LINES,
    general_hub_payload,
    general_taxonomy_tree,
    get_general_coverage,
    get_general_line,
    list_general_categories,
    list_general_lines,
    resolve_general_checklist_lob,
)
from insureflow.insurance.package_checklist import CATALOGS, detect_lob, package_checklist
from insureflow.rating.models import InsuranceLine
from insureflow.rating.personal.general_rating import rate_general
from insureflow.underwriting.general_product import LIVE_GENERAL_PRODUCT_IDS, is_filed_general_product


def _gi_line(line_id: str) -> dict[str, Any]:
    row = get_general_line(line_id)
    assert row is not None
    return row


EXPECTED_CATS = {
    "motor",
    "home",
    "travel",
    "marine",
    "fire",
    "liability",
    "cyber",
    "crop",
    "animal",
    "event",
    "title",
    "mortgage_gi",
    "provider",
}

EXPECTED_IDS = {
    "car_tp",
    "car_comprehensive",
    "tw_tp",
    "tw_comprehensive",
    "cv_tp",
    "cv_comprehensive",
    "home_structure",
    "home_contents",
    "home_comprehensive",
    "travel_domestic",
    "travel_international",
    "marine_cargo",
    "marine_hull",
    "fire_residential",
    "fire_commercial",
    "professional_indemnity_gi",
    "public_liability_gi",
    "product_liability_gi",
    "cyber_data_breach",
    "cyber_ransomware",
    "crop_yield",
    "crop_weather",
    "livestock_cattle",
    "pet_insurance",
    "wedding_insurance",
    "concert_event_insurance",
    "title_insurance_gi",
    "mortgage_insurance_gi",
    "insurer_psu",
    "insurer_private",
    "reinsurance_treaty",
}


def test_full_general_taxonomy_shape():
    assert len(GENERAL_CATEGORIES) == 13
    assert len(GENERAL_LINES) == 31
    assert {c["id"] for c in GENERAL_CATEGORIES} == EXPECTED_CATS
    assert {ln["id"] for ln in GENERAL_LINES} == EXPECTED_IDS
    for line in GENERAL_LINES:
        assert line["category_id"] in EXPECTED_CATS
        assert len(line["documents"]) >= 4, line["id"]
        assert line["uw_focus"]
        assert line["insurance_line"] == "general"
        assert line["checklist_lob"]
        assert line["status"] == "catalog"
        for cov in line.get("coverages") or []:
            assert cov.get("id")
            assert cov.get("name")
            assert isinstance(cov.get("documents"), list)
            assert len(cov["documents"]) >= 1, f"{line['id']}.{cov.get('id')}"


def test_all_catalog_until_filed():
    assert LIVE_GENERAL_PRODUCT_IDS == frozenset()
    assert not is_filed_general_product("car_tp")
    assert not is_filed_general_product("reinsurance_treaty")
    live = [ln for ln in GENERAL_LINES if ln.get("status") == "live"]
    assert live == []
    hub = general_hub_payload()
    assert hub["stats"]["live_count"] == 0
    assert hub["stats"]["catalog_count"] == 31
    assert hub["stats"]["product_count"] == 31


def test_hub_payload_has_taxonomy_and_stats():
    hub = general_hub_payload()
    assert hub["segment"] == "general_non_life"
    assert hub["title"] == "General / Non-Life Insurance"
    assert hub["base_packet"] == []
    assert len(hub["uw_responsibilities"]) >= 5
    assert hub["stats"]["category_count"] == 13
    assert len(hub["taxonomy"]) == 13
    assert len(hub["lines"]) == 31
    sample = hub["lines"][0]
    assert "all_documents" in sample
    assert isinstance(sample["coverages"], list)


def test_no_universal_kyc_forced_on_b2b_leaves():
    cargo = _gi_line("marine_cargo")
    hull = _gi_line("marine_hull")
    re = _gi_line("reinsurance_treaty")
    crop = _gi_line("crop_yield")
    assert cargo["base_packet"] == []
    assert hull["base_packet"] == []
    assert re["base_packet"] == []
    assert crop["base_packet"] == []
    assert any("bill of lading" in d.lower() or "airway" in d.lower() for d in cargo["documents"])
    assert any("vessel" in d.lower() or "seaworthiness" in d.lower() or "classification" in d.lower() for d in hull["documents"])
    assert any("treaty" in d.lower() or "facultative" in d.lower() for d in re["documents"])
    assert not any("passport-size" in d.lower() for d in re["documents"])


def test_home_contents_does_not_require_deed():
    structure = _gi_line("home_structure")
    contents = _gi_line("home_contents")
    assert any("sale deed" in d.lower() or "ownership" in d.lower() for d in structure["documents"])
    assert not any("sale deed" in d.lower() or "registry" in d.lower() for d in contents["documents"])
    assert any("insured items" in d.lower() or "jewelry" in d.lower() for d in contents["documents"])


def test_travel_domestic_vs_international_docs():
    domestic = _gi_line("travel_domestic")
    intl = _gi_line("travel_international")
    assert not any("passport" in d.lower() for d in domestic["documents"])
    assert any("passport" in d.lower() for d in intl["documents"])
    assert any("visa" in d.lower() for d in intl["documents"])


def test_cv_requires_fitness_permit_puc_car_tp_does_not():
    car = _gi_line("car_tp")
    cv = _gi_line("cv_tp")
    assert any("fitness" in d.lower() for d in cv["documents"])
    assert any("permit" in d.lower() for d in cv["documents"])
    assert any("puc" in d.lower() or "pollution" in d.lower() for d in cv["documents"])
    assert not any("fitness" in d.lower() for d in car["documents"])
    assert not any("permit" in d.lower() for d in car["documents"])


def test_taxonomy_tree_nests_motor_coverages():
    tree = general_taxonomy_tree()
    motor = next(c for c in tree if c["id"] == "motor")
    car_comp = next(p for p in motor["products"] if p["id"] == "car_comprehensive")
    cov_ids = {c["id"] for c in car_comp["coverages"]}
    assert {"car_comp_new", "car_comp_used"} <= cov_ids
    new_cov = next(c for c in car_comp["coverages"] if c["id"] == "car_comp_new")
    used_cov = next(c for c in car_comp["coverages"] if c["id"] == "car_comp_used")
    assert any("invoice" in d.lower() for d in new_cov["documents"])
    assert any("inspection" in d.lower() for d in used_cov["documents"])
    assert not any("inspection" in d.lower() for d in new_cov["documents"])


def test_resolve_coverage_id_to_product():
    assert resolve_general_checklist_lob("car_comp_new") == "car_comprehensive"
    assert resolve_general_checklist_lob("travel_intl_std") == "travel_international"
    line, cov = get_general_coverage("car_comprehensive", "car_comp_used")
    assert line is not None and cov is not None
    assert cov["id"] == "car_comp_used"
    line_only, cov_only = get_general_coverage(None, "travel_domestic_std")
    assert line_only is not None and cov_only is not None
    assert line_only["checklist_lob"] == "travel_domestic"


def test_package_checklist_scopes_to_general_coverage():
    new = package_checklist([], lob="car_comprehensive", coverage_id="car_comp_new")
    used = package_checklist([], lob="car_comprehensive", coverage_id="car_comp_used")
    assert new["lob"] == "car_comprehensive"
    assert new["coverage_id"] == "car_comp_new"
    assert used["coverage_id"] == "car_comp_used"
    assert any("invoice" in m.lower() for m in new["missing"])
    assert any("inspection" in m.lower() for m in used["missing"])


def test_get_line_by_slug_and_id():
    by_slug = get_general_line("car-tp")
    assert by_slug is not None
    assert by_slug["checklist_lob"] == "car_tp"
    by_id = get_general_line("title_insurance_gi")
    assert by_id is not None
    assert by_id["slug"] == "title-insurance"
    assert any("encumbrance" in d.lower() for d in by_id["documents"])
    assert get_general_line("not-a-line") is None


def test_category_filters():
    motor = list_general_lines(category_id="motor")
    assert len(motor) == 6
    assert all(line["category_id"] == "motor" for line in motor)
    cats = list_general_categories()
    motor_cat = next(c for c in cats if c["id"] == "motor")
    assert motor_cat["product_count"] == 6


def test_each_checklist_lob_has_catalog():
    for line in GENERAL_LINES:
        lob = line["checklist_lob"]
        assert lob in CATALOGS, f"missing catalog for {line['id']} → {lob}"
        flat = flatten_line_documents(line)
        result = package_checklist([], lob=lob)
        assert result["completeness_pct"] == 0.0
        assert len(result["missing"]) == len(flat), f"{line['id']} → {lob}"
        assert len(result["missing"]) >= 4


def test_detect_lob_general_keywords():
    assert detect_lob("third-party only car insurance registration certificate", "") == "general"
    assert detect_lob("international travel insurance passport visa itinerary", "") == "general"
    assert detect_lob("marine cargo bill of lading packing list", "") == "general"
    assert detect_lob("title insurance encumbrance certificate sale deed", "") == "general"
    assert detect_lob("yield-based crop insurance khasra sowing certificate", "") == "general"
    assert detect_lob("", "car_tp") == "car_tp"
    assert detect_lob("", "general") == "general"
    assert detect_lob("mediclaim proposal identity proof family floater", "") == "health"


def test_rate_general_is_catalog_only():
    from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission

    bundle = SubmissionBundle(
        bundle_id="gi-test",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                document_type="vehicle_rc",
                raw_text="Car third-party only. RC attached. Driving license. Age 34.",
            )
        ],
    )
    quote = rate_general(bundle, product_id="car_tp")
    assert quote.line == InsuranceLine.GENERAL
    assert quote.eligible is False
    assert quote.adjusted_premium == 0.0
    assert any("catalog-only" in r.lower() for r in quote.ineligibility_reasons)
    assert quote.metadata.get("benefit_type") == "motor_third_party"
    assert quote.metadata.get("vehicle_class") == "car"
