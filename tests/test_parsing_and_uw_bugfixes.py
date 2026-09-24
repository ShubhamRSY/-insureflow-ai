"""Regression tests for the Health/Life audit bug fixes (shared parsers + underwriting gates)."""

from __future__ import annotations

import pytest

from insureflow.health.lobs import resolve_logic_path
from insureflow.health.lobs.base import _extract_sex, _extract_tobacco
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.personal.health_rating import _household_members, rate_health
from insureflow.rating.personal.life_rating import rate_life
from insureflow.underwriting.general_uw import _claims_severity, _scaled_money
from insureflow.underwriting.health_uw import _declares_severe_condition, _is_pregnant, _occupation_class
from insureflow.underwriting.life_medical import underwrite_life
from insureflow.underwriting.personal_lines import (
    age_from_dob,
    annual_income,
    applicant_age,
    detect_sex,
    detect_tobacco,
    extract_life_factors,
    normalize_state,
)


def _b(text: str) -> SubmissionBundle:
    return SubmissionBundle(bundle_id="t", unstructured=[UnstructuredSubmission(submission_id="d0", source="a.md", raw_text=text, document_type="supplemental")])


# ── group / household counts ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,want",
    [
        ("total covered employees: 200", 200),
        ("total covered employees across all members: 180", 180),
        ("group size: 200 lives", 200),
        ("200 employees enrolled", 200),
        ("covered lives: 200", 200),
        ("employee count: 10000", 10000),
        ("employee count: 25000", 25000),
        ("number of employees: 1,200", 1200),
        ("headcount: 150", 150),
        ("eligible employees: 200", 200),
        ("number of dependents: 0", 1),
        ("number of dependents: 2", 3),
        ("household size: 2", 2),
        ("dependents: 3", 4),
    ],
)
def test_household_members(text: str, want: int) -> None:
    assert _household_members(text) == want


def test_200_life_group_is_not_priced_as_one_life() -> None:
    one = rate_health(_b("Applicant age: 42."), product_id="association_health_plan", state="TX").metadata["illustrated_adjusted_premium"]
    grp = rate_health(_b("Applicant age: 42. Total covered employees: 200"), product_id="association_health_plan", state="TX").metadata["illustrated_adjusted_premium"]
    assert grp > one * 100


# ── sex / tobacco / age / income ────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,want",
    [
        ("Sex: Male. Spouse sex: female.", "male"),
        ("Spouse sex: female\nSex: male", "male"),
        ("Gender: F", "female"),
        ("Sex: M", "male"),
        ("Beneficiary: Wife (female)\nSex: male", "male"),
    ],
)
def test_detect_sex_prefers_the_applicant(text: str, want: str) -> None:
    assert detect_sex(text.lower()) == want
    assert _extract_sex(text) == want


@pytest.mark.parametrize(
    "text,want",
    [
        ("Smoker: Yes.", True),
        ("Tobacco use: Yes", True),
        ("Smoker - Yes", True),
        ("Do you smoke? Yes", True),
        ("Current smoker.", True),
        ("Tobacco: cigars", True),
        ("Non-smoker.", False),
        ("Smoker: No", False),
        ("Smoker: Never", False),
        ("Smoker: N", False),
        ("Smoker: False", False),
        ("Tobacco: none", False),
        ("Current smoker: No", False),
        ("Non-smoker: yes", False),
        ("Spouse is a current smoker. Applicant is a non-smoker.", False),
        ("Spouse smoker: yes\nSmoker: no", False),
    ],
)
def test_detect_tobacco(text: str, want: bool) -> None:
    assert detect_tobacco(text.lower()) is want
    assert _extract_tobacco(text) is want


def test_smoker_yes_prices_like_current_smoker() -> None:
    a = rate_health(_b("Applicant age: 58. Sex: male. Smoker: Yes."), product_id="off_exchange_major_medical", state="CA")
    b = rate_health(_b("Applicant age: 58. Sex: male. Current smoker."), product_id="off_exchange_major_medical", state="CA")
    assert a.metadata["illustrated_adjusted_premium"] == b.metadata["illustrated_adjusted_premium"]


