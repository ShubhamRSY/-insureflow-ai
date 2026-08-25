"""End-to-end tests for dedicated LOB/Product/Coverage logic paths.

Verifies the confirmed architecture: every Term Life and Whole Life product
has its own logic path, state rules are applied INSIDE each path (stamped as
state_rules_applied), and unregistered products still fall back to generic
family pricing.
"""

from __future__ import annotations

import json

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
        # LOB 1 — Term Life (9)
        "level_term",
        "decreasing_term",
        "mortgage_life",
        "increasing_term",
        "renewable_term",
        "convertible_term",
        "rop_term",
        "group_term_life",
        "credit_life",
        # LOB 2 — Whole Life (7)
        "traditional_whole_life",
        "limited_pay_whole_life",
        "single_premium_whole_life",
        "participating_whole_life",
        "non_participating_whole_life",
        "modified_whole_life",
        "graded_guaranteed_issue_whole_life",
        # LOB 3 — Universal Life (4)
        "guaranteed_universal_life",
        "indexed_universal_life",
        "variable_universal_life",
        "current_assumption_universal_life",
        # LOB 4 — Endowment (3)
        "pure_endowment",
        "full_endowment",
        "guaranteed_fixed_endowment",
        # LOB 5 — ULIP (6)
        "single_premium_ulip",
        "regular_premium_ulip",
        "ulip_type_i",
        "ulip_type_ii",
        "pension_ulip",
        "child_ulip",
        # LOB 6 — Money-Back (3)
        "traditional_money_back",
        "with_profit_money_back",
        "children_money_back",
        # LOB 7 — Annuity (9)
        "immediate_annuity",
        "deferred_annuity",
        "fixed_annuity",
        "variable_annuity",
        "indexed_annuity",
        "life_annuity",
        "joint_survivor_annuity",
        "qlac",
        "structured_settlement_annuity",
    }
    assert len(PRODUCT_LOGIC_PATHS) == 41
    assert expected == set(PRODUCT_LOGIC_PATHS.keys())


def test_catalog_nodes_stamped_with_logic_path() -> None:
    stamped = {ln["id"] for ln in LIFE_LINES if ln.get("logic_path")}
    assert stamped == set(PRODUCT_LOGIC_PATHS.keys())
    level = next(ln for ln in LIFE_LINES if ln["id"] == "level_term")
    assert {c["id"] for c in level["coverages"]} >= {"level_term_10", "level_term_15", "level_term_20", "level_term_25", "level_term_30"}
    annuity = next(ln for ln in LIFE_LINES if ln["id"] == "qlac")
    assert all(c.get("logic_path", "").endswith(".annuity.qlac") for c in annuity["coverages"])


def test_resolution_by_product_and_by_coverage_hint() -> None:
    assert resolve_logic_path("level_term") == "insureflow.life.lobs.term_life.level_term"
    assert resolve_logic_path(None, "ten_pay") == "insureflow.life.lobs.whole_life.limited_pay"
    assert (resolve_logic_path(None, None, "Graded Benefit Whole Life") or "").endswith("whole_life.graded")
    assert resolve_logic_path(None, "no_lapse") == "insureflow.life.lobs.universal_life.guaranteed_universal_life"
    assert resolve_logic_path(None, "gmdb") == "insureflow.life.lobs.universal_life.variable_universal_life"
    assert resolve_logic_path(None, "pure_maturity") == "insureflow.life.lobs.endowment.pure_endowment"
    assert resolve_logic_path(None, "type_ii") == "insureflow.life.lobs.ulip.ulip_type_ii"
    assert resolve_logic_path(None, "with_profit_mb") == "insureflow.life.lobs.money_back.with_profit_money_back"
    assert resolve_logic_path(None, "qlac_deferred") == "insureflow.life.lobs.annuity.qlac"
    assert resolve_logic_path(None, "structured_lump") == "insureflow.life.lobs.annuity.structured_settlement_annuity"
    assert resolve_logic_path(None, "joint_50") == "insureflow.life.lobs.annuity.joint_survivor_annuity"
    assert resolve_logic_path(None, "life_refund") == "insureflow.life.lobs.annuity.life_annuity"
    assert resolve_logic_path(None, "period_certain") == "insureflow.life.lobs.annuity.immediate_annuity"
    assert (resolve_logic_path(None, None, "Single Premium ULIP") or "").endswith("ulip.single_premium_ulip")
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
    assert rules["free_look_days"] == 10  # CT Gen. Stat. 38a-436 — platform table
    assert rules["paramed_face_threshold"] == 100000.0  # carrier override, module layer
    assert rules["source"] == "state_table"
    assert any("free-look" in c for c in ct.metadata["conditions"])
    # CT has no filed rates → filing gate fires inside this path
    assert ct.eligible is False
    assert any("CT state-of-issue" in r for r in ct.ineligibility_reasons)


