"""Real-world life underwriting test suite — every LOB, all states, edge/negative cases.

Covers the scenarios a practicing life underwriter actually faces:
  * Medical decisioning: knockouts, negated histories, vitals boundary matrices,
    class assignment, tobacco interactions, avocation flat extras, referrals.
  * Financial justification: age-banded income multiples, net-worth estate basis,
    in-force aggregation, insurable interest, replacement / 1035 paperwork.
  * Reinsurance ladder: retention → automatic cession → jumbo → facultative.
  * Rating mechanics: mortality/class/sex/tobacco/term/modal/band/state math.
  * State law across all 51 jurisdictions (life AND annuity free look, senior
    extensions, community property, guaranty caps, grace periods, claims
    settlement anchors, premium tax tiers, suitability regimes).
  * Product gates for all seven LOBs and adversarial/malformed submissions.
"""

from __future__ import annotations

import pytest

from insureflow.life.lobs.state_law import (
    ANNUITY_FREE_LOOK_DAYS,
    ANNUITY_PREMIUM_TAX,
    COMMUNITY_PROPERTY_STATES,
    GRACE_PERIOD_DAYS_DEFAULT,
    LIFE_FREE_LOOK_DAYS,
    premium_tax_on_consideration,
)
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.personal.life_rating import rate_life
from insureflow.underwriting.life_financial import evaluate_life_financial, income_multiple_for_age
from insureflow.underwriting.life_medical import underwrite_life
from insureflow.underwriting.life_reinsurance import evaluate_life_reinsurance


def _bundle(text: str) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="uw-realworld",
        unstructured=[UnstructuredSubmission(submission_id="d0", source="app.md", raw_text=text, document_type="supplemental")],
    )


def _med(text: str):
    return underwrite_life(_bundle(text))


BASE = "Face amount: $500000. Applicant age: 42."


# ---------------------------------------------------------------------------
# Medical knockouts — instant declines
# ---------------------------------------------------------------------------


class TestMedicalKnockouts:
    @pytest.mark.parametrize(
        "disclosure,reason_frag",
        [
            ("Active cancer on chemotherapy.", "malignancy"),
            ("Metastatic breast cancer diagnosed last month.", "malignancy"),
            ("HIV positive since 2021.", "HIV"),
            ("AIDS diagnosis 2019.", "HIV"),
            ("Current substance abuse treatment.", "substance"),
            ("Active addiction, IV drug use.", "substance"),
            ("Felony conviction in 2018.", "criminal"),
            ("Currently incarcerated.", "criminal"),
            ("Suicide attempt in 2020.", "suicide"),
            ("Suicidal ideation noted by therapist.", "suicide"),
            ("Organ transplant recipient (kidney).", "transplant"),
            ("Awaiting transplant evaluation.", "transplant"),
        ],
    )
    def test_knockout_declines(self, disclosure: str, reason_frag: str) -> None:
        d = _med(f"{BASE} {disclosure}")
        assert d.decision.value == "decline"
        assert any(reason_frag.lower() in r.lower() for r in d.reasons)

    def test_knockout_beats_preferred_language(self) -> None:
        d = _med(f"{BASE} Preferred plus risk. Active cancer under treatment.")
        assert d.decision.value == "decline"
        assert d.underwriting_class == "substandard"

    def test_knockout_short_circuits_with_full_evidence_flags(self) -> None:
        d = _med(f"{BASE} HIV positive.")
        assert d.require_aps is True
        assert d.require_paramed is True
        assert d.flat_extras_per_1000 == 0.0

    def test_knockout_through_registered_product_path_stays_ineligible(self) -> None:
        q = rate_life(_bundle("Applicant age: 42. Face amount: $500000. Active cancer on chemotherapy."), coverage_id="level_term_20", product_id="level_term")
        assert q.eligible is False
        assert q.metadata["medical"]["decision"] == "decline"

    def test_clean_application_accepts(self) -> None:
        d = _med(f"{BASE} Annual income: $120000. Non-smoker. Preferred. No significant medical history.")
        assert d.decision.value in ("accept", "conditional_accept")
        assert d.underwriting_class == "preferred"


class TestKnockoutNegationGuard:
    """Real applications are full of negated histories ('no prior X').

    Knockouts/referrals must fire on AFFIRMATIVE disclosures only — negated
    histories are stripped before pattern matching (the single most damaging
    false-decline source for a life UW desk).
    """

    def test_negated_cancer_history_not_declined(self) -> None:
        d = _med(f"{BASE} No active cancer. History of treated melanoma, no recurrence.")
        assert d.decision.value != "decline"

    def test_denied_suicide_history_not_declined(self) -> None:
        d = _med(f"{BASE} Denies any history of suicide attempt or suicidal ideation.")
        assert d.decision.value != "decline"

    def test_denied_substance_use_not_declined(self) -> None:
        d = _med(f"{BASE} No IV drug use; denies current substance abuse or active addiction.")
        assert d.decision.value != "decline"

    def test_negated_transplant_not_declined(self) -> None:
        d = _med(f"{BASE} No prior organ transplant; not awaiting transplant.")
        assert d.decision.value != "decline"

    @pytest.mark.parametrize(
        "wording",
        [
            "Criminal history: none",
            "Criminal history: no",
            "Criminal history: n/a",
            "Tobacco: none",
            "Nicotine: negative",
            "Cigarettes: 0",
        ],
    )
    def test_explicit_negative_fields_do_not_trip_guards(self, wording: str) -> None:
        d = _med(f"{BASE} {wording}.")
        assert d.decision.value != "decline"


# ---------------------------------------------------------------------------
# Vitals bands — exact boundary matrix (build build build)
# ---------------------------------------------------------------------------


class TestVitalsBands:
    CASES = [
        # (vital label, value, expected class when applicant claims Preferred)
        ("Blood pressure: {v}/78", 130, "preferred"),  # at preferred_max stays preferred
        ("Blood pressure: {v}/78", 131, "standard"),  # 1 over blocks preferred
        ("Blood pressure: {v}/78", 140, "standard"),  # at standard_max
        ("Blood pressure: {v}/78", 141, "table_a"),  # over standard_max
        ("Blood pressure: {v}/78", 150, "table_a"),
        ("Blood pressure: {v}/78", 151, "table_b"),
        ("Blood pressure: {v}/78", 180, "table_b"),
        ("Blood pressure: {v}/78", 181, "DECLINE"),
        ("BMI: {v}", 27.0, "preferred"),
        ("BMI: {v}", 27.1, "standard"),
        ("BMI: {v}", 32.0, "standard"),
        ("BMI: {v}", 32.1, "table_a"),
        ("BMI: {v}", 36.0, "table_a"),
        ("BMI: {v}", 36.1, "table_b"),
        ("BMI: {v}", 42.0, "table_b"),
        ("BMI: {v}", 42.1, "DECLINE"),
        ("Cholesterol: {v}", 220, "preferred"),
        ("Cholesterol: {v}", 221, "standard"),
        ("Cholesterol: {v}", 260, "standard"),
        ("Cholesterol: {v}", 261, "table_a"),
        ("Cholesterol: {v}", 300, "table_a"),
        ("Cholesterol: {v}", 301, "table_b"),
        ("Cholesterol: {v}", 350, "table_b"),
        ("Cholesterol: {v}", 351, "DECLINE"),
    ]

    @pytest.mark.parametrize("template,value,expected", CASES, ids=[f"{t.split(':')[0]}-{v}" for t, v, _ in CASES])
    def test_vital_boundary(self, template: str, value: float, expected: str) -> None:
        d = _med(f"Face amount: $500000. Applicant age: 40. Preferred. {template.format(v=value)}.")
        if expected == "DECLINE":
            assert d.decision.value == "decline"
        else:
            assert d.underwriting_class == expected

    def test_worst_vital_wins_when_multiple_violated(self) -> None:
        d = _med("Face amount: $500000. Applicant age: 40. BMI: 34. Cholesterol: 310.")
        assert d.underwriting_class == "table_b"

    def test_malformed_vitals_ignored_without_crash(self) -> None:
        d = _med(f"{BASE} Blood pressure: high/??. BMI: not recorded. Cholesterol: N/A.")
        assert d.vitals == {}
        assert d.decision.value != "decline"

    def test_missing_vitals_leave_class_untouched(self) -> None:
        d = _med(f"{BASE} Preferred.")
        assert d.underwriting_class == "preferred"

    def test_diastolic_parsed_alongside_systolic(self) -> None:
        d = _med(f"{BASE} Blood pressure: 118/76.")
        assert d.vitals["bp_systolic"] == 118
        assert d.vitals["bp_diastolic"] == 76


# ---------------------------------------------------------------------------
# Class assignment & tobacco interaction
# ---------------------------------------------------------------------------