@pytest.mark.parametrize(
    "text,want",
    [
        ("Coverage: 500,000\nApplicant age: 40", 40),
        ("Percentage: 20\nApplicant age: 45", 45),
        ("Spouse age: 42\nApplicant age: 45", 45),
        ("Age last birthday: 45", 45),
        ("Aged 45", 45),
        ("Applicant is a 45-year-old", 45),
        ("45 y/o", 45),
        ("Age 34. Sum insured 500000.", 34),
        ("Benefit to age 65. Applicant age: 40", 40),
        ("Applicant age: 0", 0),
    ],
)
def test_applicant_age(text: str, want: int) -> None:
    assert applicant_age(text.lower(), "applicant age") == want


def test_age_from_dob_formats() -> None:
    for dob in ("03/02/1980", "1980-03-02", "March 2, 1980", "2 March 1980", "2-Mar-1980"):
        assert age_from_dob(dob) is not None and 40 <= age_from_dob(dob) <= 50, dob


@pytest.mark.parametrize(
    "text,want",
    [
        ("Annual income: 480000", 480000.0),
        ("Monthly income: $40,000", 480000.0),
        ("Salary: $6,000/month", 72000.0),
        ("Income: $7,000 per month", 84000.0),
        ("Spouse annual income: 60,000\nAnnual income: 90,000", 90000.0),
        ("Annual household income: 200,000\nAnnual income: 90,000", 90000.0),
    ],
)
def test_annual_income(text: str, want: float) -> None:
    assert annual_income(text.lower()) == want


def test_state_names_are_not_truncated() -> None:
    assert normalize_state("New York") == "NY"
    assert normalize_state("Texas") == "TX"
    assert normalize_state(" tx ") == "TX"
    assert normalize_state("ZZ") == "ZZ"
    assert normalize_state("Gondor") == ""
    assert normalize_state(None) == ""


# ── routing ─────────────────────────────────────────────────────────────────


def test_off_exchange_free_text_routes_to_off_exchange() -> None:
    assert (resolve_logic_path(None, None, "Off-Exchange Gold Major Medical") or "").endswith("off_exchange_major_medical")
    assert (resolve_logic_path(None, None, "Gold Marketplace Plan") or "").endswith("bronze_silver_plans")


# ── health underwriting gates ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,want",
    [
        ("Medical history: stroke and dialysis", True),
        ("Diagnosed with metastatic cancer, on chemotherapy, recent heart attack.", True),
        ("no history of cancer.", False),
        ("Cancer: No\nStroke: No", False),
        ("Cancer-free since 2015", False),
        ("HIV negative", False),
        ("Dialysis: n/a", False),
        ("Free from cancer", False),
        ("archive of records", False),
    ],
)
def test_severe_condition_detection(text: str, want: bool) -> None:
    assert _declares_severe_condition(text.lower()) is want


def _medigap(text: str, state: str = "TX") -> object:
    return rate_health(_b(f"Applicant age: 68. Plan G. {text}"), product_id="medicare_supplement", coverage_id="plan_g", state=state)


def test_medigap_outside_window_declines_declared_severe_condition() -> None:
    assert _medigap("Medical history: stroke and dialysis\nBeneficiary spouse: Jane").metadata["outcome"] == "decline"
    assert _medigap("Diagnosed with metastatic cancer, on chemotherapy.").metadata["outcome"] == "decline"


def test_medigap_outside_window_does_not_decline_negated_history() -> None:
    assert _medigap("Cancer: No\nStroke: No").metadata["outcome"] != "decline"
    assert _medigap("Applicant reports no history of cancer.").metadata["outcome"] != "decline"


def test_medigap_continuous_gi_state_never_declines_on_condition() -> None:
    assert _medigap("Diagnosed with stage 4 cancer.", state="New York").metadata["outcome"] != "decline"


@pytest.mark.parametrize(
    "text,want",
    [
        ("Occupation: commercial roofer", "IV"),
        ("Occupation: ironworker on high-rise construction", "IV"),
        ("Occupation: commercial logger", "IV"),
        ("Occupation: office worker", "I"),
        ("Occupation: accountant\nSpouse: Jane, roofer", "I"),
        ("This information is used for determining eligibility.", ""),
        ("Reviewed by a blogger. Examining records.", ""),
        ("Photo ID: driver license", ""),
        ("Occupation: police officer. Mailed to post office box.", ""),
        ("Occupation: mechanical engineer", ""),
        ("Occupation: long-haul driver", "III"),
    ],
)
def test_occupation_class_whole_words(text: str, want: str) -> None:
    assert _occupation_class(text.lower()) == want