def test_state_rules_carrier_default_when_state_unknown() -> None:
    # TX has no module row, but the canonical platform state-law table
    # supplies its free look — only truly unknown codes fall to defaults.
    tx = rate_life(_bundle(), coverage_id="level_term_20", product_id="level_term", state="TX")
    rules = tx.metadata["state_rules_applied"]
    assert rules["issue_state"] == "TX"
    assert rules["source"] == "state_table"
    assert rules["rule_layer"] == "platform"
    assert rules["free_look_days"] == 10


def test_all_us_jurisdictions_get_state_law_row_in_every_family() -> None:
    from insureflow.life.lobs.state_law import (
        ANNUITY_FREE_LOOK_DAYS,
        COMMUNITY_PROPERTY_STATES,
        LIFE_FREE_LOOK_DAYS,
    )

    assert len(LIFE_FREE_LOOK_DAYS) == 51  # 50 states + DC
    assert len(ANNUITY_FREE_LOOK_DAYS) == 51
    # Products without hand-tuned rows inherit the platform table verbatim.
    life_families = [
        ("level_term", "twenty_year_level"),
        ("ordinary_whole_life", "guaranteed_whole_life"),
        ("guaranteed_universal_life", "no_lapse"),
        ("pure_endowment", "pure_maturity"),
        ("regular_premium_ulip", "rp_ulip"),
        ("traditional_money_back", "traditional_mb"),
    ]
    for state in LIFE_FREE_LOOK_DAYS:
        pid, cid = life_families[hash(state) % len(life_families)]
        q = rate_life(_bundle(), coverage_id=cid, product_id=pid, state=state)
        rules = q.metadata["state_rules_applied"]
        assert rules["source"] == "state_table", (state, pid)
        assert rules["free_look_days"] == LIFE_FREE_LOOK_DAYS[state], (state, pid)
    for state in ANNUITY_FREE_LOOK_DAYS:
        a = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state=state)
        ra = a.metadata["state_rules_applied"]
        assert ra["free_look_days"] == ANNUITY_FREE_LOOK_DAYS[state], (state, "annuity")
    # Annuity statutes differ from life statutes in the same state.
    fl_life = rate_life(_bundle(), coverage_id="twenty_year_level", product_id="level_term", state="FL")
    fl_ann = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state="FL")
    assert fl_life.metadata["state_rules_applied"]["free_look_days"] == 14
    assert fl_ann.metadata["state_rules_applied"]["free_look_days"] == 21
    tx_ann = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state="TX")
    rtx = tx_ann.metadata["state_rules_applied"]
    assert rtx["free_look_days"] == 20 and rtx["replacement_free_look_days"] == 30
    # Distinctive statutory values survive the merge chain.
    ny = rate_life(_bundle(), coverage_id="ten_pay", product_id=None, state="NY")
    ny = rate_life(_bundle(), coverage_id="ten_pay", product_id="limited_pay", state="NY")
    assert ny.metadata["state_rules_applied"]["free_look_days"] == 20
    wy = rate_life(_bundle(), coverage_id="twenty_year_level", product_id="level_term", state="WY")
    assert wy.metadata["state_rules_applied"]["free_look_days"] == 30  # WY Admin Code Ins Gen Ch 12 s4
    # Senior extensions stamped on annuity paths (Cal. Ins. Code 10127.10).
    ca_ann = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state="CA")
    rca = ca_ann.metadata["state_rules_applied"]
    assert rca["senior_free_look_days"] == 30 and rca["senior_free_look_min_age"] == 60
    # Community-property consent rows fire on annuity paths in all 9 states.
    for state in COMMUNITY_PROPERTY_STATES:
        cp = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state=state)
        assert cp.metadata["state_rules_applied"].get("spousal_consent_required") is True, state


