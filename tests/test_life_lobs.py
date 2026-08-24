"""End-to-end tests for dedicated LOB/Product/Coverage logic paths.

Verifies the confirmed architecture: every Term Life and Whole Life product
has its own logic path, state rules are applied INSIDE each path (stamped as
state_rules_applied), and unregistered products still fall back to generic
family pricing.
"""

from __future__ import annotations

import pytest

from insureflow.insurance.life_lobs import LIFE_LINES
from insureflow.life.lobs import PRODUCT_LOGIC_PATHS, resolve_logic_path
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.personal.life_rating import rate_life


def _bundle(
    text: str = "Term life application. Applicant age: 42. Sex: female. Face amount: $500000. Annual income: 145000. Non-smoker. Preferred. Blood pressure: 118/76. BMI: 23.4. Cholesterol: 185.",
) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="lob-test",
        unstructured=[UnstructuredSubmission(submission_id="d0", source="app.md", raw_text=text, document_type="supplemental")],
    )


# ---------------------------------------------------------------------------
# Registry / smart lines
# ---------------------------------------------------------------------------


def test_all_term_and_whole_products_have_dedicated_paths() -> None:
    expected = {
        "level_term",
        "decreasing_term",
        "mortgage_life",
        "increasing_term",
        "renewable_term",
        "convertible_term",
        "rop_term",
        "group_term_life",
        "credit_life",
        "traditional_whole_life",
        "limited_pay_whole_life",
        "single_premium_whole_life",
        "participating_whole_life",
        "non_participating_whole_life",
        "modified_whole_life",
        "graded_guaranteed_issue_whole_life",
    }
    assert expected == set(PRODUCT_LOGIC_PATHS.keys())


def test_catalog_nodes_stamped_with_logic_path() -> None:
    stamped = {ln["id"] for ln in LIFE_LINES if ln.get("logic_path")}
    assert stamped == set(PRODUCT_LOGIC_PATHS.keys())
    level = next(ln for ln in LIFE_LINES if ln["id"] == "level_term")
    assert {c["id"] for c in level["coverages"]} >= {"level_term_10", "level_term_15", "level_term_20", "level_term_25", "level_term_30"}


def test_resolution_by_product_and_by_coverage_hint() -> None:
    assert resolve_logic_path("level_term") == "insureflow.life.lobs.term_life.level_term"
    assert resolve_logic_path(None, "ten_pay") == "insureflow.life.lobs.whole_life.limited_pay"
    assert resolve_logic_path(None, None, "Graded Benefit Whole Life").endswith("whole_life.graded")
    assert resolve_logic_path("cyber_liability") is None


# ---------------------------------------------------------------------------
# LOB 1 — Term Life product paths
# ---------------------------------------------------------------------------


def test_level_term_duration_ladder_via_lob_path() -> None:
    premiums = {}
    for years in (10, 15, 20, 25, 30):
        q = rate_life(_bundle(), coverage_id=f"level_term_{years}", state="IL")
        assert q.metadata["lob_logic_path"] == "insureflow.life.lobs.term_life.level_term"
        assert q.metadata["term_years"] == years
        assert q.metadata["rating_engine"] == "life_filing"
        premiums[years] = q.adjusted_premium
    assert premiums[10] < premiums[15] < premiums[20] < premiums[25] < premiums[30]


def test_decreasing_cheaper_than_level_and_amortizes() -> None:
    level = rate_life(_bundle(), coverage_id="level_term_20", product_id="level_term")
    mortgage = rate_life(
        _bundle(),
        coverage_id="mortgage_term",
        coverage_name="Mortgage Protection Term",
        product_id="decreasing_term",
    )
    debt = rate_life(
        _bundle(),
        coverage_id="debt_term",
        coverage_name="Debt-Reducing Term",
        product_id="decreasing_term",
    )
    assert mortgage.metadata["variant"]["amortize"] is True
    assert mortgage.adjusted_premium < level.adjusted_premium
    assert debt.adjusted_premium != mortgage.adjusted_premium


def test_mortgage_life_lender_assignment_loads_admin() -> None:
    plain = rate_life(_bundle(), coverage_id="mortgage_balance", product_id="mortgage_life")
    assigned = rate_life(_bundle(), coverage_id="lender_assign", coverage_name="Lender-Assigned Benefit", product_id="mortgage_life")
    assert assigned.adjusted_premium > plain.adjusted_premium
    assert any("assignment" in c.lower() for c in assigned.metadata["conditions"] or [])


def test_increasing_term_cpi_vs_step_up() -> None:
    cpi = rate_life(_bundle(), coverage_id="cpi_term", coverage_name="CPI-Linked Increasing Term", product_id="increasing_term")
    step = rate_life(_bundle(), coverage_id="step_term", coverage_name="Step-Up Increasing Term", product_id="increasing_term")
    assert cpi.metadata["projected_final_face"] < step.metadata["projected_final_face"]
    assert cpi.adjusted_premium > rate_life(_bundle(), coverage_id="level_term_20", product_id="level_term").adjusted_premium * 0.9


