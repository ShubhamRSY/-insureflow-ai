"""Issue gates for the pilot exhibits added on top of existing actuarial premiums.

Endowment, money-back, and no-lapse GUL may book a premium only when the
filing state, evidence, age, and income gates all still pass. A decline set
earlier must stay a decline, and the contract premium must stay zero.
"""

from __future__ import annotations

import pytest

from insureflow.life.endowment_uw import run_endowment_uw
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.personal.life_rating import rate_life

AFFORDABLE = "Face amount: $100000. Annual income: 250000. Applicant age: 40. Sex: female. Non-smoker. Preferred."
POOR = "Face amount: $400000. Annual income: 20000. Applicant age: 35. Sex: female. Non-smoker."


def _bundle(text: str) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="gate-test",
        unstructured=[UnstructuredSubmission(submission_id="d0", source="app.md", raw_text=text, document_type="supplemental")],
    )


def _declined(q) -> None:
    assert q.eligible is False
    assert q.adjusted_premium == 0.0
    assert q.base_premium == 0.0
    assert q.metadata["illustrated_adjusted_premium"] > 0.0


# ---------------------------------------------------------------------------
# Endowment
# ---------------------------------------------------------------------------


def test_endowment_uw_declines_above_35_percent_of_income() -> None:
    refer = run_endowment_uw(age=40, annual_premium=35_000, income=100_000, term_years=20, face_amount=100_000)
    decline = run_endowment_uw(age=40, annual_premium=36_000, income=100_000, term_years=20, face_amount=100_000)
    approve = run_endowment_uw(age=40, annual_premium=10_000, income=100_000, term_years=20, face_amount=100_000)
    assert refer.premium_to_income_pct == 35.0
    assert refer.decision != "DECLINE"
    assert decline.premium_to_income_pct == 36.0
    assert decline.decision == "DECLINE"
    assert approve.decision == "APPROVE"


@pytest.mark.parametrize(
    "product_id,coverage_id",
    [
        ("pure_endowment", "pure_maturity"),
        ("full_endowment", "with_profit"),
        ("guaranteed_fixed_endowment", "fixed_endowment"),
    ],
)
def test_endowment_issues_in_il_and_declines_on_the_gates(product_id: str, coverage_id: str) -> None:
    issued = rate_life(_bundle(AFFORDABLE), coverage_id=coverage_id, product_id=product_id, state="IL")
    assert issued.eligible is True, issued.ineligibility_reasons
    assert issued.adjusted_premium > 0
    assert issued.metadata["rating_engine"] == "life_filing"
    assert issued.metadata["filed_endowment"] is True
    assert issued.metadata["filing_id"] == "RYT-LIFE-END-2026-01"
    assert issued.metadata["serff_tracking"] == "RYT-LIFE-END-2026-001"

    poor = rate_life(_bundle(POOR), coverage_id=coverage_id, product_id=product_id, state="IL")
    _declined(poor)
    assert poor.metadata.get("filed_endowment") is not True
    assert any("Endowment UW" in r and "DECLINE" in r for r in poor.ineligibility_reasons)

    too_young = rate_life(_bundle("Applicant age: 17. " + AFFORDABLE), coverage_id=coverage_id, product_id=product_id, state="IL")
    _declined(too_young)
    assert any("outside" in r for r in too_young.ineligibility_reasons)

    unfiled = rate_life(_bundle(AFFORDABLE), coverage_id=coverage_id, product_id=product_id, state="AL")
    _declined(unfiled)
    assert any("not a AL state-of-issue filing" in r for r in unfiled.ineligibility_reasons)

    sick = rate_life(
        _bundle(AFFORDABLE + " Active cancer on chemotherapy."),
        coverage_id=coverage_id,
        product_id=product_id,
        state="IL",
    )
    _declined(sick)


