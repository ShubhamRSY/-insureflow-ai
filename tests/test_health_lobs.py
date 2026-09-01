"""End-to-end tests for dedicated health LOB/Product/Coverage logic paths.

Mirrors tests/test_life_lobs.py: every product has its own logic path, state
rules are applied INSIDE each path (stamped as state_rules_applied), and
unregistered products still fall back to the legacy engine.
"""

from __future__ import annotations

from insureflow.health.lobs import PRODUCT_LOGIC_PATHS, resolve_logic_path
from insureflow.insurance.health_lobs import HEALTH_LINES
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.personal.health_rating import rate_health


def _bundle(text: str) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="health-lob-test",
        unstructured=[UnstructuredSubmission(submission_id="d0", source="app.md", raw_text=text, document_type="supplemental")],
    )


# ---------------------------------------------------------------------------
# Registry / catalog
# ---------------------------------------------------------------------------


def test_all_catalog_products_have_dedicated_paths():
    expected = {
        "aca_marketplace_plan",
        "off_exchange_major_medical",
        "family_health_plan",
        "critical_illness_standalone",
        "disease_specific_critical_illness",
        "medicare_supplement",
        "medicare_advantage",
        "small_group_health",
        "large_group_health",
        "supplemental_gap_coverage",
        "add_accident_indemnity",
        "short_term_disability",
        "long_term_disability",
    }
    assert set(PRODUCT_LOGIC_PATHS) == expected
    assert {ln["id"] for ln in HEALTH_LINES} == expected


def test_catalog_nodes_stamped_with_logic_path():
    for line in HEALTH_LINES:
        assert line.get("logic_path") == PRODUCT_LOGIC_PATHS[line["id"]], line["id"]
        for cov in line.get("coverages") or []:
            assert cov.get("logic_path") == PRODUCT_LOGIC_PATHS[line["id"]], (line["id"], cov.get("id"))


def test_resolution_by_coverage_hint():
    assert resolve_logic_path(None, "bronze_plan", "Bronze Plan") == "insureflow.health.lobs.individual.bronze_silver_plans"
    assert resolve_logic_path(None, "medigap_plan_g") == "insureflow.health.lobs.senior.medicare_supplement"
    assert resolve_logic_path(None, "short_term_disability_std") == "insureflow.health.lobs.disability.short_term_disability"


# ---------------------------------------------------------------------------
# Individual / Family — ACA guaranteed issue
# ---------------------------------------------------------------------------

_INDIVIDUAL_TEXT = "Applicant age: 34. Sex: female. Annual income: 65000. Non-smoker."


def test_metal_tier_ordering():
    tiers = {}
    for tier in ("bronze", "silver", "gold", "platinum"):
        q = rate_health(_bundle(_INDIVIDUAL_TEXT), coverage_id=tier, product_id="aca_marketplace_plan", state="IL")
        assert q.metadata["lob_logic_path"] == "insureflow.health.lobs.individual.bronze_silver_plans"
        tiers[tier] = q.adjusted_premium
    assert tiers["bronze"] < tiers["silver"] < tiers["gold"] < tiers["platinum"]


def test_individual_is_guaranteed_issue_regardless_of_health_status():
    # ACA §2702 — no health-status decline, even with disclosed conditions.
    sick_text = "Applicant age: 50. Sex: male. Annual income: 80000. Diabetes. Heart attack history."
    q = rate_health(_bundle(sick_text), coverage_id="silver", product_id="aca_marketplace_plan", state="TX")
    assert q.eligible is True
    assert q.adjusted_premium > 0


def test_off_exchange_not_subsidy_eligible():
    q = rate_health(_bundle(_INDIVIDUAL_TEXT), coverage_id="off_exchange_standard", product_id="off_exchange_major_medical", state="IL")
    assert q.eligible is True
    assert q.metadata["subsidy_eligible"] is False
    assert any("subsidy" in c.lower() for c in q.metadata["conditions"])


def test_marketplace_age_ceiling_hands_off_to_medicare():
    q = rate_health(_bundle("Applicant age: 65. Sex: male. Annual income: 40000."), coverage_id="silver", product_id="aca_marketplace_plan", state="IL")
    assert q.eligible is False
    assert any("medicare" in r.lower() for r in q.ineligibility_reasons)


# ---------------------------------------------------------------------------
# Family Health Plan
# ---------------------------------------------------------------------------


def test_family_plan_uses_household_composite_tier():
    self_only = rate_health(_bundle(_INDIVIDUAL_TEXT), coverage_id="silver", product_id="aca_marketplace_plan", state="IL")
    family_text = _INDIVIDUAL_TEXT + " Household size: 4."
    family = rate_health(_bundle(family_text), coverage_id="standard_family", product_id="family_health_plan", state="IL")
    assert family.eligible is True
    assert family.adjusted_premium > self_only.adjusted_premium
    assert family.metadata["household_members"] == 4
    assert family.metadata["deductible_basis"] == "aggregate_family"


