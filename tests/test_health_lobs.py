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
        "short_term_limited_duration",
        "hdhp_hsa_qualified",
        "catastrophic_plan",
        "family_health_plan",
        "family_hdhp_hsa_qualified",
        "family_extended_dependents",
        "critical_illness_standalone",
        "disease_specific_critical_illness",
        "critical_illness_rider",
        "critical_illness_multistage",
        "medicare_supplement",
        "medicare_advantage",
        "medigap_high_deductible_plan_g",
        "medicare_advantage_snp",
        "small_group_health",
        "large_group_health",
        "association_health_plan",
        "public_sector_group_health",
        "level_funded_group_health",
        "supplemental_gap_coverage",
        "hospital_indemnity",
        "add_accident_indemnity",
        "standalone_add",
        "short_term_disability",
        "long_term_disability",
        "disability_ptd",
        "disability_ppd",
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


_FULL_KYC_TEXT = "Identity proof photo ID. Address proof utility bill. Age proof birth certificate. Passport-size photograph. Proposal form. Self-declared good health. Annual income: 65000."


def test_aca_products_never_claim_a_pre_existing_condition_waiting_period():
    # The reused handler's default disclosure ("PED waiting period apply per
    # filing") is flatly false for ACA products — ACA §2704 bans PED
    # exclusions entirely, on every individual/family plan.
    for product_id, coverage_id in (
        ("aca_marketplace_plan", "silver"),
        ("off_exchange_major_medical", "off_exchange_standard"),
        ("family_health_plan", "standard_family"),
    ):
        text = f"Applicant age: 40. Sex: female. {_FULL_KYC_TEXT}"
        if product_id == "family_health_plan":
            text += " Household size: 3."
        q = rate_health(_bundle(text), coverage_id=coverage_id, product_id=product_id, state="IL")
        conditions_l = [c.lower() for c in q.metadata["conditions"]]
        assert not any("ped waiting period" in c for c in conditions_l), product_id
        assert any("aca" in c and "2704" in c for c in conditions_l), product_id


def test_aca_marketplace_does_not_falsely_route_pre_medicare_seniors():
    # The reused handler's "age 60+ -> route to senior" gate uses the source
    # market's senior threshold, not the real US Medicare age of 65 (already
    # enforced by MAX_ISSUE_AGE=64) — a 62-year-old with complete paperwork
    # must clear straight to ACCEPT, not a false referral.
    text = f"Applicant age: 62. Sex: female. {_FULL_KYC_TEXT}"
    q = rate_health(_bundle(text), coverage_id="silver", product_id="aca_marketplace_plan", state="IL")
    assert q.metadata["outcome"] == "accept"
    assert not any("senior" in c.lower() for c in q.metadata["conditions"])
    assert not any("referral" in c.lower() for c in q.metadata["conditions"])


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


def test_medigap_guaranteed_issue_never_declines_on_disclosed_condition():
    # The reused "senior_no_medical" handler ("simplified issue") still
    # carries a CRITICAL knockout gate on a disclosed severe condition —
    # real guaranteed issue (open enrollment, or a continuous-GI state
    # outside it) has zero exceptions and must never decline on this.
    sick = "Applicant age: 70. Cancer diagnosed 2 years ago. Currently in remission."
    open_enrollment = rate_health(_bundle(sick), coverage_id="open_enrollment_plan_g", product_id="medicare_supplement", state="TX")
    assert open_enrollment.eligible is True

    continuous_gi_outside_window = rate_health(_bundle(sick), coverage_id="plan_n", product_id="medicare_supplement", state="NY")
    assert continuous_gi_outside_window.eligible is True
    assert continuous_gi_outside_window.metadata["guaranteed_issue"] is True


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


def test_small_group_threshold_is_state_specific():
    # CA/CO/NY/VT raised their small-group ceiling to 100 (45 CFR 144.103
    # state flexibility) — the same 75-employee group is still Small Group
    # there but must route to Large Group in a default-threshold state.
    text = "Applicant age: 35. Employee count: 75."
    ca = rate_health(_bundle(text), coverage_id="small_group_standard", product_id="small_group_health", state="CA")
    il = rate_health(_bundle(text), coverage_id="small_group_standard", product_id="small_group_health", state="IL")
    assert ca.eligible is True
    assert ca.metadata["small_group_max"] == 100
    assert il.eligible is False
    assert il.metadata["small_group_max"] == 50


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