def test_ad_and_d_flags_unrecognized_occupation_for_referral() -> None:
    q = rate_health(_b("Applicant age: 40. Occupation: sommelier. Principal sum: 500000"), product_id="add_accident_indemnity", state="TX")
    assert any("not recognized" in c for c in q.metadata["conditions"])
    q = rate_health(_b("Applicant age: 40. Occupation: commercial roofer. Principal sum: 500000"), product_id="add_accident_indemnity", state="TX")
    assert q.metadata["occupation_class"] == "IV"


@pytest.mark.parametrize(
    "text,want",
    [
        ("Pregnant: No", False),
        ("Pregnancy: none", False),
        ("Denies pregnancy", False),
        ("Never been pregnant", False),
        ("no longer pregnant", False),
        ("LMP: N/A", False),
        ("Spouse is pregnant", False),
        ("Currently pregnant, 20 weeks gestation", True),
    ],
)
def test_is_pregnant(text: str, want: bool) -> None:
    assert _is_pregnant(text.lower()) is want


def test_aca_plan_never_refers_for_a_missing_health_declaration() -> None:
    q = rate_health(_b("Applicant age: 40. Photo ID, proof of address, health application on file."), product_id="aca_marketplace_plan", state="TX")
    assert q.metadata["underwriting"]["gates"].get("medical_declaration") != "fail"


def test_family_plan_without_spouse_is_not_asked_for_a_marriage_certificate() -> None:
    q = rate_health(_b("Applicant age: 40. Household size: 3. Single parent with children."), product_id="family_health_plan", state="TX")
    assert q.metadata["underwriting"]["gates"].get("spouse_relationship") != "fail"


def test_stldi_declines_declared_severe_condition_but_not_clean_applicant() -> None:
    sick = rate_health(_b("Applicant age: 40. Cancer diagnosis current, dialysis. Salary slip attached."), product_id="short_term_limited_duration", state="TX")
    clean = rate_health(_b("Applicant age: 40. Salary slip attached."), product_id="short_term_limited_duration", state="TX")
    assert sick.metadata["outcome"] == "decline"
    assert clean.metadata["outcome"] != "decline"


# ── product logic ───────────────────────────────────────────────────────────


def test_ppd_schedule_distinguishes_finger_from_arm() -> None:
    def prem(cid: str) -> float:
        return rate_health(_b("Applicant age: 40. Principal sum: 5000000"), product_id="disability_ppd", coverage_id=cid, state="TX").metadata["illustrated_adjusted_premium"]

    finger, thumb, hand, limb, two = prem("loss_of_finger"), prem("loss_of_thumb"), prem("loss_of_hand"), prem("loss_of_one_limb"), prem("loss_of_two_limbs")
    assert finger < thumb < hand == limb < two


def test_public_sector_group_gets_the_size_discount_like_large_group() -> None:
    def pepm(pid: str) -> float:
        return rate_health(_b("Applicant age: 50. Employee count: 400"), product_id=pid, state="NY").metadata["per_employee_monthly"]

    assert abs(pepm("public_sector_group_health") - pepm("large_group_health")) < 5.0


def test_ltd_flags_benefit_above_issue_limit_and_annualizes_monthly_income() -> None:
    q = rate_health(_b("Applicant age: 45. Monthly income: 100000. Monthly benefit: 50000"), product_id="long_term_disability", state="TX")
    assert any("maximum issue limit" in c for c in q.metadata["conditions"])
    ok = rate_health(_b("Applicant age: 45. Monthly income: 40000. Monthly benefit: 20000"), product_id="long_term_disability", state="TX")
    assert not any("ceiling" in c for c in ok.metadata["conditions"])


def test_ltd_periods_ignore_unrelated_year_and_day_text() -> None:
    from insureflow.health.lobs.disability.long_term_disability import _benefit_period, _elimination_days

    assert _benefit_period("applicant is a 45-year-old") == "2_year"
    assert _benefit_period("benefit period: 5 years") == "5_year"
    assert _elimination_days("180-day elimination period") == 180
    assert _elimination_days("elimination period: 180-day") == 180


# ── general parsers ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,want",
    [("sum insured: $1.5M", 1_500_000), ("sum insured: 2 M", 2_000_000), ("sum insured: 500000 credit", 500_000), ("sum insured: 5 crore", 5e7), ("sum insured: USD 500,000", 500_000)],
)
def test_scaled_money(text: str, want: float) -> None:
    assert _scaled_money(text, "sum insured") == want


@pytest.mark.parametrize("text", ["No claims in the last 5 years", "claim free", "Claims: none", "Claim form attached"])
def test_clean_claims_history_is_not_a_claim(text: str) -> None:
    assert _claims_severity(text.lower()) is None