def test_renewable_art_has_renewal_schedule() -> None:
    art = rate_life(_bundle(), coverage_id="art_style", coverage_name="Annual Renewable Style", product_id="renewable_term")
    schedule = art.metadata["renewal_schedule"]
    assert len(schedule) > 25  # annual periods to age 75
    assert all(p["term_years"] == 1 for p in schedule[:5])
    ten_year = rate_life(_bundle(), coverage_id="renewal_period", coverage_name="Renewable Term (Renewal)", product_id="renewable_term")
    assert ten_year.metadata["renewal_schedule"][0]["term_years"] == 10


def test_convertible_term_conversion_privilege() -> None:
    conv = rate_life(_bundle(), coverage_id="convert_period", coverage_name="Convertible Term (Conversion)", product_id="convertible_term")
    assert conv.eligible is True
    assert any(c.name == "conversion_privilege_load" for c in conv.schedule_modifications)
    assert conv.metadata["conversion_deadline_age"] == 65
    old = rate_life(_bundle("Applicant age: 68. Face amount: $300000. Non-smoker."), coverage_id="convert_period", product_id="convertible_term")
    assert old.eligible is False


def test_rop_full_costs_more_than_partial() -> None:
    full = rate_life(_bundle(), coverage_id="full_rop", coverage_name="Full Return-of-Premium Rider", product_id="rop_term")
    partial = rate_life(_bundle(), coverage_id="partial_rop", coverage_name="Partial Return-of-Premium Rider", product_id="rop_term")
    plain = rate_life(_bundle(), coverage_id="level_term_20", product_id="level_term")
    assert full.adjusted_premium > partial.adjusted_premium > plain.adjusted_premium
    assert full.metadata["refund_pct_at_maturity"] == 1.0
    assert partial.metadata["refund_pct_at_maturity"] == 0.65


def test_group_simplified_underwriting_no_exam() -> None:
    basic = rate_life(_bundle(), coverage_id="basic_group", product_id="group_term_life")
    supp = rate_life(_bundle(), coverage_id="supplemental_group", product_id="group_term_life")
    dep = rate_life(_bundle(), coverage_id="dependent_group", product_id="group_term_life")
    assert basic.eligible is True
    assert basic.metadata["exam_required"] is False
    assert basic.adjusted_premium < supp.adjusted_premium < rate_life(_bundle(), coverage_id="level_term_20", product_id="level_term").adjusted_premium
    assert dep.adjusted_premium < basic.adjusted_premium
    assert any("IRC" in c for c in basic.metadata["conditions"])


def test_credit_life_caps_face_and_simplified_issue() -> None:
    big = rate_life(_bundle("Face amount: $900000. Applicant age: 35. Non-smoker."), coverage_id="loan_balance", product_id="credit_life")
    assert big.metadata["capped_face"] <= 250000
    assert big.metadata["exam_required"] is False
    assert any("capped" in r.lower() for r in big.ineligibility_reasons) or big.metadata["capped_face"] == big.metadata["face_amount"]
    senior = rate_life(_bundle("Face amount: $40000. Applicant age: 74."), coverage_id="loan_balance", product_id="credit_life")
    assert senior.eligible is False


# ---------------------------------------------------------------------------
# LOB 2 — Whole Life sub-product paths
# ---------------------------------------------------------------------------


def test_limited_pay_ordering_10_pay_gt_20_pay_gt_lifetime() -> None:
    lifetime = rate_life(_bundle(), coverage_name="Traditional Whole Life", product_id="traditional_whole_life")
    lp20 = rate_life(_bundle(), coverage_id="twenty_pay", product_id="limited_pay_whole_life")
    lp10 = rate_life(_bundle(), coverage_id="ten_pay", product_id="limited_pay_whole_life")
    assert lp20.adjusted_premium > lifetime.adjusted_premium
    assert lp10.adjusted_premium > lp20.adjusted_premium
    assert lp10.metadata["actuarial"]["premium_term"] == 10


def test_single_premium_equals_nsp_scale() -> None:
    sp = rate_life(_bundle(), coverage_id="lump_sum", product_id="single_premium_whole_life")
    lifetime = rate_life(_bundle(), coverage_name="Guaranteed Whole Life", product_id="traditional_whole_life")
    assert sp.adjusted_premium > lifetime.adjusted_premium * 10
    assert sp.metadata["actuarial"]["premium_term"] == 1
    assert sp.metadata["mec_notice_required"] is True
    assert any("AML" in c or "source-of-funds" in c.lower() for c in sp.metadata["conditions"])