def test_guaranty_caps_and_grace_and_claims_stamped_by_state() -> None:
    # Guaranty caps: NAIC defaults vs high-cap states.
    il = rate_life(_bundle(), coverage_id="twenty_year_level", product_id="level_term", state="IL")
    g = il.metadata["state_rules_applied"]["guaranty"]
    assert g["death_cap"] == 300000.0 and g["cash_value_cap"] == 100000.0 and g["aggregate_cap"] == 300000.0
    ny = rate_life(_bundle(), coverage_id="twenty_year_level", product_id="level_term", state="NY")
    gn = ny.metadata["state_rules_applied"]["guaranty"]
    assert gn["death_cap"] == 500000.0 and gn["cash_value_cap"] == 500000.0
    ca = rate_life(_bundle(), coverage_id="guaranteed_whole_life", product_id="ordinary_whole_life", state="CA")
    gc = ca.metadata["state_rules_applied"]["guaranty"]
    assert gc["coinsurance_pct"] == 80.0  # CA pays 80% of covered value up to cap
    ann = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state="WA")
    assert ann.metadata["state_rules_applied"]["guaranty"]["annuity_pv_cap"] == 500000.0
    # Grace periods: CA's 60-day statute (Ins. Code 10113.71) vs default 31.
    assert ca.metadata["state_rules_applied"]["grace_period_days"] == 60
    assert il.metadata["state_rules_applied"]["grace_period_days"] == 31
    # Claims-settlement interest anchors differ by state.
    assert il.metadata["state_rules_applied"]["claims_settlement"]["accrues_from"] == "proof_of_death"
    ct = rate_life(_bundle(), coverage_id="twenty_year_level", product_id="level_term", state="CT")
    ct_claims = ct.metadata["state_rules_applied"]["claims_settlement"]
    assert ct_claims["accrues_from"] == "date_of_death" and ct_claims["offset_days"] == 10


def test_ny_reg187_documented_suitability_on_life_paths() -> None:
    q = rate_life(_bundle(), coverage_id="level_term_20", product_id="level_term", state="NY")
    regime = q.metadata.get("suitability_regime")
    assert regime and regime["regime"] == "NY Reg 187" and regime["citation"] == "11 NYCRR 224"
    assert any("documented suitability analysis REQUIRED" in c for c in q.metadata["conditions"])
    # Same regime governs NY annuities (instead of Model #275).
    a = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state="NY")
    assert a.metadata["suitability_regime"]["regime"] == "NY Reg 187"


def test_best_interest_obligations_on_annuity_paths() -> None:
    tx = rate_life(_bundle("Purchase price: $500000. Applicant age: 65. Sex: male."), coverage_id="life_income", product_id="immediate_annuity", state="TX")
    regime = tx.metadata.get("suitability_regime")
    assert regime is not None and regime["regime"].startswith("NAIC Model #275")
    assert set(regime["obligations"]) == {"care", "disclosure", "conflict_of_interest", "documentation"}
    assert any("Best Interest" in c for c in tx.metadata["conditions"])
    # Life products outside NY carry no special sales-regime burden.
    life = rate_life(_bundle(), coverage_id="twenty_year_level", product_id="level_term", state="TX")
    assert life.metadata.get("suitability_regime") is None or "Best Interest" not in str(life.metadata.get("suitability_regime"))