def test_endowment_premium_order_and_ca_relativity() -> None:
    def prem(pid: str, cid: str, state: str = "IL") -> float:
        q = rate_life(_bundle(AFFORDABLE), coverage_id=cid, product_id=pid, state=state)
        assert q.eligible is True, (pid, state, q.ineligibility_reasons)
        return q.adjusted_premium

    pure = prem("pure_endowment", "pure_maturity")
    full = prem("full_endowment", "with_profit")
    fixed = prem("guaranteed_fixed_endowment", "fixed_endowment")
    assert pure < full < fixed
    assert prem("pure_endowment", "pure_maturity", "CA") > pure

    # Pure endowment pays only on survival, so the longer-lived sex costs more.
    female = prem("pure_endowment", "pure_maturity")
    male = rate_life(
        _bundle(AFFORDABLE.replace("Sex: female", "Sex: male")),
        coverage_id="pure_maturity",
        product_id="pure_endowment",
        state="IL",
    )
    assert male.eligible is True
    assert female > male.adjusted_premium
    full_male = rate_life(
        _bundle(AFFORDABLE.replace("Sex: female", "Sex: male")),
        coverage_id="with_profit",
        product_id="full_endowment",
        state="IL",
    )
    assert full_male.eligible is True
    assert prem("full_endowment", "with_profit") < full_male.adjusted_premium


def test_with_profit_endowment_bonus_is_not_in_the_contract_premium() -> None:
    full = rate_life(_bundle(AFFORDABLE), coverage_id="with_profit", product_id="full_endowment", state="IL")
    assert full.eligible is True
    assert full.metadata["illustrated_bonus_maturity_value"] > full.metadata["guaranteed_maturity_value"]
    assert any("NOT guaranteed" in c for c in full.metadata["conditions"])


# ---------------------------------------------------------------------------
# Money-back
# ---------------------------------------------------------------------------


def test_traditional_and_with_profit_money_back_share_the_guaranteed_premium() -> None:
    trad = rate_life(_bundle(AFFORDABLE), coverage_id="traditional_mb", product_id="traditional_money_back", state="IL")
    wp = rate_life(_bundle(AFFORDABLE), coverage_id="with_profit_mb", product_id="with_profit_money_back", state="IL")
    assert trad.eligible is True and wp.eligible is True
    assert trad.adjusted_premium == pytest.approx(wp.adjusted_premium)
    assert trad.metadata["filing_id"] == "RYT-LIFE-MB-2026-01"
    assert wp.metadata["filed_money_back"] is True
    assert wp.metadata["illustrated_bonus_pv"] > 0
    assert sum(s["pct_of_sa"] for s in trad.metadata["survival_benefit_schedule"]) == pytest.approx(1.0)

    poor = rate_life(_bundle(POOR), coverage_id="traditional_mb", product_id="traditional_money_back", state="IL")
    assert poor.metadata["survival_benefit_schedule"]
    al = rate_life(_bundle(AFFORDABLE), coverage_id="traditional_mb", product_id="traditional_money_back", state="AL")
    _declined(al)


@pytest.mark.parametrize(
    "text,eligible",
    [
        ("Applicant age: 34. Sex: male. Face amount: $100000. Annual income: 250000. Non-smoker. Preferred.", False),
        ("Applicant age: 34. Sex: male. Face amount: $100000. Annual income: 250000. Child's age: 8. Non-smoker. Preferred.", False),
        ("Applicant age: 34. Sex: male. Face amount: $100000. Annual income: 250000. Child's sex: female. Non-smoker. Preferred.", False),
        ("Applicant age: 34. Sex: male. Face amount: $100000. Annual income: 250000. Child's age: 8. Child's sex: female. Non-smoker. Preferred.", True),
        ("Applicant age: 19. Sex: male. Face amount: $100000. Annual income: 250000. Child's age: 8. Child's sex: female.", False),
    ],
)
def test_children_money_back_needs_the_child_on_the_submission(text: str, eligible: bool) -> None:
    q = rate_life(_bundle(text), coverage_id="children_mb", product_id="children_money_back", state="IL")
    assert q.eligible is eligible, q.ineligibility_reasons
    if eligible:
        assert q.adjusted_premium > 0
        assert q.metadata["filed_money_back"] is True
        assert q.metadata["actuarial"]["child_age_source"] == "submission"
        assert q.metadata["actuarial"]["child_sex_source"] == "submission"
    else:
        assert q.adjusted_premium == 0.0
        assert q.metadata.get("filed_money_back") is not True


# ---------------------------------------------------------------------------
# Guaranteed universal life
# ---------------------------------------------------------------------------