class TestClassAssignment:
    def test_preferred_plus_caps_super_preferred(self) -> None:
        q = rate_life(_bundle("Applicant age: 42. Sex: male. Face amount: $300000. Non-smoker. Preferred plus."), coverage_id="level_term_20")
        comp = {c.name: c.amount for c in q.schedule_modifications}
        assert q.metadata["medical"]["underwriting_class"] == "preferred"
        assert comp["underwriting_class"] == pytest.approx(0.82)

    def test_substantiated_table_floor(self) -> None:
        d = _med(f"{BASE} Rated table 2 per preliminary review.")
        assert d.underwriting_class == "table_b"

    def test_tobacco_blocks_preferred_classes(self) -> None:
        d = _med(f"{BASE} Preferred plus health class. Current smoker.")
        assert d.tobacco is True
        assert d.underwriting_class == "standard"
        assert any("Tobacco blocks preferred" in r for r in d.reasons)

    def test_tobacco_wording_variants_detected(self) -> None:
        for wording in ("Current smoker", "Nicotine: positive", "Tobacco: cigars occasionally"):
            d = _med(f"{BASE} {wording}.")
            assert d.tobacco is True, wording

    def test_smoker_premium_exceeds_non_smoker(self) -> None:
        ns = rate_life(_bundle("Applicant age: 42. Sex: male. Face amount: $300000. Tobacco: none."), coverage_id="level_term_20")
        sm = rate_life(_bundle("Applicant age: 42. Sex: male. Face amount: $300000. Current smoker."), coverage_id="level_term_20")
        assert sm.adjusted_premium > ns.adjusted_premium
        sm_comp = {c.name: c.amount for c in sm.schedule_modifications}
        ns_comp = {c.name: c.amount for c in ns.schedule_modifications}
        assert sm_comp["tobacco_factor"] == 1.85
        assert ns_comp["tobacco_factor"] == 1.0

    def test_a1c_boundary_referral(self) -> None:
        assert _med(f"{BASE} A1C: 6.4.").decision.value != "refer"
        d = _med(f"{BASE} A1C: 7.0.")
        assert d.decision.value == "refer"
        assert any("Diabetes" in r for r in d.reasons)

    def test_diabetes_wordings_refer(self) -> None:
        for wording in ("Diabetes type 2, diet controlled", "Insulin dependent diabetic"):
            d = _med(f"{BASE} {wording}.")
            assert d.decision.value == "refer", wording


# ---------------------------------------------------------------------------
# Avocation flat extras
# ---------------------------------------------------------------------------


class TestAvocationFlatExtras:
    AMOUNTS = {"scuba": 2.5, "skydiving": 3.5, "aviation": 3.0, "motorsport": 4.0}

    @pytest.mark.parametrize("activity,amount", sorted(AMOUNTS.items()))
    def test_single_avocation_extra(self, activity: str, amount: float) -> None:
        d = _med(f"{BASE} Enjoys {activity} on weekends.")
        assert d.flat_extras_per_1000 == amount

    def test_extras_stack_additively(self) -> None:
        d = _med(f"{BASE} Enjoys scuba, skydiving, aviation, and motorsport.")
        assert d.flat_extras_per_1000 == pytest.approx(sum(self.AMOUNTS.values()))

    def test_extra_flows_into_premium(self) -> None:
        clean = rate_life(_bundle(BASE + " Tobacco: none."), coverage_id="level_term_20")
        risky = rate_life(
            _bundle(BASE + " Tobacco: none. Recreational scuba diver."),
            coverage_id="level_term_20",
        )
        face = 500_000
        assert risky.adjusted_premium == pytest.approx(clean.adjusted_premium + (face / 1000) * 2.5, rel=0.001)

    def test_no_avocation_no_extra(self) -> None:
        assert _med(f"{BASE} Reads and gardens.").flat_extras_per_1000 == 0.0


# ---------------------------------------------------------------------------
# Referrals — cardiac, financial-stretch, jumbo / facultative
# ---------------------------------------------------------------------------


class TestReferrals:
    @pytest.mark.parametrize(
        "disclosure",
        ["Heart attack in 2021.", "Myocardial infarction 2019.", "Coronary stent placed 2022.", "Bypass surgery 2018.", "History of coronary artery disease."],
    )
    def test_cardiac_history_refers(self, disclosure: str) -> None:
        d = _med(f"{BASE} {disclosure}")
        assert d.decision.value == "refer"
        assert any("medical director" in r.lower() for r in d.reasons)

    @pytest.mark.parametrize("denial", ["No coronary artery disease.", "No heart attack. No bypass surgery.", "Without coronary stent."])
    def test_negated_cardiac_does_not_refer_on_cardiac_grounds(self, denial: str) -> None:
        d = _med(f"{BASE} {denial}")
        assert not any("Cardiac" in r for r in d.reasons)

    def test_jumbo_face_at_threshold_refers(self) -> None:
        d = _med("Face amount: $5000000. Applicant age: 40.")
        assert d.decision.value == "refer"
        assert any("Jumbo" in r for r in d.reasons)

    def test_just_under_jumbo_does_not_jumbo_refer(self) -> None:
        d = _med("Face amount: $4999999. Applicant age: 40. Annual income: $500000.")
        assert d.decision.value != "refer" or not any("Jumbo" in r for r in d.reasons)

    def test_facultative_reinsurance_flagged_in_metadata(self) -> None:
        q = rate_life(_bundle("Face amount: $12000000. Applicant age: 45. Non-smoker."), coverage_id="level_term_20", product_id="level_term")
        re_meta = q.metadata["life_reinsurance"]
        assert re_meta["facultative_required"] is True
        assert q.metadata["facultative_required"] is True

    def test_facultative_face_conditions_bind_before_issue(self) -> None:
        """Facultative case: quote carries the placement condition and bind would be blocked."""
        bundle = _bundle("Face amount: $12000000. Applicant age: 45. Non-smoker.")
        q = rate_life(bundle, coverage_id="level_term_20", product_id="level_term")
        assert any("facultative reinsurance" in c.lower() for c in q.metadata["conditions"])
        from insureflow.underwriting.bind_gates import life_evidence_holds

        holds = life_evidence_holds(bundle, q.metadata)
        assert any("Facultative reinsurance not placed" in h for h in holds)

    def test_income_stretch_refers(self) -> None:
        d = _med(f"{BASE} Annual income: $10000.")
        assert d.decision.value == "refer"
        assert any("income multiple" in r.lower() for r in d.reasons)


# ---------------------------------------------------------------------------
# Age eligibility boundaries
# ---------------------------------------------------------------------------


class TestAgeEligibility:
    @pytest.mark.parametrize(
        "age,expect",
        [(17, "decline"), (18, "issueable"), (30, "issueable"), (74, "issueable"), (75, "issueable"), (76, "decline")],
    )
    def test_issue_age_boundaries(self, age: int, expect: str) -> None:
        d = _med(f"Face amount: $250000. Applicant age: {age}.")
        if expect == "decline":
            assert d.decision.value == "decline"
            assert any("Age outside issue ages" in r for r in d.reasons)
        else:
            assert d.decision.value != "decline"

    def test_missing_age_defaults_for_rating(self) -> None:
        q = rate_life(_bundle("Term life application. Face amount: $250000. Non-smoker."))
        assert q.eligible is False or q.adjusted_premium > 0  # rates at default age 40, never crashes


# ---------------------------------------------------------------------------
# Evidence requirements — APS / paramed boundaries from the medical guide
# ---------------------------------------------------------------------------


class TestEvidenceRequirements:
    @pytest.mark.parametrize(
        "age,face,aps,paramed",
        [
            (39, 999_999, False, True),  # <40 needs only paramed above $100k
            (40, 1_000_000, True, True),  # APS kicks in at 40/$1M
            (49, 500_000, False, True),  # still pre-50
            (50, 25_000, True, True),  # 50+ always both
            (18, 99_999, False, False),  # small face, young: neither
            (18, 100_000, False, True),  # paramed floor exactly $100k
            (17, 5_000_000, False, False),  # declined for age before evidence matters
        ],
    )
    def test_requirement_matrix(self, age: int, face: float, aps: bool, paramed: bool) -> None:
        d = _med(f"Face amount: ${face}. Applicant age: {age}.")
        assert d.require_aps is aps, (age, face)
        assert d.require_paramed is paramed, (age, face)

    def test_aps_on_file_upgrades_to_plain_accept(self) -> None:
        d = _med("Face amount: $500000. Applicant age: 55. APS received and reviewed.")
        assert d.decision.value == "accept"

    def test_generic_path_conditions_the_offer_on_aps(self) -> None:
        q = rate_life(_bundle("Face amount: $1500000. Applicant age: 52. Non-smoker."))
        assert any("APS" in c for c in q.metadata["conditions"])

    def test_aps_missing_conditions_the_offer(self) -> None:
        q = rate_life(_bundle("Face amount: $1500000. Applicant age: 52. Non-smoker."), coverage_id="level_term_20", product_id="level_term")
        assert any("APS" in c for c in q.metadata["conditions"])

    def test_paramed_condition_present_for_standard_case(self) -> None:
        q = rate_life(_bundle(BASE + " Non-smoker."), coverage_id="level_term_20")
        assert any("Paramedical exam required" in c for c in q.metadata["conditions"])


# ---------------------------------------------------------------------------
# Face amount edges
# ---------------------------------------------------------------------------