def test_annuity_premium_tax_embedded_in_quote() -> None:
    annuity_text = "Purchase price: $500000. Applicant age: 65. Sex: male."
    ca = rate_life(_bundle(annuity_text), coverage_id="life_income", product_id="immediate_annuity", state="CA")
    tax = ca.metadata.get("premium_tax")
    assert tax and tax["rate"] == 0.0235 and tax["amount"] == 11750.0 and tax["insurer_paid"] is True
    nv = rate_life(_bundle(annuity_text), coverage_id="life_income", product_id="immediate_annuity", state="NV")
    assert nv.metadata["premium_tax"]["rate"] == 0.035
    # SD tiers: 1.25% on first $500k, 0.08% above — on $600k that's 6250 + 80.
    sd = rate_life(
        _bundle("Purchase price: $600000. Applicant age: 65. Sex: male."),
        coverage_id="life_income",
        product_id="immediate_annuity",
        state="SD",
    )
    assert sd.metadata["premium_tax"]["amount"] == round(500000 * 0.0125 + 100000 * 0.0008, 2)
    # Untaxed states carry no premium-tax block at all.
    il = rate_life(_bundle(annuity_text), coverage_id="life_income", product_id="immediate_annuity", state="IL")
    assert "premium_tax" not in il.metadata or il.metadata.get("premium_tax") is None
    fl = rate_life(_bundle(annuity_text), coverage_id="life_income", product_id="immediate_annuity", state="FL")
    assert fl.metadata["premium_tax"]["pass_through_credit"] is True


def test_pricing_relativity_basis_explicit_for_all_states() -> None:
    manual = json.load(open("src/insureflow/rating/personal/filings/life_rate_manual.json"))
    basis = manual["relativity_basis"]
    assert len(basis) == 51  # every jurisdiction has an explicit filing status
    filed = {st for st, b in basis.items() if b == "filed_exhibit"}
    assert filed == {"IL", "CA", "NY", "TX", "FL", "MT"}
    # Only filed states appear in the relativity table — presence drives
    # the state-of-filing gate and must stay truthful.
    assert set(manual["state_relativities"]) == filed
    assert basis["CT"] == "no_state_filing_generic_engine_only"


def test_florida_free_look_stamped_across_all_families() -> None:
    # FL: 14-day free look for life products, 21-day for annuities (statute) —
    # the platform table serves the family-correct value to every path.
    families = [
        ("level_term", "twenty_year_level", 14),
        ("ordinary_whole_life", "guaranteed_whole_life", 14),
        ("guaranteed_universal_life", "no_lapse", 14),
        ("pure_endowment", "pure_maturity", 14),
        ("regular_premium_ulip", "rp_ulip", 14),
        ("traditional_money_back", "traditional_mb", 14),
        ("immediate_annuity", "life_income", 21),
        ("with_profit_money_back", "with_profit_mb", 14),  # inherits table from traditional
    ]
    for pid, cid, expected_days in families:
        is_annuity = expected_days == 21
        bundle = _bundle("Purchase price: $500000. Applicant age: 65. Sex: male.") if is_annuity else _bundle()
        q = rate_life(bundle, coverage_id=cid, product_id=pid, state="FL")
        rules = q.metadata["state_rules_applied"]
        assert rules["issue_state"] == "FL", pid
        assert rules["free_look_days"] == expected_days, pid
        assert rules["source"] == "state_table", pid
    # FL pricing relativity (1.05) still applies on top of the rule row.
    fl = rate_life(_bundle(), coverage_id="twenty_year_level", product_id="level_term", state="FL")
    il = rate_life(_bundle(), coverage_id="twenty_year_level", product_id="level_term", state="IL")
    assert fl.adjusted_premium > il.adjusted_premium


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


def test_unregistered_annuity_text_falls_back_to_generic_illustration() -> None:
    generic = rate_life(_bundle("Purchase price: $300000. Immediate annuity for retirement."))
    assert "lob_logic_path" not in generic.metadata
    assert generic.metadata["product_family"] == "annuity"
    assert generic.adjusted_premium == 0.0