# ── life ────────────────────────────────────────────────────────────────────


def test_life_applicant_sex_not_overridden_by_spouse() -> None:
    f = extract_life_factors(_b("Applicant age: 45. Sex: Male. Face amount: $500000. Spouse sex: female."))
    assert f.sex == "male"


def test_life_smoker_yes_is_priced_as_smoker_and_smoker_no_is_not() -> None:
    base = "Applicant age: 45. Sex: male. Face amount: $500000. Income: 150000."
    yes = rate_life(_b(base + " Smoker: Yes."), coverage_id="level_term_20", state="IL")
    no = rate_life(_b(base + " Smoker: No."), coverage_id="level_term_20", state="IL")
    assert yes.adjusted_premium > no.adjusted_premium * 1.5
    assert underwrite_life(_b(base + " Current smoker: No.")).tobacco is False


@pytest.mark.parametrize(
    "wording",
    [
        "Organ transplant: No",
        "Chemotherapy: No",
        "HIV positive: No",
        "Suicide attempt: None",
        "Applicant reports no history of cancer or chemotherapy",
        "Mother received chemotherapy in 2015",
        "Uses hearing aids",
    ],
)
def test_life_negated_or_relative_history_does_not_decline(wording: str) -> None:
    d = underwrite_life(_b(f"Face amount: $500000. Applicant age: 42. {wording}."))
    assert d.decision.value != "decline", wording


def test_life_affirmative_disclosure_still_declines() -> None:
    assert underwrite_life(_b("Face amount: $500000. Applicant age: 42. Active cancer, on chemotherapy.")).decision.value == "decline"


def test_life_negated_avocations_add_no_flat_extra() -> None:
    d = underwrite_life(_b("Face amount: $500000. Applicant age: 42. No scuba, no skydiving. Denies aviation."))
    assert d.flat_extras_per_1000 == 0.0


def test_life_face_amount_ignores_in_force_coverage() -> None:
    f = extract_life_factors(_b("In-force face amount: $250,000\nFace amount requested: $500,000\nApplicant age: 45"))
    assert f.face_amount == 500_000
    f = extract_life_factors(_b("Existing coverage amount: $100,000\nCoverage amount: $500,000\nApplicant age: 45"))
    assert f.face_amount == 500_000


def test_life_age_zero_is_not_rewritten_and_dob_derives_age() -> None:
    assert extract_life_factors(_b("Applicant age: 0. Face amount: $100000")).age == 0
    assert extract_life_factors(_b("Date of birth (MM/DD/YYYY): 03/02/1980. Face amount: $100000")).age is not None


def test_life_state_names_and_labels() -> None:
    assert extract_life_factors(_b("State: Texas\nApplicant age: 40")).state == "TX"
    assert extract_life_factors(_b("State of residence: TX\nApplicant age: 40")).state == "TX"
    assert extract_life_factors(_b("Beneficiary state: FL\nState: TX\nApplicant age: 40")).state == "TX"


def test_life_preferred_provider_network_is_not_a_preferred_class() -> None:
    assert extract_life_factors(_b("Preferred provider network. Applicant age: 40")).health_class == "standard"
    assert extract_life_factors(_b("Preferred risk class. Applicant age: 40")).health_class == "preferred"


# ── life product logic ──────────────────────────────────────────────────────


@pytest.mark.parametrize("pid", ["pure_endowment", "full_endowment", "guaranteed_fixed_endowment"])
def test_endowment_term_is_read_from_the_submission(pid: str) -> None:
    base = "Applicant age: 45. Sex: male. Face amount: $400000. Income: 200000. Non-smoker."
    q10 = rate_life(_b(base + " Term to maturity: 10 years."), product_id=pid, state="IL")
    q25 = rate_life(_b(base + " Term to maturity: 25 years."), product_id=pid, state="IL")
    assert (q10.metadata["term_years"], q25.metadata["term_years"]) == (10, 25)
    assert q10.metadata["illustrated_adjusted_premium"] > q25.metadata["illustrated_adjusted_premium"]


def test_annuity_below_minimum_purchase_is_ineligible() -> None:
    q = rate_life(_b("Applicant age: 68. Sex: male. Purchase price: $1. Income: 100000"), product_id="immediate_annuity", state="NY")
    assert q.eligible is False and any("minimum" in r for r in q.ineligibility_reasons)
    assert rate_life(_b("Applicant age: 68. Sex: male. Purchase price: $500000."), product_id="immediate_annuity", state="NY").eligible is True