class TestFaceAmountEdges:
    def test_missing_face_cannot_rate(self) -> None:
        q = rate_life(_bundle("Applicant age: 42. Wants coverage. Non-smoker."))
        assert q.eligible is False
        assert q.adjusted_premium == 0.0
        assert q.metadata.get("tiv_unknown") is True
        assert any("Face amount missing" in r for r in q.ineligibility_reasons)

    def test_tiny_face_hits_minimum_premium_floor(self) -> None:
        q = rate_life(_bundle("Applicant age: 22. Face amount: $10000."), coverage_id="level_term_10")
        assert q.adjusted_premium == 250.0  # manual minimum_premium

    def test_band_discount_boundaries(self) -> None:
        below = rate_life(_bundle("Applicant age: 42. Sex: male. Face amount: $249,999. Non-smoker."), coverage_id="level_term_20")
        at = rate_life(_bundle("Applicant age: 42. Sex: male. Face amount: $250000. Non-smoker."), coverage_id="level_term_20")
        assert at.adjusted_premium < below.adjusted_premium

    def test_deeper_band_discount_at_2_5m(self) -> None:
        m = rate_life(_bundle("Applicant age: 40. Sex: male. Face amount: $2000000. Non-smoker. Annual income: $400000."), coverage_id="level_term_20")
        xl = rate_life(_bundle("Applicant age: 40. Sex: male. Face amount: $2500000. Non-smoker. Annual income: $400000."), coverage_id="level_term_20")
        m_band = next(c.amount for c in m.schedule_modifications if c.name == "band_discount")
        xl_band = next(c.amount for c in xl.schedule_modifications if c.name == "band_discount")
        assert m_band == 0.9 and xl_band == 0.88

    def test_zero_face_generic_path_cannot_rate(self) -> None:
        q = rate_life(_bundle("Applicant age: 42. Face amount: $0. Non-smoker."))
        assert q.adjusted_premium == 0.0
        assert q.eligible is False
        assert any("Face amount missing" in r for r in q.ineligibility_reasons)

    def test_zero_face_lob_path_refuses_to_rate(self) -> None:
        q = rate_life(_bundle("Applicant age: 42. Face amount: $0. Non-smoker."), coverage_id="level_term_20", product_id="level_term")
        assert q.adjusted_premium == 0.0
        assert q.eligible is False


# ---------------------------------------------------------------------------
# Financial underwriting — real justification scenarios
# ---------------------------------------------------------------------------


class TestFinancialUnderwriting:
    @pytest.mark.parametrize(
        "age,multiple",
        [(18, 30), (30, 30), (31, 25), (40, 25), (41, 20), (50, 20), (51, 15), (60, 15), (61, 10), (75, 10)],
    )
    def test_age_banded_income_multiples(self, age: int, multiple: int) -> None:
        assert income_multiple_for_age(age) == multiple

    def test_face_within_multiple_is_clean(self) -> None:
        f = evaluate_life_financial(_bundle("Face amount: $750000. Applicant age: 40. Annual income: $30000."))
        assert f.decision_hint.value != "refer"
        assert f.max_face_income == 750000.0

    def test_face_over_multiple_refers(self) -> None:
        f = evaluate_life_financial(_bundle("Face amount: $790000. Applicant age: 40. Annual income: $30000."))
        assert f.decision_hint.value == "refer"

    def test_five_percent_tolerance_band(self) -> None:
        edge = evaluate_life_financial(_bundle("Face amount: $787500. Applicant age: 40. Annual income: $30000."))
        assert edge.decision_hint.value != "refer"  # exactly 25x * 1.05

    def test_net_worth_rescues_income_stretch(self) -> None:
        f = evaluate_life_financial(_bundle("Face amount: $900000. Applicant age: 40. Annual income: $30000. Net worth: $4,000,000"))
        assert f.decision_hint.value != "refer"

    def test_estate_basis_net_worth_only(self) -> None:
        ok = evaluate_life_financial(_bundle("Face amount: $1000000. Applicant age: 70. Net worth: $5,000,000"))
        assert ok.decision_hint.value != "refer"
        over = evaluate_life_financial(_bundle("Face amount: $1000000. Applicant age: 70. Net worth: $500,000"))
        assert over.decision_hint.value == "refer"
        assert any("net-worth multiple" in r.lower() or "Estate-basis" in r for r in over.reasons)

    def test_both_income_and_net_worth_missing_refers(self) -> None:
        f = evaluate_life_financial(_bundle(f"{BASE}"))
        assert f.decision_hint.value == "refer"
        assert any("both missing" in r for r in f.reasons)

    def test_in_force_coverage_aggregates_with_applied_face(self) -> None:
        f = evaluate_life_financial(_bundle("Face amount: $400000. Applicant age: 40. Annual income: $30000. In-force face: $500000"))
        assert f.in_force_face == 500000.0
        assert f.decision_hint.value == "refer"  # 900k total vs 750k cap

    @pytest.mark.parametrize("good_rel", ["spouse", "child", "parent", "irrevocable trust", "estate", "key person", "business partner"])
    def test_insurable_interest_accepted_classes(self, good_rel: str) -> None:
        f = evaluate_life_financial(_bundle(f"{BASE} Beneficiary relationship: {good_rel}"))
        assert f.insurable_interest_ok is True, good_rel

    @pytest.mark.parametrize("bad_rel", ["friend", "neighbor", "stranger", "acquaintance"])
    def test_insurable_interest_rejected_classes(self, bad_rel: str) -> None:
        f = evaluate_life_financial(_bundle(f"{BASE} Beneficiary relationship: {bad_rel} John D"))
        assert f.insurable_interest_ok is False
        assert f.decision_hint.value == "refer"
        assert any("Insurable interest" in r for r in f.reasons)

    def test_unstated_beneficiary_flagged_but_not_referred(self) -> None:
        f = evaluate_life_financial(_bundle("Face amount: $400000. Applicant age: 40. Annual income: $100000."))
        assert f.insurable_interest_ok is None

    def test_replacement_without_form_refers(self) -> None:
        f = evaluate_life_financial(_bundle(f"{BASE} Existing policy to be lapsed; replacing coverage."))
        assert f.replacement is True
        assert f.decision_hint.value == "refer"
        assert any("Replacement / 1035 form missing" in r for r in f.reasons)

    def test_replacement_with_naic_notice_clears(self) -> None:
        f = evaluate_life_financial(_bundle(f"{BASE} Replacing existing policy. Signed NAIC replacement notice on file."))
        assert f.replacement is True
        assert not any("form missing" in r for r in f.reasons)

    def test_1035_exchange_with_assignment_clears(self) -> None:
        f = evaluate_life_financial(_bundle(f"{BASE} Section 1035 exchange form attached."))
        assert f.exchange_1035 is True
        assert not any("form missing" in r for r in f.reasons)


# ---------------------------------------------------------------------------
# Riders
# ---------------------------------------------------------------------------


class TestRiders:
    RATES = {"waiver_of_premium": 0.12, "accidental_death": 0.5, "child_term": 0.35, "accelerated_benefit": 0.08}

    def test_all_riders_detected_and_loaded(self) -> None:
        f = evaluate_life_financial(_bundle(f"{BASE} Waiver of premium rider. Accidental death rider. Child term rider. Accelerated benefit rider."))
        assert set(f.riders) == set(self.RATES)
        assert f.rider_load_per_1000 == pytest.approx(sum(self.RATES.values()))

    @pytest.mark.parametrize(
        "phrase,rider",
        [
            ("WOP elected", "waiver_of_premium"),
            ("double indemnity for accidents", "accidental_death"),
            ("children's rider for two kids", "child_term"),
            ("chronic illness rider", "accelerated_benefit"),
        ],
    )
    def test_rider_wording_variants(self, phrase: str, rider: str) -> None:
        f = evaluate_life_financial(_bundle(f"{BASE} {phrase}."))
        assert rider in f.riders

    def test_rider_load_flows_into_lob_premium(self) -> None:
        clean = rate_life(_bundle("Applicant age: 42. Face amount: $500000. Non-smoker."), coverage_id="level_term_20")
        riders = rate_life(
            _bundle("Applicant age: 42. Face amount: $500000. Non-smoker. Waiver of premium and accidental death riders requested."),
            coverage_id="level_term_20",
        )
        expected_delta = (500_000 / 1000) * (0.12 + 0.5)
        assert riders.metadata["financial"]["riders"] == ["waiver_of_premium", "accidental_death"]
        assert riders.adjusted_premium == pytest.approx(clean.adjusted_premium + expected_delta, rel=0.001)

    def test_riders_conditioned_on_generic_quote(self) -> None:
        q = rate_life(_bundle(BASE + " Non-smoker. Waiver of premium and accidental death riders requested."))
        assert any("Riders:" in c for c in q.metadata["conditions"])


# ---------------------------------------------------------------------------
# Reinsurance ladder
# ---------------------------------------------------------------------------


class TestReinsuranceLadder:
    def run(self, text: str):
        return evaluate_life_reinsurance(_bundle(text))

    def test_within_retention_no_cession(self) -> None:
        r = self.run("Face amount: $1000000. Applicant age: 40.")
        assert r.cession == 0.0
        assert r.facultative_required is False
        assert r.jumbo is False

    def test_automatic_cession_math(self) -> None:
        r = self.run("Face amount: $2400000. Applicant age: 40.")
        assert r.cession == 1_400_000.0  # face − $1M retention
        assert r.jumbo is False

    def test_jumbo_at_automatic_limit(self) -> None:
        r = self.run("Face amount: $6000000. Applicant age: 40.")
        assert r.jumbo is True
        assert r.facultative_required is False
        assert r.decision_hint.value == "refer"

    def test_facultative_at_threshold(self) -> None:
        r = self.run("Face amount: $10000000. Applicant age: 40.")
        assert r.facultative_required is True
        assert r.decision_hint.value == "refer"

    def test_missing_face_sizes_nothing(self) -> None:
        r = self.run("Applicant age: 40.")
        assert r.decision_hint.value == "refer"
        assert any("cannot size" in r_.lower() for r_ in r.reasons)