def test_gul_books_the_solved_no_lapse_premium() -> None:
    issued = rate_life(_bundle(AFFORDABLE), coverage_id="no_lapse", product_id="guaranteed_universal_life", state="IL")
    to120 = rate_life(_bundle(AFFORDABLE), coverage_id="gul_to_120", product_id="guaranteed_universal_life", state="IL")
    assert issued.eligible is True, issued.ineligibility_reasons
    assert issued.metadata["shadow_account_funding_adequate"] is True
    assert issued.metadata["shadow_account_first_negative_year"] is None
    assert issued.metadata["no_lapse_premium_solved"] is True
    assert issued.adjusted_premium > issued.metadata["formula_premium_before_solve"]
    assert issued.metadata["filing_id"] == "RYT-LIFE-GUL-2026-01"
    assert issued.metadata["filed_gul"] is True
    assert to120.eligible is True
    assert to120.adjusted_premium > issued.adjusted_premium

    # Cent-rounding used to drop the solved premium through the boundary and
    # still issue, with the shadow account negative in the last guarantee year.
    young = rate_life(
        _bundle("Applicant age: 18. Sex: female. Face amount: $100000. Annual income: 5000000. Non-smoker. Preferred."),
        coverage_id="no_lapse",
        product_id="guaranteed_universal_life",
        state="IL",
    )
    assert young.eligible is True, young.ineligibility_reasons
    assert young.metadata["shadow_account_funding_adequate"] is True
    assert young.metadata["shadow_account_first_negative_year"] is None

    smoker = rate_life(
        _bundle(AFFORDABLE.replace("Non-smoker", "Smoker")),
        coverage_id="no_lapse",
        product_id="guaranteed_universal_life",
        state="IL",
    )
    male = rate_life(
        _bundle(AFFORDABLE.replace("Sex: female", "Sex: male")),
        coverage_id="no_lapse",
        product_id="guaranteed_universal_life",
        state="IL",
    )
    assert smoker.eligible is True and male.eligible is True
    assert smoker.adjusted_premium > issued.adjusted_premium
    assert male.adjusted_premium > issued.adjusted_premium

    stretched = rate_life(
        _bundle("Face amount: $500000. Annual income: 145000. Applicant age: 42. Sex: female. Non-smoker. Preferred."),
        coverage_id="no_lapse",
        product_id="guaranteed_universal_life",
        state="IL",
    )
    _declined(stretched)
    assert stretched.metadata["shadow_account_funding_adequate"] is True
    assert stretched.metadata.get("filed_gul") is not True
    assert any("35% of documented income" in r for r in stretched.ineligibility_reasons)

    small = rate_life(_bundle(AFFORDABLE.replace("$100000", "$50000")), coverage_id="no_lapse", product_id="guaranteed_universal_life", state="IL")
    _declined(small)
    assert any("minimum face" in r for r in small.ineligibility_reasons)

    old = rate_life(_bundle(AFFORDABLE.replace("age: 40", "age: 76")), coverage_id="no_lapse", product_id="guaranteed_universal_life", state="IL")
    _declined(old)
    assert any("outside" in r for r in old.ineligibility_reasons)

    al = rate_life(_bundle(AFFORDABLE), coverage_id="no_lapse", product_id="guaranteed_universal_life", state="AL")
    _declined(al)

    sick = rate_life(
        _bundle(AFFORDABLE + " Active cancer on chemotherapy."),
        coverage_id="no_lapse",
        product_id="guaranteed_universal_life",
        state="IL",
    )
    _declined(sick)
    assert sick.metadata.get("filed_gul") is not True


@pytest.mark.parametrize(
    "product_id,coverage_id,needle",
    [
        ("current_assumption_universal_life", "current_rate", "current assumption universal life"),
        ("indexed_universal_life", "indexed_account", "indexed universal life"),
        ("variable_universal_life", "gmdb", "variable universal life"),
    ],
)
def test_other_universal_life_stays_illustrative(product_id: str, coverage_id: str, needle: str) -> None:
    q = rate_life(_bundle(AFFORDABLE), coverage_id=coverage_id, product_id=product_id, state="IL")
    _declined(q)
    assert any(needle in r for r in q.ineligibility_reasons)
    assert q.metadata.get("filed_gul") is not True