# ---------------------------------------------------------------------------
# LOB 3 — Universal Life sub-product paths
# ---------------------------------------------------------------------------


def test_gul_no_lapse_guarantee_and_projection() -> None:
    gul = rate_life(_bundle(), coverage_id="no_lapse", product_id="guaranteed_universal_life")
    to120 = rate_life(_bundle(), coverage_id="gul_to_120", product_id="guaranteed_universal_life")
    assert gul.metadata["guarantee_to_age"] == 120
    assert to120.metadata["guarantee_to_age"] == 121
    proj = gul.metadata["account_value_projection_guaranteed_basis"]
    # Projection now runs the FULL guarantee horizon (to guarantee_to_age),
    # not a fixed 20 years — checkpoints at 5/10/20 plus the final horizon
    # year, so the exact final-year key varies with issue age.
    assert {"av_year_5", "av_year_10", "av_year_20"} <= set(proj)
    assert "shadow_account_funding_adequate" in gul.metadata
    assert any("no-lapse" in c.lower() for c in gul.metadata["conditions"])
    assert gul.metadata["rating_engine"].startswith("life_")
    assert "universal life priced on actuarial equivalence" in " ".join(gul.ineligibility_reasons)


def test_ul_charge_load_ordering_gul_lt_iul_lt_vul() -> None:
    gul = rate_life(_bundle(), coverage_id="no_lapse", product_id="guaranteed_universal_life")
    iul = rate_life(_bundle(), coverage_id="indexed_account", product_id="indexed_universal_life")
    vul = rate_life(_bundle(), coverage_id="gmdb", product_id="variable_universal_life")
    caul = rate_life(_bundle(), coverage_id="current_rate", product_id="current_assumption_universal_life")
    assert gul.adjusted_premium < iul.adjusted_premium < vul.adjusted_premium
    assert caul.adjusted_premium < gul.adjusted_premium  # lowest flexibility load


def test_iul_crediting_scenarios_cap_and_floor() -> None:
    iul = rate_life(_bundle(), coverage_id="indexed_account", product_id="indexed_universal_life")
    scenarios = iul.metadata["credited_rate_scenarios"]
    assert scenarios["index_gain_-10pct"] == 0.0  # floor
    assert scenarios["index_gain_15pct"] == round(iul.metadata["index_cap"], 6)  # cap binds
    assert iul.metadata["index_floor"] == 0.0


def test_vul_finra_gate_and_gmdb_rider() -> None:
    finra = rate_life(_bundle(), coverage_id="finra_suitability", product_id="variable_universal_life")
    plain = rate_life(_bundle(), coverage_id="vx_account", product_id="variable_universal_life")
    gmdb = rate_life(_bundle(), coverage_id="gmdb", product_id="variable_universal_life")
    assert any("FINRA suitability review REQUIRED" in c for c in finra.metadata["conditions"])
    assert any("Prospectus delivery receipt" in c for c in plain.metadata["conditions"])
    assert gmdb.metadata["gmdb_rider"] is True
    assert gmdb.adjusted_premium > plain.adjusted_premium  # rider costs extra


def test_caul_two_crediting_columns() -> None:
    caul = rate_life(_bundle(), coverage_id="adjustable", product_id="current_assumption_universal_life")
    cols = caul.metadata["av_projection_columns"]
    assert cols["current_rate"]["av_year_20"] > cols["guaranteed_min"]["av_year_20"]
    assert caul.metadata["current_credit_rate"] > caul.metadata["guaranteed_minimum_rate"]


# ---------------------------------------------------------------------------
# LOB 4 — Endowment sub-product paths
# ---------------------------------------------------------------------------