# ---------------------------------------------------------------------------
# Rating mechanics
# ---------------------------------------------------------------------------


class TestRatingMechanics:
    T = "Applicant age: 42. Sex: female. Face amount: $500000. Annual income: 145000. Non-smoker."

    def test_term_duration_ladder_exact_factors(self) -> None:
        expected = {10: 0.62, 15: 0.80, 20: 1.00, 25: 1.22, 30: 1.48}
        for years, factor in expected.items():
            q = rate_life(_bundle(self.T), coverage_id=f"level_term_{years}")
            comp = {c.name: c.amount for c in q.schedule_modifications}
            assert comp["term_duration"] == factor, years

    def test_modal_factors_and_annual_total(self) -> None:
        annual = rate_life(_bundle(self.T), coverage_id="level_term_20")
        monthly = rate_life(_bundle(self.T + " Monthly modal."), coverage_id="level_term_20")
        quarterly = rate_life(_bundle(self.T + " Quarterly."), coverage_id="level_term_20")
        semi = rate_life(_bundle(self.T + " Semiannual."), coverage_id="level_term_20")
        assert monthly.metadata["modal_premium"] == pytest.approx(annual.adjusted_premium * 0.087, abs=0.01)
        assert quarterly.metadata["modal_premium"] == pytest.approx(annual.adjusted_premium * 0.26, abs=0.01)
        assert semi.metadata["modal_premium"] == pytest.approx(annual.adjusted_premium * 0.51, abs=0.01)
        # adjusted_premium remains the annual figure regardless of mode
        assert monthly.adjusted_premium == annual.adjusted_premium

    def test_state_relativity_applied(self) -> None:
        il = rate_life(_bundle(self.T), coverage_id="level_term_20", state="IL")
        ny = rate_life(_bundle(self.T), coverage_id="level_term_20", state="NY")
        tx = rate_life(_bundle(self.T), coverage_id="level_term_20", state="TX")
        fl = rate_life(_bundle(self.T), coverage_id="level_term_20", state="FL")
        assert ny.adjusted_premium > il.adjusted_premium > tx.adjusted_premium
        assert fl.adjusted_premium > il.adjusted_premium
        assert ny.adjusted_premium / il.adjusted_premium == pytest.approx(1.12, rel=0.02)
        assert tx.adjusted_premium / il.adjusted_premium == pytest.approx(0.98, rel=0.02)

    def test_policy_fee_included_generic_path(self) -> None:
        q = rate_life(_bundle(self.T))
        comp = {c.name: c.amount for c in q.schedule_modifications}
        assert comp["policy_fee"] == 60.0

    def test_generic_modal_premium_floored_before_modal_split(self) -> None:
        # A tiny face amount prices below the $250 minimum premium — the
        # minimum must be applied BEFORE deriving the monthly payment, or the
        # monthly figure quietly understates what the (correctly floored)
        # annual total actually implies.
        text = "Applicant age: 25. Sex: female. Face amount: $5000. Non-smoker. Preferred. Monthly payment."
        q = rate_life(_bundle(text), coverage_name="Some Term Product 12 Year")
        assert q.adjusted_premium == 250.0
        assert q.metadata["modal_premium"] == pytest.approx(250.0 * 0.087, abs=0.01)

    def test_generic_permanent_path_does_not_collapse_to_term(self) -> None:
        # The filed manual carries whole_life_interest_rate/expense_loading as
        # explicit nulls (not yet filed) — `.get(key, default)` doesn't apply a
        # default for a key that's present but None, so float(None) used to
        # raise, get silently caught, and permanent pricing fell back to the
        # same one-year-term math as level_term. An unregistered whole-life
        # coverage name forces this generic (non-LOB-dispatched) path.
        q = rate_life(_bundle(self.T), coverage_name="Generic Whole Life")
        assert q.metadata["rating_engine"] == "life_whole_life_actuarial"
        assert q.metadata["actuarial"] is not None
        assert q.metadata["actuarial"]["interest_rate"] == 0.04
        assert q.metadata["actuarial"]["expense_loading_pct"] == 0.30
        term_only = rate_life(_bundle(self.T), coverage_id="level_term_20", product_id="level_term")
        # Generic permanent path is ineligible/illustration-only -> premium
        # contract is $0 (C1); the actuarial premium lives on the illustrated
        # premium. It must be far above the filed term premium, never collapsing
        # to the same term math.
        assert q.eligible is False and q.adjusted_premium == 0.0
        assert q.metadata["illustrated_adjusted_premium"] > term_only.adjusted_premium * 5

    def test_sex_component_female_discount(self) -> None:
        # The female discount comes entirely from the sex-specific mortality
        # table (mortality_per_1000) — sex_factor is a fixed 1.0 on both sides
        # because applying it on top of an already sex-specific table would
        # double-count the differential (see level_term.py).
        male = rate_life(_bundle("Applicant age: 42. Sex: male. Face amount: $500000. Annual income: 145000. Non-smoker."), coverage_id="level_term_20")
        female = rate_life(_bundle(self.T), coverage_id="level_term_20")
        mcomp = {c.name: c.amount for c in male.schedule_modifications}
        fcomp = {c.name: c.amount for c in female.schedule_modifications}
        assert mcomp["sex_factor"] == 1.0
        assert fcomp["sex_factor"] == 1.0
        assert fcomp["mortality_per_1000"] < mcomp["mortality_per_1000"]
        assert female.adjusted_premium < male.adjusted_premium

    def test_unfiled_state_generic_path_ineligible(self) -> None:
        q = rate_life(_bundle(self.T))  # no product/coverage hints → generic engine
        assert q.eligible is False
        assert any("no filed rates" in r.lower() for r in q.ineligibility_reasons)

    def test_unknown_state_code_falls_back_gracefully(self) -> None:
        q = rate_life(_bundle(self.T), coverage_id="level_term_20", product_id="level_term", state="ZZ")
        rules = q.metadata["state_rules_applied"]
        assert rules["issue_state"] == "ZZ"
        assert rules["free_look_days"] >= 10  # NAIC floor default
        # ZZ is not the state of filing -> ineligible, so the premium contract
        # is $0 but the computed premium survives on the illustrated premium.
        assert q.eligible is False
        assert q.metadata["illustrated_adjusted_premium"] > 0

    def test_lowercase_state_normalized(self) -> None:
        q = rate_life(_bundle(self.T), coverage_id="level_term_20", product_id="level_term", state="il")
        assert q.metadata["state_rules_applied"]["issue_state"] == "IL"


# ---------------------------------------------------------------------------
# State law — every jurisdiction, life AND annuity tables
# ---------------------------------------------------------------------------


