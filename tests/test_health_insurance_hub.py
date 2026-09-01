"""Health Insurance hub catalog + LOB detection."""

from __future__ import annotations

from insureflow.insurance.commercial_lobs import flatten_coverage_documents, flatten_line_documents
from insureflow.insurance.health_lobs import (
    HEALTH_BASE_PACKET,
    HEALTH_CATEGORIES,
    HEALTH_LINES,
    get_health_coverage,
    get_health_line,
    health_hub_payload,
    health_taxonomy_tree,
    list_health_categories,
    list_health_lines,
    resolve_health_checklist_lob,
)
from insureflow.insurance.package_checklist import CATALOGS, detect_lob, package_checklist
from insureflow.rating.models import InsuranceLine
from insureflow.rating.personal.health_rating import rate_health
from insureflow.underwriting.health_product import LIVE_HEALTH_PRODUCT_IDS, is_filed_health_product


def test_full_health_taxonomy_shape():
    assert len(HEALTH_CATEGORIES) == 8
    assert len(HEALTH_LINES) == 13
    cats = {c["id"] for c in HEALTH_CATEGORIES}
    assert cats == {
        "individual",
        "family_floater",
        "critical_illness",
        "senior",
        "group",
        "top_up",
        "personal_accident",
        "disability",
    }
    for line in HEALTH_LINES:
        assert line["category_id"] in cats
        assert len(line["documents"]) >= len(HEALTH_BASE_PACKET), line["id"]
        assert len(line["additional_documents"]) <= len(line["documents"]), line["id"]
        assert line["uw_focus"]
        assert line["insurance_line"] == "health"
        assert line["checklist_lob"]
        assert line["status"] == "live"
        for cov in line.get("coverages") or []:
            assert isinstance(cov, dict), line["id"]
            assert cov.get("id")
            assert cov.get("name")
            assert isinstance(cov.get("documents"), list)
            assert len(cov["documents"]) >= 1, f"{line['id']}.{cov.get('id')}"


def test_health_hub_fully_live():
    assert len(LIVE_HEALTH_PRODUCT_IDS) == len(HEALTH_LINES)
    assert is_filed_health_product("aca_marketplace_plan")
    live = [ln for ln in HEALTH_LINES if ln.get("status") == "live"]
    catalog = [ln for ln in HEALTH_LINES if ln.get("status") == "catalog"]
    assert len(live) == len(HEALTH_LINES)
    assert catalog == []
    hub = health_hub_payload()
    assert hub["stats"]["live_count"] == len(HEALTH_LINES)
    assert hub["stats"]["catalog_count"] == 0
    assert hub["stats"]["product_count"] == len(HEALTH_LINES)
    assert "HLTH-US-2026-01" in hub["summary"]
    assert "catalog-only" not in hub["uw_responsibilities"][-1]["summary"].lower()


def test_hub_payload_has_taxonomy_and_stats():
    hub = health_hub_payload()
    assert hub["segment"] == "personal_health"
    assert hub["title"] == "Health Insurance"
    assert len(hub["base_packet"]) == len(HEALTH_BASE_PACKET)
    assert "photo ID" in HEALTH_BASE_PACKET[0]
    assert len(hub["uw_responsibilities"]) >= 6
    assert hub["stats"]["category_count"] == 8
    assert hub["stats"]["product_count"] == len(HEALTH_LINES)
    assert len(hub["taxonomy"]) == 8
    assert len(hub["lines"]) == len(HEALTH_LINES)
    assert len(hub["categories"]) == 8
    sample = hub["lines"][0]
    assert "all_documents" in sample
    assert isinstance(sample["coverages"], list)


def test_taxonomy_tree_nests_disease_coverages():
    tree = health_taxonomy_tree()
    ci_cat = next(c for c in tree if c["id"] == "critical_illness")
    disease = next(p for p in ci_cat["products"] if p["id"] == "disease_specific_critical_illness")
    cov_ids = {c["id"] for c in disease["coverages"]}
    assert {"cancer_care", "cardiac_care", "diabetes_kidney_care"} <= cov_ids
    for cov in disease["coverages"]:
        assert cov["id"]
        assert isinstance(cov["documents"], list)
        assert len(cov["documents"]) >= 1


def test_flatten_coverage_documents_excludes_sibling_coverages():
    disease = get_health_line("disease_specific_critical_illness")
    assert disease is not None
    cancer = flatten_coverage_documents(disease, "cancer_care")
    cardiac = flatten_coverage_documents(disease, "cardiac_care")
    full = flatten_line_documents(disease)
    assert any("cancer" in d.lower() for d in cancer)
    assert not any("ecg" in d.lower() for d in cancer)
    assert any("ecg" in d.lower() or "cardiac" in d.lower() for d in cardiac)
    assert len(cancer) < len(full)
    assert len(cardiac) < len(full)


def test_resolve_health_coverage_id_to_product():
    assert resolve_health_checklist_lob("cancer_care") == "disease_specific_critical_illness"
    assert resolve_health_checklist_lob("Cancer Care") == "disease_specific_critical_illness"
    line, cov = get_health_coverage("disease_specific_critical_illness", "cancer_care")
    assert line is not None and cov is not None
    assert cov["id"] == "cancer_care"
    line_only, cov_only = get_health_coverage(None, "cardiac_care")
    assert line_only is not None and cov_only is not None
    assert line_only["checklist_lob"] == "disease_specific_critical_illness"
    assert cov_only["id"] == "cardiac_care"