def test_endowment_ordering_pure_lt_with_profit_lt_fixed() -> None:
    pure = rate_life(_bundle(), coverage_id="pure_maturity", product_id="pure_endowment")
    full = rate_life(_bundle(), coverage_id="with_profit", product_id="full_endowment")
    fixed = rate_life(_bundle(), coverage_id="fixed_endowment", product_id="guaranteed_fixed_endowment")
    # No death benefit → cheapest; guaranteed-all-values → most expensive.
    assert pure.adjusted_premium < full.adjusted_premium < fixed.adjusted_premium
    assert pure.metadata["death_benefit"] == 0.0
    assert fixed.metadata["actuarial"]["basis"].endswith("fully guaranteed")


def test_full_endowment_bonus_illustrated_not_in_premium() -> None:
    full = rate_life(_bundle(), coverage_id="with_profit", product_id="full_endowment")
    assert full.metadata["illustrated_bonus_maturity_value"] > full.metadata["guaranteed_maturity_value"]
    assert any("NOT guaranteed" in c for c in full.metadata["conditions"])
    assert full.metadata["endowment_uw"]["product"] == "endowment"


def test_pure_endowment_no_death_benefit_disclosure_and_uw() -> None:
    poor_income = _bundle("Face amount: $400000. Annual income: 20000. Applicant age: 35.")
    pe = rate_life(poor_income, coverage_id="pure_maturity", product_id="pure_endowment")
    assert any("nothing is payable if the insured dies" in c.lower() or "PURE ENDOWMENT" in c for c in pe.metadata["conditions"])
    assert pe.metadata["maturity_value"] == 400000.0


# ---------------------------------------------------------------------------
# LOB 5 — ULIP sub-product paths
# ---------------------------------------------------------------------------


def test_ulip_type_i_vs_type_ii_db_formula_and_cost() -> None:
    t1 = rate_life(_bundle(), coverage_id="type_i", product_id="ulip_type_i")
    t2 = rate_life(_bundle(), coverage_id="type_ii", product_id="ulip_type_ii")
    assert t1.metadata["db_formula"] == "max(SA, FV)"
    assert t2.metadata["db_formula"] == "SA + FV"
    assert t2.metadata["type_ii_extra_mortality_load"] > 1.0
    assert t2.metadata["mortality_charge_year1"] > t1.metadata["mortality_charge_year1"]


def test_ulip_sa_multiple_rule_by_age() -> None:
    young = rate_life(_bundle("Applicant age: 40. Face amount: $500000."), coverage_id="rp_ulip", product_id="regular_premium_ulip")
    older = rate_life(_bundle("Applicant age: 55. Face amount: $500000."), coverage_id="rp_ulip", product_id="regular_premium_ulip")
    assert young.metadata["annual_premium"] * 10 == pytest.approx(young.metadata["sum_assured"], rel=0.01)
    assert older.metadata["annual_premium"] * 7 == pytest.approx(older.metadata["sum_assured"], rel=0.01)


def test_single_premium_ulip_zero_recurring_premium() -> None:
    sp = rate_life(_bundle(), coverage_id="sp_ulip", product_id="single_premium_ulip")
    # No RECURRING premium, but adjusted_premium must still carry the real
    # lump-sum contribution — it must not silently report $0.00.
    assert sp.adjusted_premium == 500000.0
    assert sp.base_premium == 500000.0
    assert sp.metadata["single_premium"] == 500000.0
    assert sp.metadata["lock_in_years"] == 5
    assert sp.metadata["fund_value_projection"] > sp.metadata["single_premium"]  # growth at assumed rate


def test_pension_ulip_annuitization_requirement() -> None:
    pension = rate_life(_bundle(), coverage_id="pension_ulip", product_id="pension_ulip")
    assert pension.metadata["vesting_age"] == 60
    assert pension.metadata["minimum_annuitization_amount"] == pytest.approx(pension.metadata["fund_value_at_vesting"] * 2 / 3, rel=0.01)
    senior = rate_life(_bundle("Applicant age: 62."), coverage_id="pension_ulip", product_id="pension_ulip")
    assert senior.eligible is False  # entry age gate