def test_whole_life_cash_value_is_never_negative() -> None:
    from insureflow.life.whole_life_formulas import compute_full_whole_life_quote

    assert min(compute_full_whole_life_quote(age=45, sex="male", smoker=False, face_amount=500000).cash_values) >= 0.0


def test_graded_whole_life_survives_unfiled_null_manual_values() -> None:
    from insureflow.rating.personal.manuals import life_manual

    man = life_manual()
    saved = (man.get("whole_life_interest_rate"), man.get("whole_life_expense_loading"))
    man["whole_life_interest_rate"] = man["whole_life_expense_loading"] = None
    try:
        q = rate_life(_b("Applicant age: 70. Sex: male. Face amount: $50000. Diabetes and prior heart attack."), product_id="graded_guaranteed_issue_whole_life", state="IL")
    finally:
        man["whole_life_interest_rate"], man["whole_life_expense_loading"] = saved
    assert q.metadata.get("lob_dispatch_error") is None
    assert q.metadata["outcome"] != "decline"  # guaranteed issue: the buyer it exists for is not medically declined


def test_life_shared_helpers_tolerate_explicit_null_manual_values() -> None:
    from types import SimpleNamespace

    from insureflow.life.lobs.base import band_factor, medical_class_factor, policy_fee

    ctx = SimpleNamespace(
        manual={"underwriting_class_factors": {"preferred": None, "standard": 1.0}, "policy_fee": None, "band_discounts": [{"min_face": 0, "factor": None}]},
        medical=SimpleNamespace(underwriting_class="preferred"),
        face=100_000,
    )
    assert medical_class_factor(ctx) == 1.0 and policy_fee(ctx) == 60.0 and band_factor(ctx) == 1.0  # type: ignore[arg-type]


def test_unknown_state_is_reported_as_carrier_default_and_medigap_tables_are_complete() -> None:
    from insureflow.health.lobs.state_law import MEDIGAP_BIRTHDAY_RULE_STATES, MEDIGAP_COMMUNITY_RATED_STATES, canonical_state_row

    assert canonical_state_row("ZZ") == {}
    assert {"KY", "MD", "OK"} <= MEDIGAP_BIRTHDAY_RULE_STATES
    assert "MA" in MEDIGAP_COMMUNITY_RATED_STATES


# ── health rating entry point (sweep findings) ──────────────────────────────


def _prem(text: str, pid: str, **kw: str) -> float:
    return rate_health(_b(text), product_id=pid, state=kw.pop("state", "TX"), **kw).metadata["illustrated_adjusted_premium"]


@pytest.mark.parametrize("age_text", ["", "Applicant age: forty.", "Applicant age: -5.", "Applicant age: 130."])
def test_undeclared_or_unreadable_age_is_not_silently_rated_as_40(age_text: str) -> None:
    q = rate_health(_b(f"Sex: male. {age_text}"), product_id="aca_marketplace_plan", coverage_id="silver", state="TX")
    assert q.eligible is False and q.adjusted_premium == 0.0
    assert any("age not declared" in r for r in q.ineligibility_reasons)


def test_group_without_a_census_count_is_not_priced_as_one_life() -> None:
    q = rate_health(_b("Applicant age: 45."), product_id="large_group_health", state="TX")
    assert q.eligible is False and any("count not declared" in r for r in q.ineligibility_reasons)
    assert rate_health(_b("Applicant age: 45. Employee count: 200."), product_id="large_group_health", state="TX").eligible is True


def test_monthly_modal_premium_is_a_twelfth_of_annual() -> None:
    q = rate_health(_b("Applicant age: 40. Monthly premium."), product_id="aca_marketplace_plan", coverage_id="silver", state="TX")
    assert q.metadata["modal"] == "monthly"
    assert q.metadata["modal_premium"] == pytest.approx(q.metadata["illustrated_adjusted_premium"] / 12, abs=0.01)