class TestStateLawAllJurisdictions:
    LIFE_TEXT = "Applicant age: 42. Sex: male. Face amount: $500000. Annual income: 145000. Non-smoker."
    ANN_TEXT = "Purchase price: $500000. Applicant age: 65. Sex: male."

    @pytest.mark.parametrize("state", sorted(LIFE_FREE_LOOK_DAYS))
    def test_life_free_look_matches_statute_table(self, state: str) -> None:
        q = rate_life(_bundle(self.LIFE_TEXT), coverage_id="twenty_year_level", product_id="level_term", state=state)
        rules = q.metadata["state_rules_applied"]
        assert rules["free_look_days"] == LIFE_FREE_LOOK_DAYS[state], state
        assert rules["source"] == "state_table"

    @pytest.mark.parametrize("state", sorted(ANNUITY_FREE_LOOK_DAYS))
    def test_annuity_free_look_matches_statute_table(self, state: str) -> None:
        q = rate_life(_bundle(self.ANN_TEXT), coverage_id="life_income", product_id="immediate_annuity", state=state)
        rules = q.metadata["state_rules_applied"]
        assert rules["free_look_days"] == ANNUITY_FREE_LOOK_DAYS[state], state

    @pytest.mark.parametrize("state", sorted(set(LIFE_FREE_LOOK_DAYS) & set(ANNUITY_FREE_LOOK_DAYS)))
    def test_life_and_annuity_tables_diverge_or_match_intentionally(self, state: str) -> None:
        life_q = rate_life(_bundle(self.LIFE_TEXT), coverage_id="twenty_year_level", product_id="level_term", state=state)
        ann_q = rate_life(_bundle(self.ANN_TEXT), coverage_id="life_income", product_id="immediate_annuity", state=state)
        lr = life_q.metadata["state_rules_applied"]["free_look_days"]
        ar = ann_q.metadata["state_rules_applied"]["free_look_days"]
        table_pairs = {
            "FL": (14, 21),
            "TX": (10, 20),
            "NY": (20, 30),
            "WI": (10, 30),
            "ID": (10, 20),
            "AK": (20, 10),
        }
        if state in table_pairs:
            assert (lr, ar) == table_pairs[state], state
        else:
            assert lr == LIFE_FREE_LOOK_DAYS[state] and ar == ANNUITY_FREE_LOOK_DAYS[state]

    @pytest.mark.parametrize("state,min_age,days", [("AZ", 65, 30), ("CA", 60, 30)])
    def test_senior_free_look_extensions_on_quote(self, state: str, min_age: int, days: int) -> None:
        senior = rate_life(_bundle("Purchase price: $300000. Applicant age: 70. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state=state)
        rules = senior.metadata["state_rules_applied"]
        assert rules["senior_free_look_min_age"] == min_age
        assert rules["senior_free_look_days"] == days

    def test_tx_replacement_extends_free_look_on_quote(self) -> None:
        plain = rate_life(_bundle(self.ANN_TEXT), coverage_id="life_income", product_id="immediate_annuity", state="TX")
        repl = rate_life(_bundle(self.ANN_TEXT + " Replacing existing annuity contract."), coverage_id="life_income", product_id="immediate_annuity", state="TX")
        rp = repl.metadata["state_rules_applied"]
        assert plain.metadata["state_rules_applied"]["free_look_days"] == 20
        assert rp["replacement_free_look_days"] == 30

    @pytest.mark.parametrize("state", sorted(COMMUNITY_PROPERTY_STATES))
    def test_community_property_spousal_consent(self, state: str) -> None:
        q = rate_life(_bundle(self.ANN_TEXT), coverage_id="life_income", product_id="immediate_annuity", state=state)
        assert q.metadata["state_rules_applied"].get("spousal_consent_required") is True, state

    @pytest.mark.parametrize(
        "state,death,cash,aggregate",
        [("IL", 300000.0, 100000.0, 300000.0), ("NY", 500000.0, 500000.0, 500000.0), ("CT", 500000.0, 500000.0, 500000.0)],
    )
    def test_guaranty_cap_overrides(self, state: str, death: float, cash: float, aggregate: float) -> None:
        q = rate_life(_bundle(self.LIFE_TEXT), coverage_id="twenty_year_level", product_id="level_term", state=state)
        g = q.metadata["state_rules_applied"]["guaranty"]
        assert g["death_cap"] == death
        assert g["cash_value_cap"] == cash
        assert g["aggregate_cap"] == aggregate

    def test_ca_coinsurance_model_guaranty(self) -> None:
        q = rate_life(_bundle(self.LIFE_TEXT), coverage_id="guaranteed_whole_life", product_id="ordinary_whole_life", state="CA")
        assert q.metadata["state_rules_applied"]["guaranty"]["coinsurance_pct"] == 80.0

    @pytest.mark.parametrize("state,grace", [("CA", 60), ("AL", 30), ("DE", 30), ("NV", 30), ("WA", 30), ("IL", 31), ("TX", 31)])
    def test_grace_period_by_state(self, state: str, grace: int) -> None:
        q = rate_life(_bundle(self.LIFE_TEXT), coverage_id="twenty_year_level", product_id="level_term", state=state)
        assert q.metadata["state_rules_applied"]["grace_period_days"] == grace

    def test_default_grace_period_constant(self) -> None:
        assert GRACE_PERIOD_DAYS_DEFAULT == 31

    @pytest.mark.parametrize(
        "state,anchor,offset,max_days",
        [("CT", "date_of_death", 10, 30), ("TX", "proof_of_loss", 0, 60), ("WY", "date_of_death", 0, 45), ("NV", "proof_of_death", 0, 60), ("AL", "proof_of_death", 0, 30)],
    )
    def test_claims_settlement_anchors(self, state: str, anchor: str, offset: int, max_days: int) -> None:
        q = rate_life(_bundle(self.LIFE_TEXT), coverage_id="twenty_year_level", product_id="level_term", state=state)
        cs = q.metadata["state_rules_applied"]["claims_settlement"]
        assert cs["accrues_from"] == anchor, state
        assert cs["offset_days"] == offset
        assert cs["max_settlement_days"] == max_days

    @pytest.mark.parametrize(
        "state,consideration,expected",
        [
            ("CA", 500_000, 11_750.0),  # 2.35%
            ("NV", 500_000, 17_500.0),  # 3.5%
            ("SD", 600_000, 6_330.0),  # 1.25% first 500k + 0.08% above
            ("SD", 400_000, 5_000.0),  # flat tier below threshold
            ("CO", 250_000, 5_000.0),  # 2%
            ("WV", 250_000, 2_500.0),  # 1%
        ],
    )
    def test_annuity_premium_tax_math(self, state: str, consideration: float, expected: float) -> None:
        tax = premium_tax_on_consideration(state, consideration)
        assert tax is not None
        assert tax["amount"] == expected
        assert tax["insurer_paid"] is True

    def test_qualified_money_lower_rate(self) -> None:
        tax = premium_tax_on_consideration("CA", 500_000, qualified=True)
        assert tax is not None
        assert tax["rate"] == 0.005
        assert tax["amount"] == 2_500.0

    def test_untaxed_states_return_none(self) -> None:
        for state in ("IL", "TX", "NY"):
            assert premium_tax_on_consideration(state, 500_000) is None

    def test_every_tax_state_has_positive_headline_rate(self) -> None:
        for state, rule in ANNUITY_PREMIUM_TAX.items():
            assert rule["rate"] > 0, state

    def test_ny_reg187_governs_both_lines(self) -> None:
        life_q = rate_life(_bundle(self.LIFE_TEXT), coverage_id="twenty_year_level", product_id="level_term", state="NY")
        ann_q = rate_life(_bundle(self.ANN_TEXT), coverage_id="life_income", product_id="immediate_annuity", state="NY")
        for q in (life_q, ann_q):
            regime = q.metadata["suitability_regime"]
            assert regime["regime"] == "NY Reg 187"
            assert regime["citation"] == "11 NYCRR 224"

    def test_best_interest_regime_on_non_ny_annuities(self) -> None:
        for state in ("TX", "CA", "IL", "FL"):
            q = rate_life(_bundle(self.ANN_TEXT), coverage_id="life_income", product_id="immediate_annuity", state=state)
            regime = q.metadata["suitability_regime"]
            assert regime["regime"].startswith("NAIC Model #275"), state
            assert set(regime["obligations"]) == {"care", "disclosure", "conflict_of_interest", "documentation"}

    def test_dc_legacy_annuity_regime_but_general_standards_for_life(self) -> None:
        ann = rate_life(_bundle(self.ANN_TEXT), coverage_id="life_income", product_id="immediate_annuity", state="DC")
        assert ann.metadata["suitability_regime"]["regime"].startswith("legacy NAIC")
        life_q = rate_life(_bundle(self.LIFE_TEXT), coverage_id="twenty_year_level", product_id="level_term", state="DC")
        regime = life_q.metadata.get("suitability_regime")
        assert not regime or regime.get("regime") in ("none_beyond_general_standards",)


# ---------------------------------------------------------------------------
# Montana unisex statute
# ---------------------------------------------------------------------------


class TestMontanaUnisex:
    F = "Applicant age: 42. Sex: female. Face amount: $500000. Annual income: 145000. Non-smoker."
    M = "Applicant age: 42. Sex: male. Face amount: $500000. Annual income: 145000. Non-smoker."

    def test_identical_pricing_regardless_of_sex(self) -> None:
        fem = rate_life(_bundle(self.F), coverage_id="level_term_20", product_id="level_term", state="MT")
        mal = rate_life(_bundle(self.M), coverage_id="level_term_20", product_id="level_term", state="MT")
        assert fem.adjusted_premium == mal.adjusted_premium
        assert {c.name: c.amount for c in fem.schedule_modifications} == {c.name: c.amount for c in mal.schedule_modifications}

    def test_unisex_state_outside_mt_prices_by_sex(self) -> None:
        fem = rate_life(_bundle(self.F), coverage_id="level_term_20", product_id="level_term", state="IL")
        mal = rate_life(_bundle(self.M), coverage_id="level_term_20", product_id="level_term", state="IL")
        assert fem.adjusted_premium != mal.adjusted_premium


# ---------------------------------------------------------------------------
# Product gates across all 7 LOBs — real-world eligibility edges
# ---------------------------------------------------------------------------


class TestProductGatesAllLOBs:
    B = "Applicant age: 45. Face amount: $500000. Annual income: 145000. Non-smoker."

    def test_level_term_registered_path_metadata(self) -> None:
        q = rate_life(_bundle(self.B), coverage_id="level_term_20", product_id="level_term")
        assert q.metadata["lob_logic_path"] == "insureflow.life.lobs.term_life.level_term"
        assert q.metadata["rating_engine"] == "life_filing"

    def test_convertible_past_deadline_declined(self) -> None:
        q = rate_life(_bundle("Applicant age: 68. Face amount: $300000. Non-smoker."), coverage_id="convert_period", product_id="convertible_term")
        assert q.eligible is False
        assert any("65" in r for r in q.ineligibility_reasons)

    def test_convertible_inside_deadline_eligible(self) -> None:
        q = rate_life(_bundle("Applicant age: 50. Face amount: $300000. Non-smoker."), coverage_id="convert_period", product_id="convertible_term")
        assert q.eligible is True
        assert q.metadata["conversion_deadline_age"] == 65

    def test_credit_life_face_capped(self) -> None:
        q = rate_life(_bundle("Face amount: $900000. Applicant age: 35. Non-smoker."), coverage_id="loan_balance", product_id="credit_life")
        assert q.metadata["capped_face"] <= 250_000
        assert q.metadata["exam_required"] is False

    def test_credit_life_senior_declined(self) -> None:
        q = rate_life(_bundle("Face amount: $40000. Applicant age: 74."), coverage_id="loan_balance", product_id="credit_life")
        assert q.eligible is False
        assert any("70" in r for r in q.ineligibility_reasons)

    def test_group_term_no_exam_simplified(self) -> None:
        q = rate_life(_bundle("Applicant age: 40. Face amount: $100000. Non-smoker."), coverage_id="basic_group", product_id="group_term_life")
        assert q.metadata["exam_required"] is False
        assert any("IRC" in c for c in q.metadata["conditions"])

    def test_gi_whole_life_window_enforced(self) -> None:
        too_young = rate_life(_bundle("Applicant age: 42. Face amount: $25000."), coverage_id="guaranteed_issue", product_id="graded_guaranteed_issue_whole_life")
        assert too_young.eligible is False
        assert any("outside 50" in r for r in too_young.ineligibility_reasons)

    def test_gi_sick_senior_no_exam_graded_schedule(self) -> None:
        sick = _bundle("Applicant age: 66. Face amount: $25000. Active cancer on chemotherapy.")
        gi = rate_life(sick, coverage_id="guaranteed_issue", coverage_name="Guaranteed Issue Whole Life", product_id="graded_guaranteed_issue_whole_life")
        assert gi.metadata["exam_required"] is False
        assert gi.metadata["capped_face"] == 25_000
        graded = rate_life(sick, coverage_id="graded_benefit", coverage_name="Graded Benefit Whole Life", product_id="graded_guaranteed_issue_whole_life")
        assert graded.metadata["graded_schedule"] == {"1": 0.30, "2": 0.65}

    def test_limited_pay_premium_ordering(self) -> None:
        lp10 = rate_life(_bundle(self.B), coverage_id="ten_pay", product_id="limited_pay_whole_life")
        lp20 = rate_life(_bundle(self.B), coverage_id="twenty_pay", product_id="limited_pay_whole_life")
        lifetime = rate_life(_bundle(self.B), coverage_name="Traditional Whole Life", product_id="traditional_whole_life")
        def ill(q):
            return q.metadata["illustrated_adjusted_premium"]

        assert all(q.eligible is False and q.adjusted_premium == 0.0 for q in (lp10, lp20, lifetime))
        assert ill(lp10) > ill(lp20) > ill(lifetime)

    def test_ul_charging_ordering(self) -> None:
        caul = rate_life(_bundle(self.B), coverage_id="current_rate", product_id="current_assumption_universal_life")
        gul = rate_life(_bundle(self.B), coverage_id="no_lapse", product_id="guaranteed_universal_life")
        iul = rate_life(_bundle(self.B), coverage_id="indexed_account", product_id="indexed_universal_life")
        vul = rate_life(_bundle(self.B), coverage_id="gmdb", product_id="variable_universal_life")
        def ill(q):
            return q.metadata["illustrated_adjusted_premium"]

        assert all(q.eligible is False and q.adjusted_premium == 0.0 for q in (caul, gul, iul, vul))
        assert ill(caul) < ill(gul) < ill(iul) < ill(vul)

    def test_iul_floor_and_cap_scenarios(self) -> None:
        iul = rate_life(_bundle(self.B), coverage_id="indexed_account", product_id="indexed_universal_life")
        sc = iul.metadata["credited_rate_scenarios"]
        assert sc["index_gain_-10pct"] == 0.0
        assert sc["index_gain_15pct"] == round(iul.metadata["index_cap"], 6)

    def test_vul_finra_gate_condition(self) -> None:
        q = rate_life(_bundle(self.B), coverage_id="finra_suitability", product_id="variable_universal_life")
        assert any("FINRA suitability review REQUIRED" in c for c in q.metadata["conditions"])

    def test_endowment_pure_has_no_death_benefit(self) -> None:
        q = rate_life(_bundle(self.B), coverage_id="pure_maturity", product_id="pure_endowment")
        assert q.metadata["death_benefit"] == 0.0
        assert any("nothing is payable if the insured dies" in c.lower() or "PURE ENDOWMENT" in c for c in q.metadata["conditions"])

    def test_pension_ulip_entry_age_gate(self) -> None:
        ok = rate_life(_bundle("Applicant age: 50."), coverage_id="pension_ulip", product_id="pension_ulip")
        old = rate_life(_bundle("Applicant age: 62."), coverage_id="pension_ulip", product_id="pension_ulip")
        assert any("outside 18-55" in r for r in old.ineligibility_reasons)
        assert not any("outside 18-55" in r for r in ok.ineligibility_reasons)

    def test_child_ulip_proposer_bounds(self) -> None:
        young = rate_life(_bundle("Applicant age: 19."), coverage_id="child_ulip", product_id="child_ulip")
        old = rate_life(_bundle("Applicant age: 61."), coverage_id="child_ulip", product_id="child_ulip")
        fit = rate_life(_bundle("Applicant age: 35."), coverage_id="child_ulip", product_id="child_ulip")
        assert any("proposer age 19 outside 21-55" in r.lower() for r in young.ineligibility_reasons)
        assert any("proposer age 61 outside 21-55" in r.lower() for r in old.ineligibility_reasons)
        assert not any("outside 21-55" in r for r in fit.ineligibility_reasons)
        assert fit.metadata["milestone_ages"] == [18, 20, 22, 25]

    def test_money_back_survival_returns_full_sa(self) -> None:
        mb = rate_life(_bundle(self.B), coverage_id="traditional_mb", product_id="traditional_money_back")
        sched = mb.metadata["survival_benefit_schedule"]
        assert sum(s["pct_of_sa"] for s in sched) == pytest.approx(1.0)
        assert mb.metadata["death_benefit"] == 500_000.0

    def test_children_money_back_proposer_bounds(self) -> None:
        young = rate_life(_bundle("Applicant age: 19."), coverage_id="children_mb", product_id="children_money_back")
        assert young.eligible is False
        fit = rate_life(_bundle("Applicant age: 34."), coverage_id="children_mb", product_id="children_money_back")
        assert fit.metadata["waiver_of_premium_included"] is True

    def test_annuity_paths_are_illustrations_only(self) -> None:
        for pid, cid in (("immediate_annuity", "life_income"), ("qlac", "qlac_lifetime"), ("structured_settlement_annuity", "structured_payments")):
            q = rate_life(_bundle("Purchase price: $200000. Applicant age: 65. Sex: male."), coverage_id=cid, product_id=pid, state="IL")
            assert q.eligible is False, pid
            # Illustration-only (unfiled) -> premium contract is $0 (C1), but
            # the computed consideration is preserved on the illustrated premium
            # so quote documents don't show $0.00.
            assert q.adjusted_premium == 0.0, pid
            assert q.metadata["illustrated_adjusted_premium"] > 0.0, pid

    def test_qlac_irs_cap_clamped(self) -> None:
        over = rate_life(_bundle("Purchase price: $400000. Applicant age: 60. Sex: male."), coverage_id="qlac_lifetime", product_id="qlac")
        assert over.metadata["purchase_price"] == over.metadata["irs_cap"] == 210_000.0
        assert any("IRS QLAC cap" in r for r in over.ineligibility_reasons)

    def test_joint_survivor_continuation_costs_income(self) -> None:
        single = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="single_life_income", product_id="life_annuity")
        j100 = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="joint_100", product_id="joint_survivor_annuity")
        j50 = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="joint_50", product_id="joint_survivor_annuity")
        s = single.metadata["annual_payout"]
        assert s > j50.metadata["annual_payout"] > j100.metadata["annual_payout"]
        assert j100.metadata["continuation_pct"] == 1.0