def test_std_elimination_period_actually_affects_price():
    # Elimination period used to be a hardcoded metadata label never fed into
    # the rate formula, despite the manual already carrying real STD
    # elimination_period_factors for 7/14/30 days — a shorter elimination
    # period (insurer pays sooner) must cost more, not the same.
    base = "Applicant age: 30. Weekly benefit: $600. Annual income: 70000."
    short = rate_health(_bundle(base + " Elimination period: 7 days."), coverage_id="std_standard", product_id="short_term_disability", state="TX")
    mid = rate_health(_bundle(base + " Elimination period: 14 days."), coverage_id="std_standard", product_id="short_term_disability", state="TX")
    long_ = rate_health(_bundle(base + " Elimination period: 30 days."), coverage_id="std_standard", product_id="short_term_disability", state="TX")
    assert short.adjusted_premium > mid.adjusted_premium > long_.adjusted_premium
    assert short.metadata["elimination_period_days"] == 7
    assert any(c.name == "elimination_period" for c in short.schedule_modifications)


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


# ---------------------------------------------------------------------------
# Breadth expansion — Individual (STLDI, HDHP, Catastrophic)
# ---------------------------------------------------------------------------


def test_stldi_banned_in_restricted_states_available_elsewhere():
    text = "Applicant age: 35. Non-smoker."
    banned = rate_health(_bundle(text), coverage_id="stldi_standard", product_id="short_term_limited_duration", state="CA")
    allowed = rate_health(_bundle(text), coverage_id="stldi_standard", product_id="short_term_limited_duration", state="TX")
    assert banned.eligible is False
    assert any("bans" in r.lower() or "not permit" in r.lower() for r in banned.ineligibility_reasons)
    assert allowed.eligible is True


def test_stldi_cheaper_than_aca_marketplace_same_profile():
    text = "Applicant age: 35. Non-smoker. Annual income: 60000."
    stldi = rate_health(_bundle(text), coverage_id="stldi_standard", product_id="short_term_limited_duration", state="TX")
    bronze = rate_health(_bundle(text), coverage_id="bronze", product_id="aca_marketplace_plan", state="TX")
    assert stldi.adjusted_premium < bronze.adjusted_premium


def test_hdhp_higher_deductible_is_cheaper_and_hsa_eligibility_tracked():
    low = rate_health(_bundle("Applicant age: 35. Non-smoker. Deductible: 1650."), coverage_id="hdhp_standard", product_id="hdhp_hsa_qualified", state="TX")
    high = rate_health(_bundle("Applicant age: 35. Non-smoker. Deductible: 8300."), coverage_id="hdhp_standard", product_id="hdhp_hsa_qualified", state="TX")
    below_min = rate_health(_bundle("Applicant age: 35. Non-smoker. Deductible: 500."), coverage_id="hdhp_standard", product_id="hdhp_hsa_qualified", state="TX")
    assert high.adjusted_premium < low.adjusted_premium
    assert low.metadata["hsa_qualified"] is True
    assert below_min.metadata["hsa_qualified"] is False
    assert below_min.eligible is True  # still issuable, just not HSA-qualified


def test_catastrophic_plan_age_and_hardship_exemption_gate():
    young = rate_health(_bundle("Applicant age: 25. Non-smoker."), coverage_id="catastrophic_standard", product_id="catastrophic_plan", state="TX")
    old_no_exemption = rate_health(_bundle("Applicant age: 40. Non-smoker."), coverage_id="catastrophic_standard", product_id="catastrophic_plan", state="TX")
    old_with_exemption = rate_health(_bundle("Applicant age: 40. Non-smoker. Hardship exemption on file."), coverage_id="catastrophic_standard", product_id="catastrophic_plan", state="TX")
    assert young.eligible is True
    assert old_no_exemption.eligible is False
    assert old_with_exemption.eligible is True


# ---------------------------------------------------------------------------
# Breadth expansion — Family (HDHP, Extended Dependents)
# ---------------------------------------------------------------------------


def test_family_hdhp_and_extended_dependents_are_guaranteed_issue():
    sick_text = "Applicant age: 40. Household size: 4. Diabetes. Heart attack history."
    hdhp = rate_health(_bundle(sick_text + " Deductible: 3300."), coverage_id="family_hdhp_standard", product_id="family_hdhp_hsa_qualified", state="TX")
    ext = rate_health(_bundle(sick_text), coverage_id="extended_dependents_standard", product_id="family_extended_dependents", state="TX")
    assert hdhp.eligible is True
    assert ext.eligible is True


# ---------------------------------------------------------------------------
# Breadth expansion — Critical Illness (Rider, Multistage)
# ---------------------------------------------------------------------------


def test_ci_rider_requires_base_policy_referral():
    q = rate_health(_bundle("Applicant age: 40. Non-smoker. Benefit amount: 50000."), coverage_id="ci_rider_standard", product_id="critical_illness_rider", state="IL")
    assert q.metadata["outcome"] == "refer"
    assert any("base policy" in c.lower() for c in q.metadata["conditions"])


def test_ci_multistage_cheaper_than_standalone_same_benefit():
    text = "Applicant age: 45. Non-smoker. Benefit amount: 100000."
    standalone = rate_health(_bundle(text), coverage_id="ci_standalone", product_id="critical_illness_standalone", state="IL")
    multistage = rate_health(_bundle(text), coverage_id="ci_multistage_standard", product_id="critical_illness_multistage", state="IL")
    assert multistage.adjusted_premium < standalone.adjusted_premium


