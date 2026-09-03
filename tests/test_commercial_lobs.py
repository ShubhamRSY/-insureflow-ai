"""Dedicated Commercial LOB logic paths — mirrors tests/test_health_lobs.py.

Covers: the per-product registry, the real state-law gates each product
adds (WC monopolistic-fund block, property valued-policy-law/named-storm
overlay, trade credit/E&O surplus-lines tax), and a happy-path quote in a
plain state for each of the 6 live products.
"""

from __future__ import annotations

from insureflow.commercial.lobs import PRODUCT_LOGIC_PATHS, CommercialProductContext, run_product_logic
from insureflow.commercial.lobs.property_bi import apply_state_law_overlay
from insureflow.commercial.lobs.state_law import MONOPOLISTIC_FUND_STATES, NON_SUBSCRIPTION_STATES
from insureflow.models.agents import Recommendation, UnderwritingMemo, UWDecision
from insureflow.models.submissions import (
    FinancialData,
    LocationData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.models import InsuranceLine, QuoteResult


def _bundle(text: str = "", *, state: str = "IL", with_payroll: bool = False) -> SubmissionBundle:
    structured = None
    if with_payroll:
        structured = StructuredSubmission(
            submission_id="t1",
            named_insured=NamedInsured(legal_name="Test Co"),
            locations=[LocationData(address="1 Main St", city="Springfield", state=state, zip_code="00000", building_value=2_000_000, contents_value=500_000)],
            financial=FinancialData(annual_revenue=10_000_000, payroll=2_400_000),
            risk_profile=RiskProfile(ncci_class_code="5403"),
        )
    unstructured = [UnstructuredSubmission(submission_id="u1", raw_text=text)] if text else []
    return SubmissionBundle(bundle_id="lob-test", structured=structured, unstructured=unstructured)


def _memo() -> UnderwritingMemo:
    return UnderwritingMemo(
        bundle_id="lob-test",
        decision=UWDecision.ACCEPT,
        summary="Clean submission",
        recommendation=Recommendation(action="accept", rationale="test"),
    )


def _ctx(product_id: str, line: InsuranceLine, *, state: str = "IL", bundle: SubmissionBundle | None = None, **kwargs) -> CommercialProductContext:
    return CommercialProductContext(
        bundle=bundle or _bundle(with_payroll=True, state=state),
        memo=_memo(),
        line=line,
        state_code=state,
        product_id=product_id,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_all_six_live_products_registered():
    assert set(PRODUCT_LOGIC_PATHS) == {
        "property_bi",
        "workers_comp",
        "directors_officers",
        "trade_credit",
        "errors_omissions",
        "key_person",
    }


def test_unregistered_product_returns_none():
    ctx = _ctx("some_unregistered_product", InsuranceLine.GENERAL_LIABILITY)
    assert run_product_logic(ctx) is None


# ---------------------------------------------------------------------------
# Workers' Comp — monopolistic fund gate, non-subscription note, happy path
# ---------------------------------------------------------------------------


def test_wc_monopolistic_fund_state_is_ineligible():
    # Hardcoded known monopolistic-fund states — asserted directly rather than
    # looped over MONOPOLISTIC_FUND_STATES itself, so a mutation that empties
    # that constant can't make this loop (and the test) silently no-op.
    for state in ("ND", "OH", "WA", "WY"):
        assert state in MONOPOLISTIC_FUND_STATES
        ctx = _ctx("workers_comp", InsuranceLine.WORKERS_COMP, state=state)
        result = run_product_logic(ctx)
        assert isinstance(result, QuoteResult)
        assert result.eligible is False, f"{state} should be a monopolistic-fund block"
        assert result.adjusted_premium == 0.0
        assert any("exclusive/monopolistic" in r for r in result.ineligibility_reasons)


def test_wc_texas_non_subscription_note_present():
    assert "TX" in NON_SUBSCRIPTION_STATES
    bundle = _bundle("Experience modification: 1.05 e-mod: 1.05", with_payroll=True, state="TX")
    ctx = _ctx("workers_comp", InsuranceLine.WORKERS_COMP, state="TX", bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert any("non-subscription" in c.lower() for c in result.metadata.get("conditions", []))


def test_wc_happy_path_plain_state_prices_via_ncci():
    bundle = _bundle("Experience modification: 1.10 e-mod: 1.10", with_payroll=True, state="IL")
    ctx = _ctx("workers_comp", InsuranceLine.WORKERS_COMP, state="IL", bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert result.eligible is True
    assert result.adjusted_premium > 0
    assert result.metadata["lob_logic_path"] == "insureflow.commercial.lobs.workers_comp"
    assert result.metadata["rating_engine"] == "ncci_class_emod"


def test_wc_dispatches_through_rating_engine_end_to_end():
    """The dedicated path fires through the real engine.quote() call, not just directly."""
    bundle = _bundle("Experience modification: 1.0 e-mod: 1.0", with_payroll=True, state="OH")
    engine = InsuranceRatingEngine()
    quote = engine.quote(bundle, _memo(), line=InsuranceLine.WORKERS_COMP, commercial_product_id="workers_comp", state_override="OH")
    assert quote.eligible is False
    assert any("monopolistic" in r for r in quote.ineligibility_reasons)


# ---------------------------------------------------------------------------
# Property/BI — valued policy law + named storm overlay
# ---------------------------------------------------------------------------


def test_property_overlay_flags_valued_policy_law_state():
    result = QuoteResult(bundle_id="b1", line=InsuranceLine.COMMERCIAL_PROPERTY, base_premium=1000.0, adjusted_premium=1200.0)
    apply_state_law_overlay(result, "TX")
    assert result.metadata["state_rules_applied"]["valued_policy_law"] is True
    assert any("Valued Policy Law" in c for c in result.metadata["conditions"])


def test_property_overlay_flags_named_storm_deductible_state():
    result = QuoteResult(bundle_id="b1", line=InsuranceLine.COMMERCIAL_PROPERTY, base_premium=1000.0, adjusted_premium=1200.0)
    apply_state_law_overlay(result, "FL")
    assert result.metadata["state_rules_applied"]["named_storm_pct_deductible"] is True
    assert any("named-storm" in c.lower() for c in result.metadata["conditions"])


def test_property_overlay_is_noop_for_plain_state():
    result = QuoteResult(bundle_id="b1", line=InsuranceLine.COMMERCIAL_PROPERTY, base_premium=1000.0, adjusted_premium=1200.0)
    apply_state_law_overlay(result, "IL")
    assert result.metadata["state_rules_applied"] == {"issue_state": "IL"}
    assert result.metadata["conditions"] == []
    # Pricing untouched by the overlay
    assert result.adjusted_premium == 1200.0


def test_property_overlay_wired_into_engine_for_commercial_property_line():
    bundle = SubmissionBundle(
        bundle_id="prop-test",
        structured=StructuredSubmission(
            submission_id="t1",
            named_insured=NamedInsured(legal_name="Test Co"),
            locations=[LocationData(address="1 Coastal Way", city="Miami", state="FL", zip_code="33101", building_value=2_000_000, contents_value=500_000)],
        ),
    )
    engine = InsuranceRatingEngine()
    quote = engine.quote(bundle, _memo(), line=InsuranceLine.COMMERCIAL_PROPERTY, commercial_product_id="property_bi", state_override="FL")
    assert quote.metadata.get("lob_logic_path") == "insureflow.commercial.lobs.property_bi"
    assert any("named-storm" in c.lower() for c in quote.metadata.get("conditions", []))


# ---------------------------------------------------------------------------
# Specialty lines — D&O / Trade Credit / E&O / Key Person
# ---------------------------------------------------------------------------


def test_do_declines_on_going_concern_language():
    bundle = _bundle("Directors and officers application. Going concern doubt disclosed in latest audit.")
    ctx = _ctx("directors_officers", InsuranceLine.DIRECTORS_AND_OFFICERS, bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert result.eligible is False
    assert result.adjusted_premium == 0.0


def test_do_happy_path_prices_via_specialty_engine():
    bundle = _bundle("Directors and officers application. Aggregate limit: $2,000,000. No litigation. Prior acts covered, continuity date 2015.")
    ctx = _ctx("directors_officers", InsuranceLine.DIRECTORS_AND_OFFICERS, bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert result.eligible is True
    assert result.adjusted_premium > 0
    assert result.metadata["lob_logic_path"] == "insureflow.commercial.lobs.directors_officers"


def test_trade_credit_surplus_lines_tax_varies_by_state():
    bundle = _bundle("Trade credit application. Accounts receivable: $2,000,000.")
    ctx_tx = _ctx("trade_credit", InsuranceLine.TRADE_CREDIT, state="TX", bundle=bundle)
    ctx_il = _ctx("trade_credit", InsuranceLine.TRADE_CREDIT, state="IL", bundle=bundle)
    result_tx = run_product_logic(ctx_tx)
    result_il = run_product_logic(ctx_il)
    assert isinstance(result_tx, QuoteResult) and isinstance(result_il, QuoteResult)
    tax_tx = result_tx.metadata["surplus_lines_tax"]["rate"]
    tax_il = result_il.metadata["surplus_lines_tax"]["rate"]
    assert tax_tx != tax_il
    assert tax_tx == 0.0485
    assert tax_il == 0.035


def test_eo_flags_real_estate_mandatory_state():
    bundle = _bundle("Errors and omissions application for a real estate brokerage. Aggregate limit: $1,000,000.")
    ctx = _ctx("errors_omissions", InsuranceLine.ERRORS_AND_OMISSIONS, state="CO", bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert any("real estate commission" in c.lower() for c in result.metadata.get("conditions", []))


def test_key_person_flags_missing_notice_and_consent():
    bundle = _bundle("Key person application. Face amount: $1,000,000. Job description: CFO.")
    ctx = _ctx("key_person", InsuranceLine.KEY_PERSON, bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert any("101(j)" in c for c in result.metadata.get("conditions", []))


def test_key_person_no_condition_when_consent_documented():
    bundle = _bundle("Key person application. Face amount: $1,000,000. Employee notice and consent obtained per IRC 101(j).")
    ctx = _ctx("key_person", InsuranceLine.KEY_PERSON, bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert not any("101(j)" in c for c in result.metadata.get("conditions", []))


# ---------------------------------------------------------------------------
# Real math: mortality-based key person pricing
# ---------------------------------------------------------------------------


def test_key_person_prices_by_real_mortality_age_curve():
    """Older key employee -> higher mortality rate -> higher premium, same face."""

    def quote_at_age(age: int) -> QuoteResult:
        bundle = _bundle(f"Key person application. Face amount: $1,000,000. Key employee age: {age}. Sex: male. IRC 101(j) notice and consent obtained.")
        ctx = _ctx("key_person", InsuranceLine.KEY_PERSON, bundle=bundle)
        result = run_product_logic(ctx)
        assert isinstance(result, QuoteResult)
        return result

    young = quote_at_age(30)
    old = quote_at_age(65)
    assert young.metadata["rating_engine"] == "key_person_mortality"
    assert old.metadata["mortality_rate_per_1000"] > young.metadata["mortality_rate_per_1000"]
    assert old.adjusted_premium > young.adjusted_premium


def test_key_person_undisclosed_age_uses_illustrative_default_and_discloses_it():
    bundle = _bundle("Key person application. Face amount: $1,000,000. IRC 101(j) notice and consent obtained.")
    ctx = _ctx("key_person", InsuranceLine.KEY_PERSON, bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert result.metadata["key_employee_age"] == 45
    assert any("not disclosed" in c for c in result.metadata["conditions"])


# ---------------------------------------------------------------------------
# Real math: ILF power curve for D&O / E&O (sub-linear in limit)
# ---------------------------------------------------------------------------


def test_do_ilf_curve_matches_basic_limit_and_is_sublinear():
    def quote_at_limit(limit: int) -> QuoteResult:
        bundle = _bundle(f"D&O application. Aggregate limit: ${limit:,}. No litigation. Prior acts covered, continuity date 2015.")
        ctx = _ctx("directors_officers", InsuranceLine.DIRECTORS_AND_OFFICERS, bundle=bundle)
        result = run_product_logic(ctx)
        assert isinstance(result, QuoteResult)
        return result

    at_basic = quote_at_limit(1_000_000)
    assert at_basic.metadata["ilf"] == 1.0

    doubled = quote_at_limit(2_000_000)
    ratio = doubled.adjusted_premium / at_basic.adjusted_premium
    # Real curve gives ~2**0.25 = 1.19x. A tight bound matters here: a loose
    # <2.0 bound would still pass even for a mutated LINEAR curve, since the
    # flat $75 fee alone keeps any sub-2x curve under 2.0 regardless of shape.
    assert 1.0 < ratio < 1.4


def test_eo_ilf_curve_matches_basic_limit_and_is_sublinear():
    def quote_at_limit(limit: int) -> QuoteResult:
        bundle = _bundle(f"Errors and omissions application. Aggregate limit: ${limit:,}.")
        ctx = _ctx("errors_omissions", InsuranceLine.ERRORS_AND_OMISSIONS, bundle=bundle)
        result = run_product_logic(ctx)
        assert isinstance(result, QuoteResult)
        return result

    at_basic = quote_at_limit(1_000_000)
    assert at_basic.metadata["ilf"] == 1.0
    doubled = quote_at_limit(2_000_000)
    ratio = doubled.adjusted_premium / at_basic.adjusted_premium
    assert 1.0 < ratio < 1.4


# ---------------------------------------------------------------------------
# Real math: trade credit indemnity % + concentration surcharge
# ---------------------------------------------------------------------------


def test_trade_credit_applies_indemnity_percentage():
    bundle = _bundle("Trade credit application. Accounts receivable: $1,000,000.")
    ctx = _ctx("trade_credit", InsuranceLine.TRADE_CREDIT, bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert result.metadata["indemnity_pct"] == 0.90
    assert result.metadata["insured_exposure"] == 900_000.0


def test_trade_credit_concentration_surcharge_increases_premium():
    plain = _bundle("Trade credit application. Accounts receivable: $2,000,000.")
    concentrated = _bundle("Trade credit application. Accounts receivable: $2,000,000. Top buyer concentration: 60%.")
    ctx_plain = _ctx("trade_credit", InsuranceLine.TRADE_CREDIT, bundle=plain)
    ctx_concentrated = _ctx("trade_credit", InsuranceLine.TRADE_CREDIT, bundle=concentrated)
    result_plain = run_product_logic(ctx_plain)
    result_concentrated = run_product_logic(ctx_concentrated)
    assert isinstance(result_plain, QuoteResult) and isinstance(result_concentrated, QuoteResult)
    assert result_concentrated.metadata["concentration_surcharge_pct"] > 0
    assert result_plain.metadata["concentration_surcharge_pct"] == 0.0
    assert result_concentrated.adjusted_premium > result_plain.adjusted_premium


# ---------------------------------------------------------------------------
# Real math: WC layered/marginal NCCI premium discount
# ---------------------------------------------------------------------------


def test_ncci_premium_discount_is_layered_not_flat_top_tier():
    from insureflow.commercial.lobs.workers_comp import ncci_premium_discount

    # $500,000 standard premium spans all 3 tiers. A naive "flat top-tier"
    # implementation would discount the WHOLE premium at 15% -> 425,000.
    # The correct layered calc: 10,000@0% + 90,000@8% + 400,000@15%.
    discounted, pct = ncci_premium_discount(500_000.0)
    expected_layered = 10_000.0 + 90_000.0 * 0.92 + 400_000.0 * 0.85
    assert discounted == expected_layered
    naive_flat_top_tier = 500_000.0 * 0.85
    assert discounted != naive_flat_top_tier
    assert discounted > naive_flat_top_tier  # layering is always less aggressive than a flat top rate
    assert round(pct, 2) == round((1 - expected_layered / 500_000.0) * 100.0, 2)


def test_wc_large_payroll_gets_a_real_layered_discount_end_to_end():
    bundle = _bundle("Experience modification: 1.0 e-mod: 1.0", with_payroll=True, state="IL")
    assert bundle.structured is not None
    assert bundle.structured.financial is not None
    bundle.structured.financial.payroll = 5_000_000.0
    ctx = _ctx("workers_comp", InsuranceLine.WORKERS_COMP, state="IL", bundle=bundle)
    result = run_product_logic(ctx)
    assert isinstance(result, QuoteResult)
    assert result.eligible is True
    assert result.metadata["premium_discount_pct"] > 10.0
    assert any("premium discount" in c.lower() for c in result.metadata["conditions"])


# ---------------------------------------------------------------------------
# Real math: property coinsurance penalty
# ---------------------------------------------------------------------------


def _property_bundle(building_value: float, limit_amount: float, coinsurance_pct: float | None = None) -> SubmissionBundle:
    from insureflow.models.submissions import CoverageDetail

    structured = StructuredSubmission(
        submission_id="t1",
        named_insured=NamedInsured(legal_name="Test Co"),
        locations=[LocationData(address="1 Main St", city="Springfield", state="IL", zip_code="00000", building_value=building_value, contents_value=0)],
        coverages=[CoverageDetail(coverage_type="property", limit_amount=limit_amount, coinsurance_pct=coinsurance_pct, deductible=1000.0, premium=0.0)],
    )
    return SubmissionBundle(bundle_id="prop-test", structured=structured)


def test_property_coinsurance_penalty_computed_when_underinsured():
    bundle = _property_bundle(building_value=2_000_000.0, limit_amount=1_000_000.0)
    engine = InsuranceRatingEngine()
    quote = engine.quote(bundle, _memo(), line=InsuranceLine.COMMERCIAL_PROPERTY, commercial_product_id="property_bi", state_override="IL")
    check = quote.metadata.get("coinsurance_check")
    assert check is not None
    assert check["penalty_applies"] is True
    assert check["compliance_ratio"] == 0.625  # 1,000,000 / (80% x 2,000,000)
    assert any("coinsurance penalty" in c.lower() for c in quote.metadata.get("conditions", []))


def test_property_coinsurance_no_penalty_when_adequately_insured():
    bundle = _property_bundle(building_value=2_000_000.0, limit_amount=1_800_000.0)
    engine = InsuranceRatingEngine()
    quote = engine.quote(bundle, _memo(), line=InsuranceLine.COMMERCIAL_PROPERTY, commercial_product_id="property_bi", state_override="IL")
    check = quote.metadata.get("coinsurance_check")
    assert check is not None
    assert check["penalty_applies"] is False