def test_each_product_reads_its_own_benefit_label() -> None:
    assert _prem("Applicant age: 45. Daily benefit amount: $200. Sum insured: $10,000.", "hospital_indemnity") == _prem("Applicant age: 45. Daily benefit amount: $200.", "hospital_indemnity")
    assert _prem("Applicant age: 32. Weekly benefit: $600. Monthly benefit: $2,600.", "short_term_disability") == _prem("Applicant age: 32. Weekly benefit: $600.", "short_term_disability")
    assert _prem("Applicant age: 35. Deductible: $5,000. Sum insured: $500,000.", "supplemental_gap_coverage") == _prem("Applicant age: 35. Deductible: $5,000.", "supplemental_gap_coverage")
    assert _prem("Applicant age: 45. Sex: female. Lump sum: $50,000. Benefit amount: $1,000.", "critical_illness_standalone") == _prem(
        "Applicant age: 45. Sex: female. Lump sum: $50,000.", "critical_illness_standalone"
    )
    only_ded = rate_health(_b("Applicant age: 45. Sex: female. Deductible: $2,500."), product_id="critical_illness_standalone", state="TX")
    assert only_ded.eligible is False  # a deductible is not a CI lump sum


def test_absurd_benefit_is_ineligible() -> None:
    for pid, text in (("critical_illness_standalone", "Sex: male. Lump sum: $10,000,000,000"), ("long_term_disability", "Monthly income: 100000. Monthly benefit: 10000000000")):
        q = rate_health(_b(f"Applicant age: 45. {text}"), product_id=pid, state="TX")
        assert q.eligible is False and q.adjusted_premium == 0.0


def test_refer_conditions_set_the_refer_outcome() -> None:
    q = rate_health(_b("Applicant age: 40. Occupation: sommelier. Principal sum: 500000. Photo ID, proof of address, health application."), product_id="add_accident_indemnity", state="TX")
    assert q.metadata["outcome"] == "refer"


def test_blank_state_is_flagged_and_unknown_sex_on_ci_is_flagged() -> None:
    q = rate_health(_b("Applicant age: 40."), product_id="aca_marketplace_plan", coverage_id="silver", state="")
    assert any("Issue state not provided" in c for c in q.metadata["conditions"])
    ci = rate_health(_b("Applicant age: 45. Lump sum: $50,000."), product_id="critical_illness_standalone", state="TX")
    assert any("Sex not stated" in c for c in ci.metadata["conditions"])


def test_ltd_premium_never_rises_with_a_longer_elimination_period() -> None:
    def prem(days: int) -> float:
        return _prem(f"Applicant age: 45. Monthly benefit: 5000. Elimination period: {days} days. Benefit period: 5 years", "long_term_disability")

    series = [prem(d) for d in (0, 7, 14, 30, 45, 60, 90, 120, 180, 365)]
    assert all(a >= b for a, b in zip(series, series[1:], strict=False)), series


@pytest.mark.parametrize("label,want", [("lifetime", "to_65"), ("to age 67", "to_65"), ("1 year", "2_year"), ("5 years", "5_year")])
def test_ltd_benefit_period_labels(label: str, want: str) -> None:
    q = rate_health(_b(f"Applicant age: 45. Monthly benefit: 5000. Benefit period: {label}"), product_id="long_term_disability", state="TX")
    assert q.metadata["benefit_period"] == want


def test_std_unfiled_elimination_period_is_not_priced_as_the_default() -> None:
    def prem(days: int) -> float:
        return _prem(f"Applicant age: 32. Weekly benefit: $600. Elimination period: {days} days.", "short_term_disability")

    assert prem(60) == prem(30) and prem(30) < prem(14)


def test_every_catalog_coverage_id_resolves_to_its_own_product() -> None:
    from insureflow.health.lobs import resolve_product_id
    from insureflow.insurance.health_lobs import HEALTH_LINES

    for line in HEALTH_LINES:
        for cv in line["coverages"]:
            assert resolve_product_id(None, cv["id"], cv["name"]) == line["id"], (line["id"], cv["id"])


@pytest.mark.parametrize(
    "name,want",
    [
        ("Golden Care", None),
        ("Bronzeville", None),
        ("Medicare Advantage Gold", "medicare_advantage"),
        ("Platinum Medigap Plan G", "medicare_supplement"),
        ("Family Silver", "family_health_plan"),
        ("HSA Gold", "hdhp_hsa_qualified"),
        ("Standard Critical Illness Rider", "critical_illness_rider"),
        ("Multi-Stage Critical Illness", "critical_illness_multistage"),
        ("Family Plan — Extended Dependent Coverage", "family_extended_dependents"),
    ],
)
def test_free_text_routing_uses_word_boundaries_and_specific_first(name: str, want: str | None) -> None:
    from insureflow.health.lobs import resolve_product_id

    assert resolve_product_id(None, None, name) == want