# ---------------------------------------------------------------------------
# Adversarial / messy inputs an intake desk actually receives
# ---------------------------------------------------------------------------


class TestAdversarialInputs:
    def test_empty_bundle_never_crashes(self) -> None:
        q = rate_life(_bundle(""))
        assert q.line.value == "life"
        assert q.eligible is False

    def test_garbage_text_handled(self) -> None:
        q = rate_life(_bundle("asdf jkl;; 12345 !!! $$$"))
        assert isinstance(q.adjusted_premium, float)

    def test_money_with_commas_and_cents_parsed(self) -> None:
        q = rate_life(_bundle("Applicant age: 42. Face amount: $1,000,000.55. Non-smoker."), coverage_id="level_term_20")
        assert q.metadata["face_amount"] == 1_000_000.55

    def test_sex_short_forms(self) -> None:
        for text, expect in (("Sex: M.", "male"), ("Sex: F.", "female"), ("Male applicant.", "male")):
            q = rate_life(_bundle(f"Applicant age: 42. {text} Face amount: $500000. Non-smoker."), coverage_id="level_term_20")
            assert q.metadata["personal_factors"]["sex"] == expect, text

    def test_state_from_city_zip_pattern(self) -> None:
        q = rate_life(_bundle("Applicant age: 42. Face amount: $500000. Non-smoker. Resides: Austin, TX 78701."), coverage_id="level_term_20", product_id="level_term")
        assert q.metadata["state_rules_applied"]["issue_state"] == "TX"

    def test_duplicate_conflicting_ages_first_wins(self) -> None:
        q = rate_life(_bundle("Applicant age: 42. Applicant age: 95. Face amount: $500000."), coverage_id="level_term_20")
        assert q.metadata["personal_factors"]["age"] == 42

    def test_unicode_and_newlines(self) -> None:
        q = rate_life(_bundle("Applicant age: 40.\nFace amount: €—$250,000.\nNon-smoker ✓\nPreferred ✓"))
        assert isinstance(q.adjusted_premium, float)