# ---------------------------------------------------------------------------
# Breadth expansion — Senior (Medigap HD Plan G, MA SNP)
# ---------------------------------------------------------------------------


def test_medigap_hd_plan_g_cheaper_than_standard_plan_g():
    text = "Applicant age: 66."
    standard = rate_health(_bundle(text), coverage_id="plan_g", product_id="medicare_supplement", state="TX")
    hd = rate_health(_bundle(text), coverage_id="hd_plan_g", product_id="medigap_high_deductible_plan_g", state="TX")
    assert hd.adjusted_premium < standard.adjusted_premium


def test_ma_snp_requires_qualifying_condition_or_dual_eligibility():
    with_condition = rate_health(_bundle("Applicant age: 68. Diabetes diagnosis on file."), coverage_id="snp_standard", product_id="medicare_advantage_snp", state="IL")
    without_condition = rate_health(_bundle("Applicant age: 68."), coverage_id="snp_standard", product_id="medicare_advantage_snp", state="IL")
    assert with_condition.eligible is True
    assert without_condition.eligible is False


# ---------------------------------------------------------------------------
# Breadth expansion — Group (AHP, Public Sector, Level-Funded)
# ---------------------------------------------------------------------------


def test_new_group_products_price_and_carry_distinct_conditions():
    text = "Applicant age: 35. Employee count: 20."
    ahp = rate_health(_bundle(text), coverage_id="ahp_standard", product_id="association_health_plan", state="IL")
    public_sector = rate_health(_bundle(text), coverage_id="public_sector_standard", product_id="public_sector_group_health", state="IL")
    level_funded = rate_health(_bundle(text), coverage_id="level_funded_standard", product_id="level_funded_group_health", state="IL")
    assert ahp.eligible is True and ahp.adjusted_premium > 0
    assert public_sector.eligible is True and public_sector.adjusted_premium > 0
    assert level_funded.eligible is True and level_funded.adjusted_premium > 0
    assert any("association" in c.lower() for c in ahp.metadata["conditions"])
    assert any("government" in c.lower() or "psu" in c.lower() for c in public_sector.metadata["conditions"])
    assert any("stop-loss" in c.lower() for c in level_funded.metadata["conditions"])


def test_level_funded_stop_loss_questionnaire_condition_clears_when_on_file():
    text = "Applicant age: 35. Employee count: 20."
    without_q = rate_health(_bundle(text), coverage_id="level_funded_standard", product_id="level_funded_group_health", state="IL")
    with_q = rate_health(_bundle(text + " Stop-loss questionnaire on file."), coverage_id="level_funded_standard", product_id="level_funded_group_health", state="IL")
    assert any("stop-loss health questionnaire required" in c.lower() for c in without_q.metadata["conditions"])
    assert not any("stop-loss health questionnaire required" in c.lower() for c in with_q.metadata["conditions"])


# ---------------------------------------------------------------------------
# Breadth expansion — Top-up (Hospital Indemnity), Personal Accident (Standalone AD&D)
# ---------------------------------------------------------------------------


def test_hospital_indemnity_prices_off_daily_benefit_not_deductible():
    q = rate_health(_bundle("Applicant age: 45. Benefit amount: 200. Bank account details on file."), coverage_id="hospital_indemnity_standard", product_id="hospital_indemnity", state="IL")
    assert q.eligible is True
    assert q.metadata["daily_benefit_amount"] == 200.0
    assert q.metadata["payout_structure"] == "fixed_daily_cash"


def test_standalone_add_cheaper_than_full_add():
    text = "Applicant age: 35. Occupation: office clerk. Benefit amount: 500000. Nominee: spouse."
    full = rate_health(_bundle(text), coverage_id="individual", product_id="add_accident_indemnity", state="IL")
    standalone = rate_health(_bundle(text), coverage_id="standalone_add_standard", product_id="standalone_add", state="IL")
    assert standalone.adjusted_premium < full.adjusted_premium


# ---------------------------------------------------------------------------
# Breadth expansion — Disability (PTD, PPD)
# ---------------------------------------------------------------------------


def test_ptd_ppd_are_lump_sum_not_income_replacement():
    text = "Applicant age: 40. Occupation: office clerk. Medical fitness certificate on file. Benefit amount: 100000."
    ptd = rate_health(_bundle(text), coverage_id="ptd_standard", product_id="disability_ptd", state="IL")
    ppd = rate_health(_bundle(text), coverage_id="loss_of_one_limb", product_id="disability_ppd", state="IL")
    assert ptd.eligible is True
    assert ptd.metadata["benefit_type"] == "permanent_total_disability"
    assert ppd.eligible is True
    assert ppd.metadata["schedule_key"] == "loss_of_one_limb"
    assert ppd.adjusted_premium < ptd.adjusted_premium  # partial schedule payout is cheaper than total