def test_package_checklist_scopes_to_health_coverage():
    cancer = package_checklist([], lob="disease_specific_critical_illness", coverage_id="cancer_care")
    cardiac = package_checklist([], lob="disease_specific_critical_illness", coverage_id="cardiac_care")
    assert cancer["lob"] == "disease_specific_critical_illness"
    assert cancer["coverage_id"] == "cancer_care"
    assert cardiac["coverage_id"] == "cardiac_care"
    assert any("ecg" in m.lower() or "cardiac" in m.lower() for m in cardiac["missing"])
    assert not any("ecg" in m.lower() for m in cancer["missing"])


def test_get_line_by_slug_and_id():
    by_slug = get_health_line("aca-marketplace-plan")
    assert by_slug is not None
    assert by_slug["checklist_lob"] == "aca_marketplace_plan"
    assert len(by_slug["documents"]) >= len(HEALTH_BASE_PACKET)
    assert "all_documents" in by_slug

    by_id = get_health_line("family_health_plan")
    assert by_id is not None
    assert by_id["slug"] == "family-health-plan"
    assert any("marriage" in d.lower() for d in by_id["additional_documents"])

    by_checklist_lob = get_health_line("small_group_health")
    assert by_checklist_lob is not None
    assert by_checklist_lob["category_id"] == "group"

    assert get_health_line("not-a-line") is None


def test_base_packet_is_included_in_every_line():
    base_set = set(HEALTH_BASE_PACKET)
    for line in HEALTH_LINES:
        assert base_set <= set(line["documents"]), line["id"]
        assert base_set.isdisjoint(set(line["additional_documents"])), line["id"]


def test_category_filters():
    individual = list_health_lines(category_id="individual")
    assert len(individual) == 2
    assert all(line["category_id"] == "individual" for line in individual)
    cats = list_health_categories()
    ind_cat = next(c for c in cats if c["id"] == "individual")
    assert ind_cat["product_count"] == len(individual)


def test_each_checklist_lob_has_catalog():
    for line in HEALTH_LINES:
        lob = line["checklist_lob"]
        assert lob in CATALOGS, f"missing catalog for {line['id']} → {lob}"
        flat = flatten_line_documents(line)
        result = package_checklist([], lob=lob)
        assert result["completeness_pct"] == 0.0
        assert len(result["missing"]) == len(flat), f"{line['id']} → {lob}"
        assert len(result["missing"]) >= 5


def test_detect_lob_health_keywords_before_life():
    assert detect_lob("mediclaim proposal identity proof family floater", "") == "health"
    assert detect_lob("critical illness insurance medical test reports", "") == "health"
    assert detect_lob("personal accident occupation proof nominee", "") == "health"
    assert detect_lob("disability income salary slips medical fitness", "") == "health"
    assert detect_lob("", "aca_marketplace_plan") == "aca_marketplace_plan"
    assert detect_lob("", "health") == "health"
    assert detect_lob("term life insurance face amount beneficiary designation paramedical", "") == "life"


def test_rate_health_filed_mediclaim():
    from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission

    bundle = SubmissionBundle(
        bundle_id="health-test",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                document_type="health_application",
                raw_text="Mediclaim proposal. Age 34. Sum insured 500000. Self-declared good health.",
            )
        ],
    )
    quote = rate_health(bundle, product_id="individual_basic")
    assert quote.line == InsuranceLine.HEALTH
    assert quote.eligible is True
    assert quote.adjusted_premium > 0
    assert quote.metadata.get("rating_engine") == "health_filing"
    assert quote.metadata.get("filed") is True
    assert quote.metadata.get("benefit_type") == "hospitalization_indemnity"
    assert quote.metadata.get("age") == 34
    assert quote.metadata.get("sum_insured") == 500_000
    assert any(c.name == "attained_age" for c in quote.schedule_modifications)
    assert quote.rate_per_100_tiv > 0


def test_rate_health_income_basis_disability():
    from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission

    bundle = SubmissionBundle(
        bundle_id="health-di",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                document_type="health_application",
                raw_text="Disability income. Age 40. Monthly income 100000. Good health.",
            )
        ],
    )
    quote = rate_health(bundle, product_id="disability_income")
    assert quote.eligible is True
    assert quote.adjusted_premium > 0
    assert quote.metadata.get("rating_engine") == "health_filing"
    assert quote.metadata.get("sum_insured") == 1_800_000


def test_rate_health_daily_cash_hospital():
    from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission

    bundle = SubmissionBundle(
        bundle_id="health-hc",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                document_type="health_application",
                raw_text="Hospital cash. Age 50. Daily cash 1000. Good health.",
            )
        ],
    )
    quote = rate_health(bundle, product_id="hospital_cash")
    assert quote.eligible is True
    assert quote.adjusted_premium > 0
    assert quote.metadata.get("sum_insured") == 365_000


def test_rate_health_missing_sum_insured_ineligible():
    from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission

    bundle = SubmissionBundle(
        bundle_id="health-nosi",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                document_type="health_application",
                raw_text="Mediclaim proposal. Age 34. Self-declared good health.",
            )
        ],
    )
    quote = rate_health(bundle, product_id="individual_basic")
    assert quote.eligible is False
    assert quote.adjusted_premium == 0.0
    assert any("sum insured not declared" in r.lower() for r in quote.ineligibility_reasons)


def test_rate_health_age_gate_routes_senior():
    from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission

    bundle = SubmissionBundle(
        bundle_id="health-age",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                document_type="health_application",
                raw_text="Mediclaim proposal. Age 65. Sum insured 500000. Self-declared good health.",
            )
        ],
    )
    quote = rate_health(bundle, product_id="individual_basic")
    assert quote.eligible is False
    assert any("above the" in r.lower() for r in quote.ineligibility_reasons)
    senior = rate_health(bundle, product_id="senior_standard")
    assert senior.eligible is True
    assert senior.adjusted_premium > quote.adjusted_premium