@pytest.mark.parametrize("age", [18, 42])
@pytest.mark.parametrize("coverage_id", ["no_lapse", "gul_to_120"])
def test_gul_solved_premium_funds_the_ages_that_used_to_round_through(age: int, coverage_id: str) -> None:
    q = rate_life(
        _bundle(f"Applicant age: {age}. Sex: male. Face amount: $100000. Annual income: 5000000. Smoker."),
        coverage_id=coverage_id,
        product_id="guaranteed_universal_life",
        state="IL",
    )
    assert q.eligible is True, (age, coverage_id, q.ineligibility_reasons)
    assert q.metadata["shadow_account_funding_adequate"] is True
    assert q.metadata["shadow_account_first_negative_year"] is None
    assert q.adjusted_premium > q.metadata["formula_premium_before_solve"]
    assert q.metadata["filed_gul"] is True


def test_gul_age_75_smoker_cannot_fund_inside_the_face() -> None:
    smoker = rate_life(
        _bundle("Applicant age: 75. Sex: male. Face amount: $100000. Annual income: 5000000. Smoker."),
        coverage_id="no_lapse",
        product_id="guaranteed_universal_life",
        state="IL",
    )
    assert smoker.eligible is False
    assert smoker.adjusted_premium == 0.0
    assert smoker.metadata.get("filed_gul") is not True
    assert any("at or below the face amount" in r for r in smoker.ineligibility_reasons)
    nonsmoker = rate_life(
        _bundle("Applicant age: 75. Sex: female. Face amount: $100000. Annual income: 5000000. Non-smoker. Preferred."),
        coverage_id="no_lapse",
        product_id="guaranteed_universal_life",
        state="IL",
    )
    assert nonsmoker.eligible is True, nonsmoker.ineligibility_reasons
    assert nonsmoker.metadata["shadow_account_first_negative_year"] is None


# ---------------------------------------------------------------------------
# QLAC
# ---------------------------------------------------------------------------