def test_child_ulip_waiver_of_premium_and_proposer_gate() -> None:
    child = rate_life(_bundle("Applicant age: 35."), coverage_id="child_ulip", product_id="child_ulip")
    assert child.metadata["waiver_of_premium_included"] is True
    assert child.metadata["milestone_ages"] == [18, 20, 22, 25]
    old_proposer = rate_life(_bundle("Applicant age: 61."), coverage_id="child_ulip", product_id="child_ulip")
    assert old_proposer.eligible is False


# ---------------------------------------------------------------------------
# LOB 6 — Money-Back sub-product paths
# ---------------------------------------------------------------------------


def test_money_back_survival_schedule_totals() -> None:
    mb = rate_life(_bundle(), coverage_id="traditional_mb", product_id="traditional_money_back")
    schedule = mb.metadata["survival_benefit_schedule"]
    assert [s["year"] for s in schedule] == [5, 10, 15, 20]
    total_pct = sum(s["pct_of_sa"] for s in schedule)
    assert total_pct == pytest.approx(1.0)  # 20+20+20+40% fully returned while living
    assert mb.metadata["death_benefit"] == 500000.0  # full SA on death throughout


def test_with_profit_money_back_bonuses_on_top() -> None:
    wp = rate_life(_bundle(), coverage_id="with_profit_mb", product_id="with_profit_money_back")
    trad = rate_life(_bundle(), coverage_id="traditional_mb", product_id="traditional_money_back")
    assert wp.adjusted_premium == pytest.approx(trad.adjusted_premium, rel=1e-9)  # same guaranteed basis
    assert wp.metadata["illustrated_bonus_pv"] > 0
    assert any("NOT guaranteed" in c for c in wp.metadata["conditions"])


def test_children_money_back_milestones_and_wp() -> None:
    cmb = rate_life(_bundle("Applicant age: 34."), coverage_id="children_mb", product_id="children_money_back")
    sched = cmb.metadata["payout_schedule"]
    assert [s["child_age"] for s in sched] == [18, 20, 22, 25]
    assert cmb.metadata["waiver_of_premium_included"] is True
    young_parent = rate_life(_bundle("Applicant age: 19."), coverage_id="children_mb", product_id="children_money_back")
    assert young_parent.eligible is False


# ---------------------------------------------------------------------------
# LOB 7 — Annuity sub-product paths (illustration only)
# ---------------------------------------------------------------------------


ANN_TEXT = "Purchase price: $500000. Applicant age: 65. Sex: male."


def _ann(text: str = ANN_TEXT):
    return _bundle(text)


def test_all_annuity_paths_are_illustrations_only() -> None:
    cases = [
        ("immediate_annuity", "life_income"),
        ("deferred_annuity", "deferred_income"),
        ("fixed_annuity", "fixed_accum"),
        ("variable_annuity", "var_annuity"),
        ("indexed_annuity", "indexed_crediting"),
        ("life_annuity", "single_life_income"),
        ("joint_survivor_annuity", "joint_100"),
        ("qlac", "qlac_lifetime"),
        ("structured_settlement_annuity", "structured_payments"),
    ]
    for pid, cid in cases:
        q = rate_life(_ann(), coverage_id=cid, product_id=pid, state="IL")
        assert q.eligible is False, pid
        # Illustration-only (unfiled) does not mean the computed consideration
        # is discarded — adjusted_premium/base_premium must carry the real
        # purchase price so quote documents don't show $0.00.
        assert q.adjusted_premium > 0.0, pid
        assert q.base_premium > 0.0, pid
        assert q.metadata["state_rules_applied"]["issue_state"] == "IL", pid