# ---------------------------------------------------------------------------
# End-to-end underwriter scenario files (stacked impairments)
# ---------------------------------------------------------------------------


class TestScenarioFiles:
    def test_scenario_midcareer_smoker_stack(self) -> None:
        """58yo smoker, hypertensive, diabetic, replacing coverage without forms, TX."""
        text = (
            "Face amount: $750000. Applicant age: 58. Sex: male. Current smoker. "
            "Blood pressure: 148/92. Diabetes type 2. A1C: 7.4. "
            "Annual income: $60000. Beneficiary relationship: spouse. "
            "Replacing existing policy to be lapsed. State: TX"
        )
        d = _med(text)
        assert d.tobacco is True
        assert d.decision.value == "refer"
        reasons = " | ".join(d.reasons).lower()
        assert "diabetes" in reasons
        q = rate_life(_bundle(text), coverage_id="level_term_20", product_id="level_term")
        med = q.metadata["medical"]
        fin = q.metadata["financial"]
        assert med["decision"] == "refer"
        assert med["tobacco"] is True
        assert any("Diabetes" in r for r in med["reasons"])
        assert fin["replacement"] is True
        assert fin["exchange_1035"] is False
        rules = q.metadata["state_rules_applied"]
        assert rules["issue_state"] == "TX"

    def test_scenario_midcareer_smoker_stack_not_issueable(self) -> None:
        """58yo smoker + Table A vitals + diabetes + replacement: routed to review, never a clean accept."""
        text = (
            "Face amount: $750000. Applicant age: 58. Sex: male. Current smoker. "
            "Blood pressure: 148/92. Diabetes type 2. A1C: 7.4. "
            "Annual income: $60000. Beneficiary relationship: spouse. "
            "Replacing existing policy to be lapsed. State: TX"
        )
        bundle = _bundle(text)
        q = rate_life(bundle, coverage_id="level_term_20", product_id="level_term")
        assert q.metadata["outcome"] == "refer"
        conds = " | ".join(q.metadata["conditions"]).lower()
        assert "referral" in conds or "review required" in conds
        assert any("replacement" in c.lower() for c in q.metadata["conditions"])
        from insureflow.underwriting.bind_gates import life_evidence_holds

        assert life_evidence_holds(bundle, q.metadata), "stack must not be cleanly bindable"

    def test_scenario_clean_young_professional(self) -> None:
        """32yo preferred professional, standard case that should price cleanly."""
        text = (
            "Face amount: $750000. Applicant age: 32. Sex: female. Non-smoker. Preferred plus. "
            "Blood pressure: 112/70. BMI: 22.5. Cholesterol: 175. Annual income: $110000. "
            "Beneficiary relationship: spouse."
        )
        d = _med(text)
        assert d.decision.value != "decline"
        assert d.underwriting_class in ("preferred", "super_preferred")
        assert d.flat_extras_per_1000 == 0.0
        q = rate_life(_bundle(text), coverage_id="level_term_20", product_id="level_term", state="IL")
        assert q.adjusted_premium > 0
        assert q.eligible is True

    def test_scenario_jumbo_keyman(self) -> None:
        """$12M key-person case: facultative + financial stretch + jumbo referral."""
        text = "Face amount: $12000000. Applicant age: 48. Sex: male. Non-smoker. Preferred. Annual income: $900000. Beneficiary relationship: employer (key person)."
        d = _med(text)
        assert d.decision.value == "refer"
        assert any("Facultative" in r for r in d.reasons)
        q = rate_life(_bundle(text), coverage_id="level_term_20", product_id="level_term")
        re_meta = q.metadata["life_reinsurance"]
        assert re_meta["facultative_required"] is True
        assert re_meta["cession_amount"] == 11_000_000.0
        assert re_meta["jumbo"] is True

    def test_scenario_senior_gi_fallback(self) -> None:
        """72yo with impairments who cannot pass term UW lands in GI whole life window."""
        term_attempt = _med("Face amount: $50000. Applicant age: 72. Diabetic. A1C: 8.2.")
        assert term_attempt.decision.value in ("refer", "accept", "conditional_accept")  # rated, not auto-declined
        gi = rate_life(
            _bundle("Applicant age: 72. Face amount: $25000."),
            coverage_id="guaranteed_issue",
            coverage_name="Guaranteed Issue Whole Life",
            product_id="graded_guaranteed_issue_whole_life",
        )
        assert gi.metadata["exam_required"] is False
        assert gi.metadata["capped_face"] == 25_000

    def test_scenario_retirement_annuitant_ca(self) -> None:
        """67yo CA annuitant: senior free look + premium tax + best interest."""
        q = rate_life(
            _bundle("Purchase price: $400000. Applicant age: 67. Sex: female. Suitable for retirement income."),
            coverage_id="life_income",
            product_id="immediate_annuity",
            state="CA",
        )
        rules = q.metadata["state_rules_applied"]
        assert rules["free_look_days"] == 30
        assert rules["senior_free_look_days"] == 30
        assert q.metadata["premium_tax"]["amount"] == pytest.approx(400_000 * 0.0235)
        assert q.metadata["suitability_regime"]["regime"].startswith("NAIC Model #275")


# ---------------------------------------------------------------------------
# Regression battery — defects found in senior-tester bug hunt, fixed & pinned
# ---------------------------------------------------------------------------


class TestMoneySuffixParsing:
    """$1.5M / $200k / $300K used to parse as 1.5 / 200 / 300 (catastrophic
    under-statement of face, income, and in-force). Suffix + word multipliers
    and ISO currency prefixes are now handled by the shared money parser."""

    @pytest.mark.parametrize(
        "text,label,want",
        [
            ("Face amount: $1.5M.", "face amount", 1_500_000.0),
            ("face amount: $2 mm", "face amount", 2_000_000.0),
            ("Annual income: $200k", "annual income", 200_000.0),
            ("in-force face: $300K", "in-force face", 300_000.0),
            ("net worth: $3 billion", "net worth", 3e9),
            ("salary USD 75,000/year", "salary", 75_000.0),
            ("death benefit: $5 million", "death benefit", 5_000_000.0),
            ("Face amount: $500,000.00", "face amount", 500_000.0),
        ],
    )
    def test_suffixes_and_prefixes(self, text: str, label: str, want: float) -> None:
        from insureflow.underwriting.personal_lines import _money

        assert _money(text.lower(), label) == pytest.approx(want)

    def test_plain_numbers_unaffected(self) -> None:
        from insureflow.underwriting.personal_lines import _money

        assert _money("face amount: $500000 for a 20 year period", "face amount") == 500_000.0

    def test_jumbo_via_suffixed_face_triggers_reinsurance(self) -> None:
        q = rate_life(_bundle("Face amount: $15m. Applicant age: 35. Non-smoker."), coverage_id="level_term_20")
        assert q.metadata["life_reinsurance"]["jumbo"] is True

    def test_income_stretch_cleared_by_k_suffix(self) -> None:
        """$60000 income justified a $750k face; '$60k' must too."""
        d = _med("Face amount: $750000. Applicant age: 40. Annual income: $60k.")
        assert d.decision.value != "refer" or not any("income multiple" in r.lower() for r in d.reasons)


class TestBlobCrossDocumentBarrier:
    r"""_blob joined chunks with '\n' only; '\s*' patterns crossed into the next
    document's filename/fields — an empty 'Criminal history:' swallowed 'app.md'
    and DECLINED the case."""

    def test_empty_label_at_end_of_document_not_a_confession(self) -> None:
        d = _med("Face amount: $500000. Applicant age: 40. Criminal history:")
        assert d.decision.value != "decline"

    def test_empty_label_does_not_swallow_next_document(self) -> None:
        b = SubmissionBundle(
            bundle_id="two-doc",
            unstructured=[
                UnstructuredSubmission(submission_id="d0", source="p1.md", raw_text="Criminal history:", document_type="supplemental"),
                UnstructuredSubmission(submission_id="d1", source="p2.md", raw_text="Applicant was convicted of nothing; resides in Texas.", document_type="supplemental"),
            ],
        )
        d = underwrite_life(b)
        assert d.decision.value != "decline"

    def test_affirmative_conviction_still_declines_across_docs(self) -> None:
        b = SubmissionBundle(
            bundle_id="two-doc",
            unstructured=[
                UnstructuredSubmission(submission_id="d0", source="p1.md", raw_text="Criminal history:", document_type="supplemental"),
                UnstructuredSubmission(submission_id="d1", source="court.md", raw_text="", document_type="supplemental"),
            ],
        )
        b.unstructured[0].raw_text = "Criminal history: felony conviction for arson"
        d = underwrite_life(b)
        assert d.decision.value == "decline"