def test_qlac_deferral_gates() -> None:
    male = rate_life(
        _bundle("Purchase price: $200000. Applicant age: 60. Sex: male."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="IL",
    )
    female = rate_life(
        _bundle("Purchase price: $200000. Applicant age: 60. Sex: female."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="IL",
    )
    assert male.eligible is True and female.eligible is True
    assert male.metadata["years_of_deferral"] == 15
    assert female.metadata["annual_payout_at_start"] < male.metadata["annual_payout_at_start"]
    spot = male.metadata["purchase_price"] / male.metadata["actuarial"]["annuity_factor_at_start"]
    assert male.metadata["annual_payout_at_start"] > spot

    later = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 75. Sex: male."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="IL",
    )
    assert later.eligible is True, later.ineligibility_reasons
    assert later.metadata["years_of_deferral"] == 0
    assert later.metadata["income_start_age"] == 75
    too_old = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 78. Sex: male."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="IL",
    )
    assert too_old.eligible is False
    assert any("outside 50-75" in r for r in too_old.ineligibility_reasons)
    assert later.metadata["annual_payout_at_start"] == pytest.approx(
        later.metadata["purchase_price"] / later.metadata["actuarial"]["annuity_factor_at_start"],
        rel=0.001,
    )

    young = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 40. Sex: male."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="IL",
    )
    _declined(young)
    assert any("outside" in r for r in young.ineligibility_reasons)

    small = rate_life(
        _bundle("Purchase price: $5000. Applicant age: 60. Sex: male."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="IL",
    )
    assert small.eligible is False
    assert small.adjusted_premium == 0.0
    assert any("below the $10,000 minimum" in r for r in small.ineligibility_reasons)

    over = rate_life(
        _bundle("Purchase price: $400000. Applicant age: 60. Sex: male."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="IL",
    )
    assert over.eligible is False
    assert over.metadata["purchase_price"] == 210_000.0
    assert over.metadata.get("filed_annuity") is not True
    assert any("IRS QLAC cap" in r for r in over.ineligibility_reasons)

    missing = rate_life(
        _bundle("Applicant age: 60. Sex: male."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="IL",
    )
    assert missing.eligible is False
    assert missing.metadata["purchase_price"] == 0.0
    assert missing.metadata["illustrated_adjusted_premium"] == 0.0
    assert any("not on the submission" in r for r in missing.ineligibility_reasons)

    al = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 60. Sex: male."),
        coverage_id="qlac_lifetime",
        product_id="qlac",
        state="AL",
    )
    _declined(al)
    assert any("not a AL state-of-issue filing" in r for r in al.ineligibility_reasons)


# ---------------------------------------------------------------------------
# Structured settlement
# ---------------------------------------------------------------------------


def test_structured_settlement_explicit_zero_beats_a_stated_purchase_price() -> None:
    zero = rate_life(
        _bundle("Structured settlement: $0 per month for 20 years. Purchase price: $500000. Claimant age: 34."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    assert zero.eligible is False
    assert zero.metadata.get("filed_annuity") is not True
    assert any("schedule is zero" in r for r in zero.ineligibility_reasons)
    assert zero.metadata["present_value_of_settlement"] == pytest.approx(0.0)
    assert zero.metadata["monthly_payment"] == pytest.approx(0.0)
    assert zero.metadata["illustrated_adjusted_premium"] == pytest.approx(0.0)

    stated = rate_life(
        _bundle("$2500 per month for 20 years settlement. Purchase price: $500000."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    assert stated.eligible is True, stated.ineligibility_reasons
    assert stated.metadata["schedule_source"] == "submission"
    assert stated.metadata["filed_annuity"] is True
    assert stated.metadata["monthly_payment"] == pytest.approx(2500.0)
    assert stated.adjusted_premium == pytest.approx(stated.metadata["present_value_of_settlement"])
    assert any("qualified assignment" in c.lower() for c in stated.metadata["conditions"])

    fallback = rate_life(
        _bundle("Purchase price: $120000. Applicant age: 50. Sex: male."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    assert fallback.eligible is False
    assert fallback.metadata["schedule_source"] == "assumed"
    assert fallback.metadata.get("filed_annuity") is not True
    assert any("assumed stream" in r for r in fallback.ineligibility_reasons)
    assert fallback.metadata["present_value_of_settlement"] > 0
    assert fallback.metadata["monthly_payment"] > 0
    no_term = rate_life(
        _bundle("$2500 per month settlement."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    assert no_term.eligible is False
    assert no_term.metadata["schedule_source"] == "assumed"
    tiny = rate_life(
        _bundle("$100 per month for 2 years settlement."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    assert tiny.eligible is False
    assert any("below the $25,000 minimum" in r for r in tiny.ineligibility_reasons)

    payments = rate_life(
        _bundle("$2000 per month for 18 payments."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    by_years = rate_life(
        _bundle("$2500 per month for 240 payments."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    assert payments.eligible is True, payments.ineligibility_reasons
    assert payments.metadata["term_months"] == 18
    v = 1.0 / (1.0 + 0.04 / 12.0)
    expected_18 = 2000 * (1.0 - v**18) / (0.04 / 12.0)
    assert payments.adjusted_premium == pytest.approx(expected_18, rel=0.001)
    assert by_years.eligible is True
    assert by_years.adjusted_premium == pytest.approx(stated.adjusted_premium, rel=0.001)
    lump = rate_life(
        _bundle("$2500 per month for 20 years settlement."),
        coverage_id="structured_lump",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    assert lump.eligible is True
    assert lump.adjusted_premium == pytest.approx(stated.adjusted_premium)
    assert lump.metadata["commuted_lump_pv"] == pytest.approx(stated.metadata["present_value_of_settlement"])

    child = rate_life(
        _bundle("$2000 per month for 10 years. Claimant age: 10."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="IL",
    )
    assert child.eligible is True, child.ineligibility_reasons

    al = rate_life(
        _bundle("$2500 per month for 20 years settlement."),
        coverage_id="structured_payments",
        product_id="structured_settlement_annuity",
        state="AL",
    )
    assert al.eligible is False
    assert al.adjusted_premium == 0.0
    assert al.metadata.get("filed_annuity") is not True
    assert any("not a AL state-of-issue filing" in r for r in al.ineligibility_reasons)


def test_annuity_past_75_issues_and_cancer_still_declines() -> None:
    healthy = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 80. Sex: female."),
        coverage_id="life_income",
        product_id="immediate_annuity",
        state="IL",
    )
    assert healthy.eligible is True, healthy.ineligibility_reasons
    assert healthy.adjusted_premium == 100_000.0
    assert healthy.metadata["filed_annuity"] is True
    sick = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 80. Sex: female. Active cancer on chemotherapy."),
        coverage_id="life_income",
        product_id="immediate_annuity",
        state="IL",
    )
    assert sick.eligible is False
    assert any("Active malignancy" in r for r in sick.ineligibility_reasons)
    life = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 91. Sex: male."),
        coverage_id="single_life_income",
        product_id="life_annuity",
        state="IL",
    )
    assert life.eligible is False
    assert any("outside" in r for r in life.ineligibility_reasons)


def test_fixed_annuity_income_issues_and_accumulation_does_not() -> None:
    male = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 65. Sex: male."),
        coverage_id="fixed_income",
        product_id="fixed_annuity",
        state="IL",
    )
    female = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 65. Sex: female."),
        coverage_id="fixed_income",
        product_id="fixed_annuity",
        state="IL",
    )
    assert male.eligible is True, male.ineligibility_reasons
    assert male.metadata["phase"] == "income"
    assert male.metadata["rating_engine"] == "life_filing"
    assert male.metadata["filed_annuity"] is True
    assert male.metadata["filing_id"] == "RYT-LIFE-ANN-2026-01"
    assert male.adjusted_premium == 100_000.0
    factor = male.metadata["actuarial"]["annuity_factor"]
    assert male.metadata["annual_payout_at_vesting"] == pytest.approx(100_000 / factor, rel=0.001)
    assert female.eligible is True
    assert female.metadata["annual_payout_at_vesting"] < male.metadata["annual_payout_at_vesting"]

    older = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 80. Sex: female."),
        coverage_id="fixed_income",
        product_id="fixed_annuity",
        state="IL",
    )
    assert older.eligible is True, older.ineligibility_reasons

    accum = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 65. Sex: male."),
        coverage_id="fixed_accum",
        product_id="fixed_annuity",
        state="IL",
    )
    assert accum.eligible is False
    assert accum.adjusted_premium == 0.0
    assert accum.metadata["phase"] == "accumulation"
    assert accum.metadata["fund_value_at_vesting"] > 100_000
    assert accum.metadata.get("filed_annuity") is not True
    assert accum.metadata["rating_engine"] == "annuity_illustration"
    assert any("renewable declared rate" in r for r in accum.ineligibility_reasons)

    missing = rate_life(
        _bundle("Applicant age: 65. Sex: male."),
        coverage_id="fixed_income",
        product_id="fixed_annuity",
        state="IL",
    )
    assert missing.eligible is False
    assert missing.metadata["purchase_price"] == 0.0
    assert any("not on the submission" in r for r in missing.ineligibility_reasons)

    small = rate_life(
        _bundle("Purchase price: $1000. Applicant age: 65. Sex: male."),
        coverage_id="fixed_income",
        product_id="fixed_annuity",
        state="IL",
    )
    assert small.eligible is False
    assert any("below the $5,000 minimum" in r for r in small.ineligibility_reasons)

    young = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 30. Sex: male."),
        coverage_id="fixed_income",
        product_id="fixed_annuity",
        state="IL",
    )
    assert young.eligible is False
    assert any("outside 40-85" in r for r in young.ineligibility_reasons)

    al = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 65. Sex: male."),
        coverage_id="fixed_income",
        product_id="fixed_annuity",
        state="AL",
    )
    assert al.eligible is False
    assert al.metadata.get("filed_annuity") is not True
    assert any("not a AL state-of-issue filing" in r for r in al.ineligibility_reasons)


def test_deferred_income_is_the_contract_and_accumulation_is_not() -> None:
    male = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 55. Sex: male."),
        coverage_id="deferred_income",
        product_id="deferred_annuity",
        state="IL",
    )
    female = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 55. Sex: female."),
        coverage_id="deferred_income",
        product_id="deferred_annuity",
        state="IL",
    )
    assert male.eligible is True, male.ineligibility_reasons
    assert male.metadata["rating_engine"] == "life_filing"
    assert male.metadata["filed_annuity"] is True
    assert female.metadata["annual_payout_at_vesting"] < male.metadata["annual_payout_at_vesting"]
    vested = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 68. Sex: male."),
        coverage_id="deferred_income",
        product_id="deferred_annuity",
        state="IL",
    )
    assert vested.eligible is True, vested.ineligibility_reasons
    assert vested.metadata["years_to_vesting"] == 0
    assert vested.metadata["vesting_age"] == 68
    accum = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 55. Sex: male."),
        coverage_id="deferred_accum",
        product_id="deferred_annuity",
        state="IL",
    )
    assert accum.eligible is False
    assert accum.metadata.get("filed_annuity") is not True
    assert accum.metadata["fund_value_at_vesting"] > 100_000
    assert any("assumed credited rate" in r for r in accum.ineligibility_reasons)
    missing = rate_life(
        _bundle("Applicant age: 55. Sex: male."),
        coverage_id="deferred_income",
        product_id="deferred_annuity",
        state="IL",
    )
    assert missing.eligible is False
    assert missing.metadata["purchase_price"] == 0.0
    assert any("not on the submission" in r for r in missing.ineligibility_reasons)
    young = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 25. Sex: male."),
        coverage_id="deferred_income",
        product_id="deferred_annuity",
        state="IL",
    )
    assert young.eligible is False
    assert any("outside 30-70" in r for r in young.ineligibility_reasons)


def test_deferred_income_age_and_consideration_edges() -> None:
    def income(text: str, state: str = "IL"):
        return rate_life(_bundle(text), coverage_id="deferred_income", product_id="deferred_annuity", state=state)

    at_min = income("Purchase price: $100000. Applicant age: 30. Sex: male. Non-smoker.")
    assert at_min.eligible is True, at_min.ineligibility_reasons
    assert at_min.metadata["vesting_age"] == 65
    assert at_min.metadata["years_to_vesting"] == 35

    at_vesting = income("Purchase price: $100000. Applicant age: 65. Sex: male. Non-smoker.")
    assert at_vesting.eligible is True, at_vesting.ineligibility_reasons
    assert at_vesting.metadata["years_to_vesting"] == 0
    assert at_vesting.metadata["vesting_age"] == 65
    assert at_vesting.metadata["fund_value_at_vesting"] == 100_000
    assert at_vesting.metadata["annual_payout_at_vesting"] == pytest.approx(at_vesting.metadata["illustrated_payout_at_vesting"])
    assert at_vesting.adjusted_premium == 100_000

    at_max = income("Purchase price: $100000. Applicant age: 70. Sex: male. Non-smoker.")
    assert at_max.eligible is True, at_max.ineligibility_reasons
    assert at_max.metadata["vesting_age"] == 70
    assert at_max.metadata["years_to_vesting"] == 0

    under = income("Purchase price: $100000. Applicant age: 29. Sex: male. Non-smoker.")
    over = income("Purchase price: $100000. Applicant age: 71. Sex: male. Non-smoker.")
    assert under.eligible is False
    assert over.eligible is False
    assert any("outside 30-70" in r for r in under.ineligibility_reasons)
    assert any("outside 30-70" in r for r in over.ineligibility_reasons)

    # A longer deferral buys a larger annual income. The year of vesting itself does not.
    assert at_min.metadata["annual_payout_at_vesting"] > at_vesting.metadata["annual_payout_at_vesting"]

    floor = income("Purchase price: $5000. Applicant age: 65. Sex: male. Non-smoker.")
    assert floor.eligible is True, floor.ineligibility_reasons
    penny = income("Purchase price: $4999. Applicant age: 65. Sex: male. Non-smoker.")
    assert penny.eligible is False
    assert penny.adjusted_premium == 0.0
    assert any("below the $5,000 minimum" in r for r in penny.ineligibility_reasons)

    zero = income("Purchase price: $0. Applicant age: 65. Sex: male. Non-smoker.")
    assert zero.eligible is False
    assert zero.metadata["purchase_price"] == 0.0
    assert zero.metadata["fund_value_at_vesting"] == 0.0

    smoker = income("Purchase price: $100000. Applicant age: 55. Sex: male. Smoker.")
    nonsmoker = income("Purchase price: $100000. Applicant age: 55. Sex: male. Non-smoker.")
    assert smoker.eligible is True, smoker.ineligibility_reasons
    assert smoker.metadata["annual_payout_at_vesting"] > nonsmoker.metadata["annual_payout_at_vesting"]

    sick = income("Purchase price: $100000. Applicant age: 55. Sex: male. Active cancer on chemotherapy.")
    assert sick.eligible is False
    assert sick.adjusted_premium == 0.0
    assert any("Active malignancy" in r for r in sick.ineligibility_reasons)

    al = income("Purchase price: $100000. Applicant age: 65. Sex: male. Non-smoker.", state="AL")
    assert al.eligible is False
    assert al.metadata.get("filed_annuity") is not True
    assert any("not a AL state-of-issue filing" in r for r in al.ineligibility_reasons)


def test_gmwb_is_five_percent_of_the_stated_base() -> None:
    def gmwb(text: str, state: str = "IL"):
        return rate_life(_bundle(text), coverage_id="var_gmwb", product_id="variable_annuity", state=state)

    male = gmwb("Purchase price: $100000. Applicant age: 65. Sex: male. Non-smoker.")
    female = gmwb("Purchase price: $100000. Applicant age: 65. Sex: female. Non-smoker.")
    assert male.eligible is True, male.ineligibility_reasons
    assert male.metadata["rating_engine"] == "life_filing"
    assert male.metadata["filed_annuity"] is True
    assert male.adjusted_premium == 100_000
    assert male.metadata["withdrawal_base_if_gmwb"] == 100_000
    assert male.metadata["guaranteed_annual_withdrawal"] == 5_000
    assert female.metadata["guaranteed_annual_withdrawal"] == male.metadata["guaranteed_annual_withdrawal"]
    assert male.metadata["fund_value_projection_air_basis"] > 100_000
    assert male.metadata["illustrated_payout_at_vesting"] != pytest.approx(5_000, rel=0.01)

    older = gmwb("Purchase price: $100000. Applicant age: 80. Sex: female. Non-smoker.")
    assert older.eligible is True, older.ineligibility_reasons
    assert older.metadata["guaranteed_annual_withdrawal"] == 5_000

    floor = gmwb("Purchase price: $25000. Applicant age: 40. Sex: male. Non-smoker.")
    assert floor.eligible is True, floor.ineligibility_reasons
    assert floor.metadata["guaranteed_annual_withdrawal"] == 1_250
    under = gmwb("Purchase price: $24999. Applicant age: 40. Sex: male. Non-smoker.")
    assert under.eligible is False
    assert under.adjusted_premium == 0.0
    assert any("below the $25,000 minimum" in r for r in under.ineligibility_reasons)

    young = gmwb("Purchase price: $100000. Applicant age: 39. Sex: male. Non-smoker.")
    old = gmwb("Purchase price: $100000. Applicant age: 81. Sex: male. Non-smoker.")
    assert young.eligible is False and any("outside 40-80" in r for r in young.ineligibility_reasons)
    assert old.eligible is False and any("outside 40-80" in r for r in old.ineligibility_reasons)

    missing = gmwb("Applicant age: 65. Sex: male. Non-smoker.")
    assert missing.eligible is False
    assert missing.metadata["purchase_price"] == 0.0
    assert missing.metadata["guaranteed_annual_withdrawal"] == 0.0

    sick = gmwb("Purchase price: $100000. Applicant age: 65. Sex: male. Active cancer on chemotherapy.")
    assert sick.eligible is False
    assert sick.adjusted_premium == 0.0
    assert any("Active malignancy" in r for r in sick.ineligibility_reasons)

    bare = rate_life(
        _bundle("Purchase price: $100000. Applicant age: 65. Sex: male. Non-smoker."),
        coverage_id="var_annuity",
        product_id="variable_annuity",
        state="IL",
    )
    assert bare.eligible is False
    assert bare.metadata.get("filed_annuity") is not True
    assert bare.metadata["rating_engine"] == "annuity_illustration"
    assert any("subaccounts can lose value" in r for r in bare.ineligibility_reasons)

    al = gmwb("Purchase price: $100000. Applicant age: 65. Sex: male. Non-smoker.", state="AL")
    assert al.eligible is False
    assert al.metadata.get("filed_annuity") is not True
    assert any("not a AL state-of-issue filing" in r for r in al.ineligibility_reasons)