# ---------------------------------------------------------------------------
# Critical Illness
# ---------------------------------------------------------------------------


def test_ci_standalone_uses_real_sex_specific_morbidity():
    male = rate_health(_bundle("Applicant age: 55. Sex: male. Lump sum: $100000."), coverage_id="ci_standalone", product_id="critical_illness_standalone", state="IL")
    female = rate_health(_bundle("Applicant age: 55. Sex: female. Lump sum: $100000."), coverage_id="ci_standalone", product_id="critical_illness_standalone", state="IL")
    assert male.eligible is True and female.eligible is True
    # Female morbidity table is lower at every age in the filed manual.
    assert female.adjusted_premium < male.adjusted_premium
    assert male.metadata["morbidity_sex_source"] == "submission"


def test_disease_specific_cardiac_requires_exam_cancer_does_not():
    cardiac = rate_health(_bundle("Applicant age: 50. Sex: male. Lump sum: $100000."), coverage_id="cardiac_care", product_id="disease_specific_critical_illness", state="IL")
    cancer = rate_health(_bundle("Applicant age: 50. Sex: male. Lump sum: $100000."), coverage_id="cancer_care", product_id="disease_specific_critical_illness", state="IL")
    assert cardiac.metadata["exam_required"] is True
    assert cancer.metadata["exam_required"] is False
    assert cardiac.adjusted_premium > cancer.adjusted_premium  # cardiac carries a higher disease load


# ---------------------------------------------------------------------------
# Senior — Medicare Supplement / Advantage
# ---------------------------------------------------------------------------


def test_medigap_guaranteed_issue_within_open_enrollment_else_underwritten():
    within = rate_health(_bundle("Applicant age: 65."), coverage_id="open_enrollment_plan_g", product_id="medicare_supplement", state="TX")
    outside = rate_health(_bundle("Applicant age: 68."), coverage_id="plan_g", product_id="medicare_supplement", state="TX")
    assert within.metadata["guaranteed_issue"] is True
    assert outside.metadata["guaranteed_issue"] is False
    assert any("full medical underwriting" in c.lower() for c in outside.metadata["conditions"])


def test_medigap_continuous_gi_state_overrides_window():
    outside_gi_state = rate_health(_bundle("Applicant age: 70."), coverage_id="plan_n", product_id="medicare_supplement", state="NY")
    assert outside_gi_state.metadata["guaranteed_issue"] is True


def test_medigap_plan_letter_ordering():
    a = rate_health(_bundle("Applicant age: 66."), coverage_id="open_enrollment_plan_a", product_id="medicare_supplement", state="IL")
    g = rate_health(_bundle("Applicant age: 66."), coverage_id="open_enrollment_plan_g", product_id="medicare_supplement", state="IL")
    # Plan A covers less than Plan G — falls back to plan letter parsing; both use the "open_enrollment" hint.
    assert a.metadata["plan_letter"] == "A"
    assert g.metadata["plan_letter"] == "G"
    assert a.adjusted_premium < g.adjusted_premium


def test_medicare_advantage_always_guaranteed_issue():
    q = rate_health(_bundle("Applicant age: 66. Diabetes. Prior cancer."), coverage_id="ma_standard", product_id="medicare_advantage", state="TX")
    assert q.eligible is True
    assert q.metadata["guaranteed_issue"] is True


def test_medicare_products_gate_under_65():
    q = rate_health(_bundle("Applicant age: 60."), coverage_id="plan_g", product_id="medicare_supplement", state="IL")
    assert q.eligible is False
    assert any("65" in r for r in q.ineligibility_reasons)


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------


def test_small_group_over_threshold_routes_to_large_group():
    q = rate_health(_bundle("Applicant age: 35. Employee count: 75."), coverage_id="small_group_standard", product_id="small_group_health", state="IL")
    assert q.eligible is False
    assert any("large group" in r.lower() for r in q.ineligibility_reasons)


def test_large_group_self_funded_erisa_preemption():
    text = "Applicant age: 40. Employee count: 500."
    self_funded = rate_health(_bundle(text), coverage_id="self_funded", product_id="large_group_health", state="CA")
    fully_insured = rate_health(_bundle(text), coverage_id="fully_insured", product_id="large_group_health", state="CA")
    assert any("erisa preemption" in c.lower() for c in self_funded.metadata["conditions"])
    assert not any("erisa preemption" in c.lower() for c in fully_insured.metadata["conditions"])