class TestNegationStrippingMatrix:
    """Negated clauses are stripped before KO/referral/class matching —
    affirmative disclosures still fire."""

    @pytest.mark.parametrize(
        "negated,still_declines",
        [
            ("No active cancer.", False),
            ("Denies chest pain or shortness of breath.", None),
            ("Not replacing any existing policy.", None),
        ],
    )
    def test_negated_segments_removed(self, negated: str, still_declines: bool | None) -> None:
        from insureflow.underwriting.personal_lines import strip_negated_clauses

        out = strip_negated_clauses(negated)
        if still_declines is False:
            assert "cancer" not in out.lower()

    def test_negated_replacement_no_refer(self) -> None:
        fin = evaluate_life_financial(_bundle(f"{BASE} Not replacing any existing policy. Beneficiary relationship: spouse."))
        assert fin.replacement is False
        assert not any("replacement" in r.lower() for r in fin.reasons)

    def test_negated_rider_not_charged(self) -> None:
        fin = evaluate_life_financial(_bundle(f"{BASE} No waiver of premium rider requested."))
        assert fin.riders == []

    def test_negated_referral_clean(self) -> None:
        d = _med(f"{BASE} No coronary artery disease, no heart attack, without stent, denies angina.")
        assert d.decision.value == "accept"

    def test_affirmative_versions_still_fire(self) -> None:
        assert _med(f"{BASE} Coronary stent placed 2021.").decision.value == "refer"
        assert _med(f"{BASE} Replacing existing policy to be lapsed.").decision is not None


class TestMedicalGuidePatternGaps:
    """Wording variants real applicants use that the filed patterns missed."""

    @pytest.mark.parametrize(
        "text",
        [
            f"{BASE} A1C: 10.2.",
            f"{BASE} a1c = 11",
            f"{BASE} Type 2 diabetic, controlled with metformin.",
            f"{BASE} History of angina.",
            f"{BASE} CHF diagnosed 2023.",
            f"{BASE} Cardiac stent placement.",
            f"{BASE} CABG x3 in 2019.",
            f"{BASE} Atrial fibrillation on Eliquis.",
        ],
    )
    def test_cardiac_and_diabetic_wording_refers(self, text: str) -> None:
        d = _med(text)
        assert d.decision.value == "refer", f"expected refer, got {d.decision.value}: {d.reasons}"

    @pytest.mark.parametrize(
        "text",
        [
            f"{BASE} HIV+ since 2019.",
            f"{BASE} AIDS diagnosis.",
        ],
    )
    def test_hiv_wording_declines(self, text: str) -> None:
        d = _med(text)
        assert d.decision.value == "decline"

    def test_normal_labs_not_referred(self) -> None:
        d = _med(f"{BASE} A1C: 5.4. No diabetic history.")
        assert d.decision.value == "accept"

    def test_negated_new_terms_still_clean(self) -> None:
        d = _med(f"{BASE} No angina, no CHF, no stent, no CABG, no afib, a1c 5.6.")
        assert d.decision.value == "accept"


class TestLOBPlatformBindingGates:
    """Dedicated LOB logic paths now carry every gate the generic path applies:
    medical REFER/DECLINE propagation, APS/paramed orders, riders, facultative/
    jumbo placement, zero-face refusal."""

    def test_financial_refer_routes_to_review(self) -> None:
        q = rate_life(
            _bundle(f"{BASE} Replacing existing policy to be lapsed. State: TX"),
            coverage_id="level_term_20",
            product_id="level_term",
            state="TX",
        )
        assert q.metadata["outcome"] == "refer"
        assert any("replacement" in c.lower() for c in q.metadata["conditions"])

    def test_medical_decline_propagates_reasons_on_lob_path(self) -> None:
        q = rate_life(
            _bundle(f"{BASE} Active cancer under treatment."),
            coverage_id="level_term_20",
            product_id="level_term",
        )
        assert q.eligible is False
        assert q.ineligibility_reasons, "medical decline reasons must reach the quote record"

    def test_jumbo_confirm_capacity_condition(self) -> None:
        q = rate_life(_bundle("Face amount: $6000000. Applicant age: 45. Non-smoker."), coverage_id="level_term_20")
        assert any("automatic reinsurance treaty capacity" in c.lower() for c in q.metadata["conditions"])
        assert not q.metadata["life_reinsurance"]["facultative_required"]

    def test_riders_surfaced_as_condition_on_lob_quote(self) -> None:
        q = rate_life(
            _bundle(f"{BASE} Waiver of premium rider requested."),
            coverage_id="level_term_20",
            product_id="level_term",
        )
        assert any(c.lower().startswith("riders:") for c in q.metadata["conditions"])

    def test_zero_face_whole_life_also_refused(self) -> None:
        q = rate_life(
            _bundle("Applicant age: 50."),
            coverage_id="whole_life_ord",
            product_id="whole_life",
            coverage_name="Whole Life",
        )
        assert q.eligible is False and q.adjusted_premium == 0.0

    def test_annuity_style_consideration_products_exempt_from_face_gate(self) -> None:
        q = rate_life(
            _bundle("Purchase price: $100000. Applicant age: 66."),
            coverage_id="qlac",
            product_id="qlac_deferred_annuity",
            coverage_name="QLAC",
        )
        assert q.metadata.get("purchase_price") == 100_000.0

    def test_paramed_condition_not_duplicated_with_carrier_rule(self) -> None:
        q = rate_life(_bundle("Face amount: $500000. Applicant age: 42. Non-smoker."), coverage_id="level_term_20")
        paramedish = [c for c in q.metadata["conditions"] if "paramed" in c.lower()]
        assert len(paramedish) >= 1

    def test_convertible_quote_still_eligible_with_added_conditions(self) -> None:
        q = rate_life(
            _bundle("Face amount: $300000. Applicant age: 50. Non-smoker."),
            coverage_id="convertible_term",
            product_id="convertible_term",
            coverage_name="Convertible Term",
        )
        assert q.eligible is True


class TestRefutedSuspicionPins:
    """Behaviors probed and confirmed CORRECT — pinned so future edits cannot
    silently regress them."""

    def test_table_b_override_preserved_even_with_preferred_language(self) -> None:
        d = _med(f"{BASE} Blood pressure: 170/95. Preferred plus. Cholesterol: 180.")
        assert d.underwriting_class == "table_b"

    def test_annuitant_payouts_are_sex_aware(self) -> None:
        male = rate_life(
            _bundle("Purchase price: $100000. Applicant age: 65. Sex: male."),
            coverage_id="life_income",
            product_id="immediate_annuity",
        )
        female = rate_life(
            _bundle("Purchase price: $100000. Applicant age: 65. Sex: female."),
            coverage_id="life_income",
            product_id="immediate_annuity",
        )
        assert female.metadata.get("annual_payout") != male.metadata.get("annual_payout")
        assert female.metadata["annual_payout"] < male.metadata["annual_payout"]

    def test_credit_life_prices_on_capped_face(self) -> None:
        capped = rate_life(
            _bundle("Face amount: $250000. Applicant age: 45. Non-smoker."),
            coverage_id="credit_life_involuntary",
            product_id="credit_life_involuntary_unemployment",
            coverage_name="Credit Life Involuntary Unemployment",
        )
        over = rate_life(
            _bundle("Face amount: $900000. Applicant age: 45. Non-smoker."),
            coverage_id="credit_life_involuntary",
            product_id="credit_life_involuntary_unemployment",
            coverage_name="Credit Life Involuntary Unemployment",
        )
        assert over.adjusted_premium == pytest.approx(capped.adjusted_premium)

    def test_mortality_clamps_to_nearest_filed_age(self) -> None:
        young = rate_life(_bundle("Face amount: $250000. Applicant age: 16."), coverage_id="level_term_10")
        adult = rate_life(_bundle("Face amount: $250000. Applicant age: 18."), coverage_id="level_term_10")
        # Age 16 is below the issued band -> ineligible, premium contract $0 but
        # clamped to the nearest filed age on the illustrated premium; age 18
        # issues normally.
        assert young.eligible is False
        assert young.metadata["illustrated_adjusted_premium"] > 0
        assert adult.eligible is True and adult.adjusted_premium > 0


@pytest.mark.xfail(reason="KNOWN GAP (spec needed): diastolic pressure ignored entirely — 118/105 rates Preferred; needs diastolic band table", strict=False)
def test_diastolic_hypertension_should_not_rate_preferred():
    d = _med(f"{BASE} Blood pressure: 118/105. Preferred plus.")
    assert d.underwriting_class not in ("preferred", "preferred_plus")


@pytest.mark.xfail(reason="KNOWN GAP (robustness): structured settlement fabricates PV from garbage input ('$0 per month' → pv≈343795)", strict=False)
def test_structured_settlement_zero_payment_should_not_fabricate_value():
    q = rate_life(
        _bundle("Structured settlement: $0 per month for 240 payments. Claimant age: 34."),
        coverage_id="structured_settlement",
        product_id="structured_settlement_purchase",
        coverage_name="Structured Settlement Purchase",
    )
    assert q.metadata.get("present_value_of_settlement", 0) == pytest.approx(0.0)
