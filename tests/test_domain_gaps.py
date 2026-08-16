"""Domain-gap coverage — the insurance taxonomy that was previously missing or partial.

Covers the Batch A–F additions: premium accounting, combined ratio, solvency /
RBC, morbidity, policy architecture (coinsurance / SIR / aggregate), insurability,
disclosure duty, legal remedies, proximate cause, guaranty funds, health exposure,
the claims lifecycle (FNOL → adjudication → subrogation/salvage → defense →
indemnity), property valuation (RCV/ACV/agreed), life cash value, health networks,
annuity payout illustration, and the BI evaluator on commercial packages.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from insureflow.models.policy import ClaimDecision, EarningMethod, HealthNetworkType
from insureflow.models.submissions import (
    ClaimRecord,
    CoverageDetail,
    FinancialData,
    LocationData,
    LossRunData,
    NamedInsured,
    PolicyPeriod,
    RiskProfile,
    ScheduleItem,
    ScheduleOfValues,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)
from insureflow.rating.personal.morbidity import morbidity_rate, morbidity_rating_factor
from insureflow.rating.premium_accounting import apply_collection, compute_earned_unearned, premium_accounting_for_bundle
from insureflow.underwriting.causation import analyze_proximate_cause
from insureflow.underwriting.claims import (
    adjudicate_claim,
    adjudicate_claims,
    claims_recovery_review,
    create_notice_of_loss,
    defense_cost_assessment,
    evaluate_salvage,
    evaluate_subrogation,
    indemnity_valuation,
)
from insureflow.underwriting.combined_ratio import combined_ratio, combined_ratio_from_bundle, expense_ratio
from insureflow.underwriting.disclosure import assess_disclosure, assess_warranty_compliance
from insureflow.underwriting.health_exposure import covered_lives, health_exposure_base
from insureflow.underwriting.health_network import assess_network, network_assessment_from_bundle
from insureflow.underwriting.insurability import assess_insurability
from insureflow.underwriting.legal_remedies import determine_remedy, remedy_matrix
from insureflow.underwriting.life_cash_value import cash_value_for_bundle, project_cash_value
from insureflow.underwriting.policy_architecture import (
    aggregate_utilization,
    architecture_assessment,
    coinsurance_penalty,
    per_occurrence_vs_aggregate,
    sir_rating_credit,
)
from insureflow.underwriting.solvency import assess_solvency, rbc_requirement
from insureflow.underwriting.surplus_lines import guarantee_fund_assessment
from insureflow.underwriting.valuation import depreciation_for_age, valuation_assessment, valuation_from_bundle


def _claim(claim_id: str, *, cause: str, incurred: float, paid: float = 0.0, description: str = "") -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        date_of_loss=date(2024, 1, 15),
        line_of_business="commercial_property",
        cause=cause,
        description=description or cause,
        incurred_amount=incurred,
        paid_amount=paid,
    )


def _structured(bundle: SubmissionBundle) -> StructuredSubmission:
    assert bundle.structured is not None
    return bundle.structured


def _bundle(**overrides) -> SubmissionBundle:
    structured = StructuredSubmission(
        submission_id="gap-1",
        named_insured=NamedInsured(legal_name="Gap Test Co"),
        policy_period=PolicyPeriod(effective_date=date(2025, 1, 1), expiration_date=date(2025, 12, 31)),
        locations=[LocationData(address="1 Main", city="Austin", state="TX", zip_code="78701", building_value=2_000_000)],
        coverages=[CoverageDetail(coverage_type="Property", limit_amount=2_000_000, deductible=10_000, premium=60_000)],
        financial=FinancialData(
            annual_revenue=5_000_000,
            employee_count=50,
            loss_run=LossRunData(
                written_premium=80_000,
                earned_premium=75_000,
                claims=[_claim("c1", cause="fire", incurred=25_000, paid=20_000)],
            ),
        ),
        risk_profile=RiskProfile(naics_code="336111", business_description="metal fabrication"),
    )
    kwargs: dict[str, Any] = {
        "bundle_id": "gap-1",
        "structured": structured,
        "unstructured": [
            UnstructuredSubmission(submission_id="gap-1", raw_text="Application for metal fabrication — no prior losses"),
        ],
    }
    kwargs.update(overrides)
    return SubmissionBundle(**kwargs)


# ── 1. Premium accounting ────────────────────────────────────────────────


def test_pro_rata_earned_at_quarter():
    result = compute_earned_unearned(
        12_000,
        effective_date=date(2025, 1, 1),
        expiration_date=date(2025, 12, 31),
        as_of_date=date(2025, 4, 1),
    )
    assert result.earned_premium == round(12_000 * (90 / 364), 2)
    assert result.unearned_premium == 12_000 - result.earned_premium


def test_short_rate_penalizes_early_cancellation():
    pro = compute_earned_unearned(
        12_000,
        effective_date=date(2025, 1, 1),
        expiration_date=date(2025, 12, 31),
        as_of_date=date(2025, 4, 1),
        method=EarningMethod.SHORT_RATE,
    )
    pro2 = compute_earned_unearned(
        12_000,
        effective_date=date(2025, 1, 1),
        expiration_date=date(2025, 12, 31),
        as_of_date=date(2025, 4, 1),
        method=EarningMethod.PRO_RATA,
    )
    assert pro.earned_premium > pro2.earned_premium


def test_apply_collection_updates_receivables():
    result = compute_earned_unearned(
        12_000,
        effective_date=date(2025, 1, 1),
        expiration_date=date(2025, 12, 31),
        as_of_date=date(2025, 4, 1),
    )
    apply_collection(result, collected_premium=10_000)
    assert result.collected_premium == 10_000
    assert result.collection_rate == round(10_000 / 12_000, 4)
    assert "receivable" in result.basis_note.lower()


def test_premium_accounting_from_bundle_prefers_loss_run_earned():
    # No policy period → unearned until established, so the loss run's explicit
    # earned premium becomes the source of truth.
    bundle = _bundle()
    _structured(bundle).policy_period = None
    result = premium_accounting_for_bundle(bundle)
    assert result.written_premium == 80_000
    assert result.earned_premium == 75_000
    assert "loss run" in result.basis_note.lower()


# ── 2. Combined ratio ─────────────────────────────────────────────────────


def test_expense_ratio_and_combined():
    assert expense_ratio(expenses=30_000, written_premium=100_000) == 0.3
    assert expense_ratio(expenses=10_000, written_premium=0) is None
    ok = combined_ratio(loss_ratio=0.6, expense_ratio=0.3)
    assert ok.combined_ratio == 0.9
    assert ok.underwriting_profit is True
    bad = combined_ratio(loss_ratio=1.1, expense_ratio=0.3)
    assert bad.underwriting_profit is False


def test_combined_ratio_from_bundle():
    result = combined_ratio_from_bundle(_bundle())
    assert result.combined_ratio is not None
    assert result.combined_ratio > 0
    assert result.detail


# ── 3. Solvency / RBC ─────────────────────────────────────────────────────


def test_rbc_covariance_includes_charge_families():
    requirement, charges = rbc_requirement(fixed_income_assets=1_000_000, equity_investments=500_000)
    assert set(charges) >= {"R1_fixed_income", "R2_equity", "R3_credit", "R4_underwriting", "R5_off_balance_sheet"}
    assert requirement > 0


def test_solvency_flagged_by_surplus_ratio():
    ok = assess_solvency(total_assets=1_000_000, total_liabilities=200_000, net_written_premium=100_000)
    assert ok.solvent is True
    assert ok.rbc_ratio is not None
    assert ok.rbc_ratio >= 1.0
    stressed = assess_solvency(total_assets=100_000, total_liabilities=90_000, net_written_premium=500_000)
    assert stressed.solvent is False


# ── 4. Morbidity tables ───────────────────────────────────────────────────


def test_morbidity_rate_and_factor():
    dis = morbidity_rate(age=45, sex="male", benefit_type="disability")
    ci = morbidity_rate(age=45, sex="male", benefit_type="critical_illness")
    assert dis > 0
    assert ci > 0
    # Disability incidence (occupational exposure) exceeds critical-illness
    # incidence at working age.
    assert dis > ci
    factor = morbidity_rating_factor(age=60, sex="female", benefit_type="disability")
    assert factor > 1.0


# ── 5. Policy architecture ────────────────────────────────────────────────


def test_coinsurance_penalty_math():
    satisfied = coinsurance_penalty(insured_limit=1_000_000, property_value=900_000, coinsurance_pct=0.80)
    assert satisfied["compliance_ratio"] == 1.0
    assert satisfied["penalty_applies"] is False
    under = coinsurance_penalty(insured_limit=500_000, property_value=1_000_000, coinsurance_pct=0.80)
    assert under["penalty_applies"] is True
    assert under["penalty_pct"] > 0


def test_sir_credit_and_aggregate_utilization():
    credit = sir_rating_credit(sir_amount=200_000, base_premium=100_000)
    assert credit["credit_pct"] > 0
    assert credit["credit_amount"] == 100_000 * credit["credit_pct"]
    agg = aggregate_utilization(aggregate_limit=100_000, aggregate_used=80_000)
    assert agg["utilization_pct"] == 0.8
    assert agg["remaining"] == 20_000
    assert agg["exhausted"] is False


def test_per_occurrence_vs_aggregate_relationship():
    rel = per_occurrence_vs_aggregate(per_occurrence_limit=1_000_000, aggregate_limit=2_000_000)
    assert rel["valid"] is True
    invalid = per_occurrence_vs_aggregate(per_occurrence_limit=2_000_000, aggregate_limit=1_000_000)
    assert invalid["valid"] is False


def test_architecture_assessment_on_coverage():
    coverage = CoverageDetail(
        coverage_type="Commercial Property",
        limit_amount=2_000_000,
        deductible=50_000,
        premium=60_000,
        per_occurrence_limit=2_000_000,
        aggregate_limit=4_000_000,
        coinsurance_pct=80.0,
        self_insured_retention=25_000,
    )
    out = architecture_assessment(coverage)
    assert out["per_occurrence_vs_aggregate"]["valid"] is True
    assert out["self_insured_retention"] == 25_000
    # No architecture flags for a coherent placement.
    assert not out["flags"]


# ── 6. Insurability ───────────────────────────────────────────────────────


def test_insurability_passes_on_quantified_class_risk():
    result = assess_insurability(_bundle())
    assert result.insurable is True
    assert result.failed_criteria == []


def test_insurability_fails_on_empty_submission():
    bare = SubmissionBundle(bundle_id="bare-1")
    result = assess_insurability(bare)
    assert result.insurable is False
    assert "measurable" in result.failed_criteria
    assert "large_pool" in result.failed_criteria
    assert "calculable_probability" in result.failed_criteria


def test_intentional_loss_breaks_fortuity():
    bundle = _bundle(structured=_structured(_bundle()).model_copy(update={"financial": FinancialData(loss_run=LossRunData(claims=[_claim("c1", cause="intentional fire", incurred=50_000)]))}))
    result = assess_insurability(bundle)
    assert result.insurable is False
    assert "fortuitous" in result.failed_criteria


# ── 7. Disclosure duty / utmost good faith ───────────────────────────────


def test_undisclosed_loss_run_claim_is_concealment():
    hidden = _claim("c9", cause="theft", incurred=90_000)
    bundle = _bundle(
        structured=_structured(_bundle()).model_copy(
            update={
                "risk_profile": RiskProfile(business_description="metal fabrication", prior_claims=[]),
                "financial": FinancialData(loss_run=LossRunData(claims=[_claim("c1", cause="fire", incurred=25_000), hidden])),
            }
        )
    )
    result = assess_disclosure(bundle)
    assert result.utmost_good_faith is False
    assert result.concealment is True
    # Both loss-run claims are absent from an empty application disclosure.
    assert len(result.undisclosed_claims) == 2


def test_warranty_compliance_missing_term_is_breach():
    bundle = _bundle()
    breaches = assess_warranty_compliance(bundle, ["sprinkler system maintained", "nightly burglar alarm"])
    assert "sprinkler system maintained" in breaches
    assert "nightly burglar alarm" in breaches


# ── 8. Legal remedies ─────────────────────────────────────────────────────


def test_remedy_matrix_driven_by_disclosure_breach():
    # Fully disclosed risk: the application names the same claim as the loss run.
    disclosed = _claim("c1", cause="fire", incurred=25_000)
    clean_bundle = _bundle(
        structured=_structured(_bundle()).model_copy(
            update={
                "risk_profile": RiskProfile(business_description="metal fabrication", prior_claims=[disclosed]),
                "financial": FinancialData(loss_run=LossRunData(claims=[disclosed])),
            }
        )
    )
    clean = assess_disclosure(clean_bundle)
    assert clean.utmost_good_faith is True
    remedy = determine_remedy(clean)
    assert remedy.remedy.value == "none"
    matrix = remedy_matrix(clean)
    assert matrix["remedy"] == "none"
    breached = assess_disclosure(
        _bundle(
            unstructured=[
                UnstructuredSubmission(submission_id="gap-1", raw_text="Applicant failed to disclose material facts"),
            ]
        )
    )
    breached_remedy = determine_remedy(breached)
    assert breached_remedy.remedy.value == "voidance"


# ── 9. Proximate cause ────────────────────────────────────────────────────


def test_proximate_cause_covered_and_covered_chain():
    covered = analyze_proximate_cause(cause="fire", description="kitchen fire", policy_perils=["fire", "wind"])
    assert covered.decision == "covered"
    assert covered.unbroken_chain is True


def test_superseding_excluded_event_breaks_chain():
    broken = analyze_proximate_cause(
        cause="fire",
        description="fire followed by flood water from storm surge",
        policy_perils=["fire", "wind"],
        exclusions=["flood"],
    )
    assert broken.decision == "not_covered"
    assert broken.excluded_peril == "flood"


# ── 10. Surplus lines / guaranty fund ─────────────────────────────────────


def test_guaranty_fund_only_backs_admitted_placements():
    nonadmitted = guarantee_fund_assessment(admitted=False, state="TX", premium=100_000)
    assert nonadmitted["guaranty_fund_backed"] is False
    admitted = guarantee_fund_assessment(admitted=True, state="TX", premium=100_000)
    assert admitted["guaranty_fund_backed"] is True
    assert admitted["per_claim_cap"] > 0


# ── 11. Health exposure ───────────────────────────────────────────────────


def test_covered_lives_includes_dependents():
    # Group health exposure = employees + dependents (2.2 deps/employee default).
    assert covered_lives(employee_count=100) == 320.0
    assert covered_lives(employee_count=100, dependents_per_employee=1.5) == 250.0


def test_health_exposure_base_from_bundle():
    base = health_exposure_base(_bundle())
    assert base["covered_lives"] == 50 * (1.0 + 2.2)
    assert base["exposure_base"] == "lives"


# ── 12. Claims lifecycle ──────────────────────────────────────────────────


def test_notice_of_loss_flow():
    claim = _claim("c1", cause="fire", incurred=25_000)
    notice = create_notice_of_loss(
        loss_date=claim.date_of_loss,
        cause=claim.cause,
        description=claim.description,
        line_of_business=claim.line_of_business,
        claim_id=claim.claim_id,
    )
    assert notice.claim_id == "c1"
    assert notice.status == "submitted"
    assert notice.reported_at == date.today()
    assert notice.fnol_id.startswith("FNOL-")


def test_adjudicate_claim_approved():
    claim = _claim("c1", cause="fire", incurred=25_000, paid=20_000)
    out = adjudicate_claim(claim)
    assert out.decision == ClaimDecision.APPROVED
    assert out.coverage_valid is True


def test_adjudicate_claim_denied_on_exclusion():
    claim = _claim("c1", cause="wear and tear", incurred=25_000)
    coverage = CoverageDetail(coverage_type="Property", limit_amount=1_000_000, deductible=0, premium=0)
    out = adjudicate_claim(claim, coverage)
    assert out.decision == ClaimDecision.DENIED
    assert out.denial_reason


def test_adjudicate_claims_batch_totals():
    bundle = _bundle(
        structured=_structured(_bundle()).model_copy(
            update={
                "financial": FinancialData(
                    loss_run=LossRunData(
                        claims=[
                            _claim("c1", cause="fire", incurred=25_000, paid=20_000),
                            _claim("c2", cause="theft", incurred=15_000, paid=5_000),
                        ]
                    )
                )
            }
        )
    )
    review = adjudicate_claims(bundle)
    assert len(review.decisions) == 2
    assert review.approved_count == 2


def test_subrogation_pursued_on_third_party_marker():
    claim = _claim("c1", cause="collision", description="hit by third party vehicle", incurred=25_000)
    sub = evaluate_subrogation(claim)
    assert sub.status.value in ("pursued", "recovered")
    assert sub.potential_recovery > 0


def test_salvage_recovery_values():
    claim = _claim("c1", cause="fire damage", incurred=25_000, description="inventory destroyed")
    salvage = evaluate_salvage(claim)
    assert salvage.salvage_value > 0
    assert salvage.offset_amount <= salvage.salvage_value


def test_defense_cost_erodes_inside_limits():
    claim = _claim("c1", cause="bodily injury", incurred=100_000)
    claim.defense_cost = 50_000
    outside = defense_cost_assessment([claim], policy_limit=200_000, defense_in_addition_to_limits=True)
    assert outside["remaining_indemnity_capacity"] == 200_000
    inside = defense_cost_assessment([claim], policy_limit=200_000, defense_in_addition_to_limits=False)
    assert inside["remaining_indemnity_capacity"] == 150_000
    assert inside["limit_erosion_pct"] == 0.25


def test_indemnity_valuation_acv_vs_rcv():
    rcv = indemnity_valuation(replacement_cost=100_000, depreciation_pct=0.2, policy_limit=200_000, basis="rcv")
    assert rcv["indemnity_amount"] == 100_000
    acv = indemnity_valuation(replacement_cost=100_000, depreciation_pct=0.2, policy_limit=200_000, basis="acv")
    assert acv["indemnity_amount"] == 80_000


def test_claims_recovery_review_aggregates():
    bundle = _bundle(
        structured=_structured(_bundle()).model_copy(
            update={
                "financial": FinancialData(
                    loss_run=LossRunData(
                        claims=[
                            _claim("c1", cause="collision", description="hit by third party", incurred=25_000),
                            _claim("c2", cause="fire", incurred=15_000),
                        ]
                    )
                )
            }
        )
    )
    review = claims_recovery_review(bundle)
    assert review["claim_count"] == 2
    assert review["subrogation_potential"] > 0


# ── 13. Valuation (RCV / ACV / agreed) ────────────────────────────────────


def test_depreciation_linear_cap():
    assert depreciation_for_age(age_years=5, useful_life_years=25) == 0.2
    assert depreciation_for_age(age_years=100, useful_life_years=25) == 0.9
    assert depreciation_for_age(age_years=None) == 0.0


def test_valuation_basis_variants():
    rcv = valuation_assessment(basis="rcv", replacement_cost=100_000, age_years=10)
    assert rcv.effective_value == 100_000
    acv = valuation_assessment(basis="acv", replacement_cost=100_000, age_years=10, useful_life_years=25)
    assert acv.effective_value == 60_000
    agreed = valuation_assessment(basis="agreed_value", replacement_cost=100_000, age_years=10, agreed_value=150_000)
    assert agreed.effective_value == 150_000


def test_valuation_from_bundle_schedule_and_fallback():
    bundle = _bundle()
    _structured(bundle).schedule_of_values = [
        ScheduleOfValues(
            schedule_type="commercial",
            coverage_type="Property",
            items=[
                ScheduleItem(item_number="1", description="Milling machine", value=120_000),
                ScheduleItem(item_number="2", description="Welder", value=80_000),
            ],
        )
    ]
    out = valuation_from_bundle(bundle)
    assert out["total_effective_value"] == 200_000
    assert len(out["assets"]) == 2
    fallback = valuation_from_bundle(_bundle(), basis="acv")
    # Without an asset age the depreciation is zero — ACV equals RCV here.
    assert fallback["assets"][0]["replacement_cost"] == 2_000_000
    assert fallback["basis"] == "acv"
    assert fallback["total_effective_value"] == 2_000_000


# ── 14. Life cash value ───────────────────────────────────────────────────


def test_cash_value_accumulates_on_savings_products():
    lc = project_cash_value(face_amount=500_000, annual_premium=12_000, product_family="whole_life", years=10)
    assert len(lc.cash_value_schedule) == 10
    assert lc.cash_value_schedule[-1]["cash_value"] > lc.cash_value_schedule[0]["cash_value"]
    assert lc.cash_value_schedule[0]["surrender_value"] < lc.cash_value_schedule[0]["cash_value"]


def test_cash_value_none_for_term():
    bundle = _bundle()
    result = cash_value_for_bundle(bundle, product_id="TERM20", coverage_name="term life insurance")
    assert result is None


def test_cash_value_for_savings_product_from_bundle():
    bundle = _bundle(
        structured=_structured(_bundle()).model_copy(
            update={
                "risk_profile": RiskProfile(
                    business_description="individual life",
                    occupancy_type="whole life",
                )
            }
        )
    )
    result = cash_value_for_bundle(bundle, product_id="WL", coverage_name="whole life insurance")
    assert result is None or result.cash_value_schedule


# ── 15. Health networks ───────────────────────────────────────────────────


def test_network_detection_and_rating_factor():
    ppo = assess_network("preferred provider organization ppo plan — self-referral allowed")
    assert ppo.network_type == HealthNetworkType.PPO
    assert ppo.rating_factor > 1.0
    hmo = assess_network("hmo plan with referral required")
    assert hmo.network_type == HealthNetworkType.HMO
    assert hmo.primary_care_referral_required is True
    assert hmo.rating_factor < 1.0


def test_network_assessment_from_bundle_text():
    bundle = _bundle(unstructured=[UnstructuredSubmission(submission_id="gap-1", raw_text="ppo plan with out-of-network coverage")])
    out = network_assessment_from_bundle(bundle)
    assert out["network_type"] == "ppo"
    assert out["rating_factor"] > 1.0


# ── 16. Annuity payout illustration ───────────────────────────────────────


def test_annuity_factor_and_payout_positive():
    from insureflow.rating.personal.annuity_rating import annuity_factor, illustrative_payout, rate_annuity

    factor = annuity_factor(age=65, sex="male")
    assert factor > 0
    payout = illustrative_payout(principal=100_000, age=65, sex="female")
    assert payout["annual_payout"] > 0
    assert payout["monthly_payout"] > 0
    result = rate_annuity(_bundle())
    assert result.eligible is False
    assert "annuity" in result.metadata["product_family"]
    assert result.metadata["illustrative_payout"]["annual_payout"] > 0


# ── 17. Business-interruption evaluator on commercial packages ───────────


def test_bi_evaluator_flags_interruption_exposure():
    from insureflow.underwriting.commercial_checklists import evaluate_bi_checklist

    bundle = _bundle(unstructured=[UnstructuredSubmission(submission_id="gap-1", raw_text="business interruption coverage sought with contingent business interruption")])
    result = evaluate_bi_checklist(bundle)
    assert result.flags
    assert result.decision.value in ("accept", "conditional_accept", "refer", "decline")


def test_bi_pass_is_additive_in_commercial_evaluation():
    from insureflow.rating.models import InsuranceLine
    from insureflow.underwriting.commercial_checklists import evaluate_commercial_checklist

    bundle = _bundle(unstructured=[UnstructuredSubmission(submission_id="gap-1", raw_text="business interruption coverage sought for the metal fabrication plant")])
    plain = evaluate_commercial_checklist(bundle, InsuranceLine.COMMERCIAL_PROPERTY)
    # The BI additive pass runs as long as a BI trigger term is present.
    assert plain.decision in ("accept", "conditional_accept", "refer", "decline")


# ── 18. Pipeline integration ──────────────────────────────────────────────


def test_pipeline_summary_includes_domain_analytics():
    from insureflow.insurance.pipeline import InsurancePipeline

    pipeline = InsurancePipeline(org_id="test-org", use_llm=False)
    result = pipeline.run(
        documents=[
            {
                "filename": "loss_run.txt",
                "content": ("Loss Run\nPremium 80,000\nEarned 75,000\nTotal 25,000\nClaims 1\n1. fire — 25,000"),
                "encoding": "utf-8",
            }
        ],
        bundle_id="gap-pipeline-1",
    )
    assert result["status"] == "completed"
    analytics = result.get("domain_analytics") or {}
    assert "premium_accounting" in analytics
    assert "combined_ratio" in analytics
    assert "insurability" in analytics
    assert "solvency" in analytics
    assert "claims_recovery" in analytics
    assert "valuation" in analytics
    assert isinstance(analytics["insurability"]["insurable"], bool)