def test_large_group_experience_discount_scales_with_size():
    small = rate_health(_bundle("Applicant age: 40. Employee count: 60."), coverage_id="fully_insured", product_id="large_group_health", state="IL")
    big = rate_health(_bundle("Applicant age: 40. Employee count: 5000."), coverage_id="fully_insured", product_id="large_group_health", state="IL")
    assert big.metadata["per_employee_monthly"] < small.metadata["per_employee_monthly"]


# ---------------------------------------------------------------------------
# Top-up / Super Top-up
# ---------------------------------------------------------------------------


def test_higher_deductible_makes_gap_coverage_cheaper():
    low = rate_health(_bundle("Applicant age: 35. Base plan deductible: $5000."), coverage_id="standard_gap", product_id="supplemental_gap_coverage", state="IL")
    high = rate_health(_bundle("Applicant age: 35. Base plan deductible: $50000."), coverage_id="standard_gap", product_id="supplemental_gap_coverage", state="IL")
    assert high.adjusted_premium < low.adjusted_premium


def test_super_gap_flagged_as_annual_aggregate():
    q = rate_health(_bundle("Applicant age: 35. Base plan deductible: $10000."), coverage_id="super_gap", product_id="supplemental_gap_coverage", state="IL")
    assert q.metadata["deductible_basis"] == "annual_aggregate"


# ---------------------------------------------------------------------------
# Personal Accident / AD&D
# ---------------------------------------------------------------------------


def test_add_hazardous_occupation_costs_more_and_refers():
    desk = rate_health(_bundle("Applicant age: 35. Principal sum: $250000. Software engineer."), coverage_id="individual", product_id="add_accident_indemnity", state="IL")
    mining = rate_health(_bundle("Applicant age: 35. Principal sum: $250000. Underground mine worker."), coverage_id="individual", product_id="add_accident_indemnity", state="IL")
    assert mining.adjusted_premium > desk.adjusted_premium
    assert mining.metadata["occupation_class"] == "IV"
    assert any("refer" in c.lower() for c in mining.metadata["conditions"])


# ---------------------------------------------------------------------------
# Disability Income
# ---------------------------------------------------------------------------


def test_std_flags_sdi_coordination_in_sdi_states_only():
    text = "Applicant age: 30. Weekly benefit: $600. Annual income: 70000."
    ca = rate_health(_bundle(text), coverage_id="std_standard", product_id="short_term_disability", state="CA")
    tx = rate_health(_bundle(text), coverage_id="std_standard", product_id="short_term_disability", state="TX")
    assert ca.metadata["sdi_coordination_required"] is True
    assert tx.metadata["sdi_coordination_required"] is False
    assert any("sdi" in c.lower() for c in ca.metadata["conditions"])
    assert not any("sdi" in c.lower() for c in tx.metadata["conditions"])


def test_ltd_income_replacement_ceiling_flagged():
    over_ceiling = rate_health(
        _bundle("Applicant age: 40. Monthly benefit: $8000. Annual income: 90000."),
        coverage_id="ltd_standard",
        product_id="long_term_disability",
        state="IL",
    )
    assert any("income-replacement ceiling" in c.lower() for c in over_ceiling.metadata["conditions"])


def test_ltd_occupation_class_and_elimination_period_affect_price():
    base_text = "Applicant age: 40. Monthly benefit: $3000. Annual income: 90000."
    desk = rate_health(_bundle(base_text + " Accountant. Elimination period: 90 days."), coverage_id="ltd_standard", product_id="long_term_disability", state="IL")
    hazardous = rate_health(_bundle(base_text + " Offshore rig worker. Elimination period: 90 days."), coverage_id="ltd_standard", product_id="long_term_disability", state="IL")
    short_elim = rate_health(_bundle(base_text + " Accountant. Elimination period: 7 days."), coverage_id="ltd_standard", product_id="long_term_disability", state="IL")
    assert hazardous.adjusted_premium > desk.adjusted_premium
    assert short_elim.adjusted_premium > desk.adjusted_premium  # shorter elimination period costs more


# ---------------------------------------------------------------------------
# State-rules-inside-path
# ---------------------------------------------------------------------------


def test_state_rules_stamped_and_mandated_benefits_surface():
    q = rate_health(_bundle(_INDIVIDUAL_TEXT), coverage_id="silver", product_id="aca_marketplace_plan", state="CA")
    rules = q.metadata["state_rules_applied"]
    assert rules["issue_state"] == "CA"
    assert rules["source"] == "state_table"
    assert isinstance(rules.get("mandated_benefits"), list)


def test_unregistered_product_falls_back_to_legacy_engine():
    # Old India-market ids are not in the new registry — must not raise, and
    # must be handled by the legacy engine, not silently dropped.
    q = rate_health(_bundle("Age: 34. Sum insured: 500000."), product_id="individual_basic")
    assert q.metadata.get("rating_engine") in ("health_filing", "catalog_only")