def test_par_costs_more_than_non_par() -> None:
    par_cash = rate_life(_bundle(), coverage_id="div_cash", product_id="participating_whole_life")
    par_pua = rate_life(_bundle(), coverage_id="div_pua", product_id="participating_whole_life")
    nonpar = rate_life(_bundle(), coverage_id="non_par_whole", product_id="non_participating_whole_life")
    assert par_cash.adjusted_premium == pytest.approx(nonpar.adjusted_premium * 1.12, rel=0.02)
    assert par_pua.adjusted_premium == pytest.approx(par_cash.adjusted_premium, rel=0.01)
    assert any("NOT guaranteed" in c or "not guaranteed" in c.lower() for c in par_cash.metadata["conditions"])


def test_modified_step_up_schedule() -> None:
    mod = rate_life(_bundle(), coverage_id="modified_step", product_id="modified_whole_life")
    schedule = mod.metadata["premium_schedule"]
    assert schedule["years_1_to_step"]["ratio"] == 0.60
    assert schedule["year_step_onward"]["annual"] > schedule["years_1_to_step"]["annual"]
    m510 = rate_life(_bundle(), coverage_id="modified_5_10", product_id="modified_whole_life")
    assert m510.metadata["premium_schedule"]["variant_5_10"] is True


def test_graded_gi_no_exam_with_medical_decline() -> None:
    sick = _bundle("Applicant age: 62. Face amount: $25000. Active cancer on chemotherapy. Insulin-dependent diabetes.")
    gi = rate_life(sick, coverage_id="guaranteed_issue", coverage_name="Guaranteed Issue Whole Life", product_id="graded_guaranteed_issue_whole_life")
    assert gi.metadata["exam_required"] is False
    assert gi.metadata["simplified_underwriting"] is True
    assert gi.metadata["capped_face"] == 25000
    graded = rate_life(sick, coverage_id="graded_benefit", coverage_name="Graded Benefit Whole Life", product_id="graded_guaranteed_issue_whole_life")
    assert graded.metadata["graded_schedule"] == {"1": 0.30, "2": 0.65}
    young = rate_life(_bundle(), coverage_id="guaranteed_issue", product_id="graded_guaranteed_issue_whole_life")
    assert young.eligible is False  # age 42 outside GI window


def test_traditional_whole_life_actuarial_metadata() -> None:
    wl = rate_life(_bundle(), coverage_name="Guaranteed Whole Life", product_id="traditional_whole_life")
    act = wl.metadata["actuarial"]
    assert act["pv_whole_life_benefits"] > 0
    assert act["gross_premium"] > act["level_net_premium"]
    assert wl.eligible is False  # no filed permanent rates in pilot
    assert any("illustrative" in r.lower() for r in wl.ineligibility_reasons)


# ---------------------------------------------------------------------------
# State rules applied INSIDE each path
# ---------------------------------------------------------------------------


def test_state_rules_inside_path_connecticut() -> None:
    ct = rate_life(_bundle(), coverage_id="level_term_20", product_id="level_term", state="CT")
    rules = ct.metadata["state_rules_applied"]
    assert rules["issue_state"] == "CT"
    assert rules["free_look_days"] == 30
    assert rules["paramed_face_threshold"] == 100000.0
    assert rules["source"] == "state_table"
    assert any("free-look" in c for c in ct.metadata["conditions"])
    # CT has no filed rates → filing gate fires inside this path
    assert ct.eligible is False
    assert any("CT state-of-issue" in r for r in ct.ineligibility_reasons)


def test_state_rules_carrier_default_when_state_unknown() -> None:
    tx = rate_life(_bundle(), coverage_id="level_term_20", product_id="level_term", state="TX")
    rules = tx.metadata["state_rules_applied"]
    assert rules["issue_state"] == "TX"
    assert rules["source"] == "carrier_default"
    assert rules["free_look_days"] == 10


def test_unisex_state_forces_one_sex_table() -> None:
    # Within a unisex state, a female and a male applicant price identically.
    female = _bundle("Term life application. Applicant age: 42. Sex: female. Face amount: $500000. Annual income: 145000. Non-smoker. Preferred.")
    male = _bundle("Term life application. Applicant age: 42. Sex: male. Face amount: $500000. Annual income: 145000. Non-smoker. Preferred.")
    mt_female = rate_life(female, coverage_id="level_term_20", product_id="level_term", state="MT")
    mt_male = rate_life(male, coverage_id="level_term_20", product_id="level_term", state="MT")
    assert mt_female.adjusted_premium == mt_male.adjusted_premium


def test_unregistered_coverage_falls_back_to_generic_path() -> None:
    generic = rate_life(_bundle())  # no product/coverage hints at all
    assert "lob_logic_path" not in generic.metadata
    assert generic.metadata["filing_id"]