def test_immediate_vs_period_certain_vs_refund_payout_ordering() -> None:
    life_only = rate_life(_ann(), coverage_id="life_income", product_id="immediate_annuity")
    certain = rate_life(_ann(), coverage_id="period_certain", product_id="immediate_annuity")
    refund = rate_life(_ann(ANN_TEXT), coverage_id="life_refund", product_id="life_annuity")
    plain_life = rate_life(_ann(), coverage_id="single_life_income", product_id="life_annuity")
    # Certain-and-life pays less than pure life; refund guarantee costs ~3%.
    assert life_only.metadata["annual_payout"] > certain.metadata["annual_payout"]
    assert plain_life.metadata["annual_payout"] > refund.metadata["annual_payout"]
    assert refund.metadata["breakeven_years"] == pytest.approx(500000 / refund.metadata["annual_payout"], abs=0.2)


def test_joint_survivor_continuation_costs_income() -> None:
    j100 = rate_life(_ann(), coverage_id="joint_100", product_id="joint_survivor_annuity")
    j50 = rate_life(_ann(), coverage_id="joint_50", product_id="joint_survivor_annuity")
    single = rate_life(_ann(), coverage_id="single_life_income", product_id="life_annuity")
    single_payout = single.metadata["annual_payout"]
    # Richer continuation = lower starting payout, but far from zero.
    assert single_payout > j50.metadata["annual_payout"] > j100.metadata["annual_payout"]
    assert j100.metadata["annual_payout"] > single_payout * 0.6
    assert j100.metadata["continuation_pct"] == 1.0
    assert j100.metadata["assumed_spouse_age"] == 62  # explicit −3 offset assumption


def test_deferred_accumulates_then_annuitizes_at_vesting() -> None:
    d = rate_life(_ann("Purchase price: $500000. Applicant age: 55. Sex: male."), coverage_id="deferred_income", product_id="deferred_annuity")
    assert d.metadata["vesting_age"] == 65
    fv = d.metadata["fund_value_at_vesting"]
    assert fv > 500000  # credited growth over 10 years
    payout = d.metadata["annual_payout_at_vesting"]
    factor = d.metadata["annuitization_factor_at_vesting"]
    assert payout == pytest.approx(fv / factor, rel=0.01)


def test_qlac_irs_cap_enforced_inside_path() -> None:
    within = rate_life(_ann("Purchase price: $200000. Applicant age: 60. Sex: male."), coverage_id="qlac_lifetime", product_id="qlac")
    over = rate_life(_ann("Purchase price: $400000. Applicant age: 60. Sex: male."), coverage_id="qlac_lifetime", product_id="qlac")
    assert within.eligible is False  # illustration only regardless
    assert over.metadata["purchase_price"] == over.metadata["irs_cap"] == 210000.0
    assert "IRS QLAC cap" in " ".join(over.ineligibility_reasons)
    assert over.metadata["rmd_excluded_until_income_starts"] is True
    assert over.metadata["income_start_age"] <= 75


def test_structured_settlement_prices_schedule_pv() -> None:
    text = "$2500 per month for 20 years settlement."
    q = rate_life(_ann(text), coverage_id="structured_payments", product_id="structured_settlement_annuity")
    meta = q.metadata
    expected_pv = 2500 * ((1 - (1 / (1 + 0.04 / 12)) ** 240) / (0.04 / 12))
    assert meta["present_value_of_settlement"] == pytest.approx(expected_pv, rel=0.001)
    assert meta["total_nominal_payouts"] == 600000.0
    lump = rate_life(_ann(text), coverage_id="structured_lump", product_id="structured_settlement_annuity")
    assert lump.metadata["commuted_lump_pv"] == pytest.approx(expected_pv, rel=0.001)


def test_variable_indexed_annuity_riders_and_scenarios() -> None:
    va = rate_life(_ann(), coverage_id="var_gmwb", product_id="variable_annuity")
    assert va.metadata["gmwb_rider"] is True
    assert va.metadata["gmwb_rider_fee_pct"] == 0.0115
    ia = rate_life(_ann(), coverage_id="indexed_crediting", product_id="indexed_annuity")
    sc = ia.metadata["credited_rate_scenarios"]
    assert sc["index_gain_-15pct"] == 0.0
    assert sc["index_gain_20pct"] == ia.metadata["index_cap"]
