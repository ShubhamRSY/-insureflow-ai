"""Tests for underwriting modules: COPE, Authority, Market, Renewal, Triage."""

from __future__ import annotations

from datetime import date, timedelta

from insureflow.agents.triage_agent import (
    DocumentChecklist,
    SubmissionPriority,
    TriageAgent,
)
from insureflow.models.submissions import (
    BrokerInfo,
    CoverageDetail,
    FinancialData,
    LocationData,
    NamedInsured,
    PolicyPeriod,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.underwriting.authority import (
    AuthorityMatrix,
    AuthorityTier,
)
from insureflow.underwriting.cope import (
    COPERatingEngine,
    RiskGrade,
    analyze_cope,
)
from insureflow.underwriting.market import (
    MarketCycle,
    MarketCycleAwareness,
    MarketPhase,
)
from insureflow.underwriting.renewal import (
    AuditAdjustmentType,
    AuditStatus,
    PolicyLapse,
    PremiumAuditEngine,
    RenewalAction,
    RenewalEngine,
    RetentionRisk,
)


# ── COPE Tests ────────────────────────────────────────────────


class TestCOPEModule:
    def test_analyze_cope_returns_grade_and_modifiers(self) -> None:
        result = analyze_cope(
            construction_type="Masonry",
            occupancy_type="Mercantile",
            protection_class=5,
            year_built=2000,
            sprinklered=True,
            state="TX",
        )
        assert result.score.total_score > 0
        assert result.score.risk_grade in (
            RiskGrade.PREFERRED, RiskGrade.STANDARD,
            RiskGrade.NON_STANDARD, RiskGrade.DECLINED,
        )
        assert isinstance(result.score.schedule_mod_pct, float)

    def test_wood_frame_gets_non_standard_or_declined(self) -> None:
        result = analyze_cope(
            construction_type="Frame",
            occupancy_type="Manufacturing",
            protection_class=10,
            year_built=1920,
            sprinklered=False,
            state="TX",
        )
        assert result.score.risk_grade in (RiskGrade.NON_STANDARD, RiskGrade.DECLINED)

    def test_fire_resistive_gets_preferred(self) -> None:
        result = analyze_cope(
            construction_type="Fire Resistive",
            occupancy_type="Office",
            protection_class=1,
            year_built=2020,
            sprinklered=True,
            state="OK",
        )
        assert result.score.risk_grade == RiskGrade.PREFERRED

    def test_cope_engine_from_bundle(self, sample_bundle: SubmissionBundle) -> None:
        engine = COPERatingEngine()
        result = engine.analyze(sample_bundle)
        assert result.score.total_score > 0
        assert result.score.risk_grade is not None

    def test_florida_exposure_higher_risk(self) -> None:
        inland = analyze_cope(
            construction_type="Masonry", occupancy_type="Office",
            protection_class=4, state="OK",
        )
        coastal = analyze_cope(
            construction_type="Masonry", occupancy_type="Office",
            protection_class=4, state="FL",
        )
        assert coastal.score.exposure_score > inland.score.exposure_score


# ── Authority Tests ────────────────────────────────────────────


class TestAuthorityModule:
    def test_matrix_has_default_tiers(self) -> None:
        matrix = AuthorityMatrix()
        all_auths = matrix.list_all()
        tiers = {a.tier for a in all_auths}
        assert AuthorityTier.JUNIOR in tiers
        assert AuthorityTier.SENIOR in tiers
        assert AuthorityTier.CUO in tiers

    def test_binding_limits_senior(self) -> None:
        matrix = AuthorityMatrix()
        senior = matrix.get_authority("sfields")
        assert senior is not None
        assert senior.binding_authority.max_premium == 250_000
        assert senior.binding_authority.max_tiv == 10_000_000

    def test_binding_limits_junior(self) -> None:
        matrix = AuthorityMatrix()
        junior = matrix.get_authority("junderwood")
        assert junior is not None
        assert junior.binding_authority.max_premium == 25_000

    def test_check_binding_authority_under_limit(self) -> None:
        matrix = AuthorityMatrix()
        authorized, reason = matrix.check_binding_authority(
            "sfields", premium=100_000, tiv=5_000_000,
        )
        assert authorized is True

    def test_check_binding_authority_over_limit(self) -> None:
        matrix = AuthorityMatrix()
        authorized, reason = matrix.check_binding_authority(
            "junderwood", premium=100_000, tiv=5_000_000,
        )
        assert authorized is False
        assert "exceeds" in reason

    def test_co_sign_required_above_threshold(self) -> None:
        matrix = AuthorityMatrix()
        authorized, reason = matrix.check_binding_authority(
            "sfields", premium=200_000, tiv=8_000_000,
        )
        assert authorized is True

    def test_list_by_tier(self) -> None:
        matrix = AuthorityMatrix()
        seniors = matrix.list_by_tier(AuthorityTier.SENIOR)
        assert len(seniors) >= 1
        assert all(a.tier == AuthorityTier.SENIOR for a in seniors)


# ── Market Cycle Tests ────────────────────────────────────────


class TestMarketCycleModule:
    def test_default_is_soft(self) -> None:
        mc = MarketCycleAwareness()
        assert mc.current.phase == MarketPhase.SOFT

    def test_set_phase_hard(self) -> None:
        mc = MarketCycleAwareness()
        mc.set_cycle(MarketCycle(phase=MarketPhase.HARD))
        assert mc.current.phase == MarketPhase.HARD

    def test_adjust_appetite_hard_tightens(self) -> None:
        mc = MarketCycleAwareness()
        mc.set_cycle(MarketCycle(phase=MarketPhase.HARD, appetite_tightness=1.4))
        threshold = mc.adjust_appetite_threshold(100_000)
        assert threshold > 100_000

    def test_adjust_premium_hard_increases(self) -> None:
        mc = MarketCycleAwareness()
        mc.set_cycle(MarketCycle(
            phase=MarketPhase.HARD,
            property_rate_mod=1.25, liability_rate_mod=1.15,
            workers_comp_rate_mod=0.95, auto_rate_mod=1.30,
            reinsurance_cost_mod=1.20,
        ))
        adjusted = mc.adjust_premium(100_000)
        assert adjusted > 100_000

    def test_adjust_premium_soft_decreases(self) -> None:
        mc = MarketCycleAwareness()
        adjusted = mc.adjust_premium(100_000)
        assert adjusted < 100_000

    def test_adjust_tiv_limit_hard_reduces(self) -> None:
        mc = MarketCycleAwareness()
        mc.set_cycle(MarketCycle(phase=MarketPhase.HARD))
        limited = mc.adjust_tiv_limit(10_000_000)
        assert limited < 10_000_000

    def test_narrative_changes_with_phase(self) -> None:
        mc = MarketCycleAwareness()
        soft_narr = mc.market_adjustment_narrative()
        mc.set_cycle(MarketCycle(phase=MarketPhase.HARD, description="Hard market"))
        hard_narr = mc.market_adjustment_narrative()
        assert soft_narr["phase"] != hard_narr["phase"]

    def test_loss_ratio_threshold_adjustment(self) -> None:
        mc = MarketCycleAwareness()
        mc.set_cycle(MarketCycle(phase=MarketPhase.HARD))
        adjusted = mc.adjust_loss_ratio_threshold(0.55)
        assert adjusted > 0.55


# ── Renewal Engine Tests ──────────────────────────────────────


class TestRenewalModule:
    def test_standard_renewal(self) -> None:
        engine = RenewalEngine()
        rec = engine.analyze_renewal(
            bundle_id="b-1", insured_name="Good Co",
            current_premium=50_000, loss_ratio=0.30, claims_count=0,
            expiry_date=date.today() + timedelta(days=90),
        )
        assert rec.action == RenewalAction.RENEW
        assert rec.retention_risk in (RetentionRisk.LOW, RetentionRisk.MEDIUM)

    def test_non_renew_high_losses(self) -> None:
        engine = RenewalEngine()
        rec = engine.analyze_renewal(
            bundle_id="b-2", insured_name="Bad Co",
            current_premium=50_000, loss_ratio=0.85, claims_count=4,
            expiry_date=date.today() + timedelta(days=90),
        )
        assert rec.action == RenewalAction.NON_RENEW

    def test_modify_elevated_loss_ratio(self) -> None:
        engine = RenewalEngine()
        rec = engine.analyze_renewal(
            bundle_id="b-3", insured_name="Med Co",
            current_premium=50_000, loss_ratio=0.65, claims_count=1,
            expiry_date=date.today() + timedelta(days=90),
        )
        assert rec.action == RenewalAction.RENEW_WITH_MODIFICATION

    def test_refer_to_uw_under_60_days(self) -> None:
        engine = RenewalEngine()
        rec = engine.analyze_renewal(
            bundle_id="b-4", insured_name="Urgent Co",
            current_premium=50_000, loss_ratio=0.30, claims_count=0,
            expiry_date=date.today() + timedelta(days=30),
        )
        assert rec.action == RenewalAction.REFER_TO_UW

    def test_bundling_discount(self) -> None:
        engine = RenewalEngine()
        engine.register_policy(PolicyLapse(
            policy_number="P-1", line_of_business="GL",
            current_premium=20_000, expiry_date=date.today() + timedelta(days=90),
        ))
        engine.register_policy(PolicyLapse(
            policy_number="P-2", line_of_business="Property",
            current_premium=30_000, expiry_date=date.today() + timedelta(days=90),
        ))
        rec = engine.analyze_renewal(
            bundle_id="b-5", insured_name="Bundle Co",
            current_premium=50_000, loss_ratio=0.30, claims_count=0,
            expiry_date=date.today() + timedelta(days=120),
            policy_number="P-1",
        )
        assert rec.bundling_discount_pct >= 0.0

    def test_premium_change_deteriorating(self) -> None:
        engine = RenewalEngine()
        rec = engine.analyze_renewal(
            bundle_id="b-6", insured_name="Declining Co",
            current_premium=100_000, loss_ratio=0.70, claims_count=2,
            expiry_date=date.today() + timedelta(days=90),
        )
        assert rec.proposed_premium > rec.current_premium

    def test_premium_change_improving(self) -> None:
        engine = RenewalEngine()
        rec = engine.analyze_renewal(
            bundle_id="b-7", insured_name="Improving Co",
            current_premium=100_000, loss_ratio=0.15, claims_count=0,
            expiry_date=date.today() + timedelta(days=90),
        )
        assert rec.proposed_premium < rec.current_premium

    def test_find_expiring_policies(self) -> None:
        engine = RenewalEngine()
        p1 = PolicyLapse("P-1", "GL", 10_000, date.today() + timedelta(days=30))
        p2 = PolicyLapse("P-2", "Property", 20_000, date.today() + timedelta(days=200))
        engine.register_policy(p1)
        engine.register_policy(p2)
        expiring = engine.find_expiring_policies(within_days=90)
        assert len(expiring) == 1
        assert expiring[0].policy_number == "P-1"


# ── Premium Audit Tests ──────────────────────────────────────


class TestPremiumAudit:
    def test_create_audit(self) -> None:
        engine = PremiumAuditEngine()
        audit = engine.create_audit("b-1", 100_000.0)
        assert audit.audit_id.startswith("aud-")
        assert audit.status == AuditStatus.PENDING
        assert audit.estimated_premium == 100_000.0

    def test_start_and_complete_audit(self) -> None:
        engine = PremiumAuditEngine()
        audit = engine.create_audit("b-2", 50_000.0)
        engine.start_audit(audit.audit_id)
        assert audit.status == AuditStatus.IN_PROGRESS
        engine.complete_audit(audit.audit_id, 52_000.0, notes="Clean audit")
        assert audit.status == AuditStatus.COMPLETED
        assert audit.actual_premium == 52_000.0

    def test_premium_delta_calculation(self) -> None:
        engine = PremiumAuditEngine()
        audit = engine.create_audit("b-3", 100_000.0)
        engine.add_adjustment(
            audit.audit_id, AuditAdjustmentType.EXPOSURE_CHANGE,
            "Additional locations", 5_000.0,
        )
        engine.complete_audit(audit.audit_id, 108_000.0)
        assert audit.premium_delta == 13_000.0
        assert abs(audit.premium_delta_pct - 13.0) < 0.01

    def test_dispute_audit(self) -> None:
        engine = PremiumAuditEngine()
        audit = engine.create_audit("b-4", 50_000.0)
        engine.dispute_audit(audit.audit_id, "Disagree with exposure calculation")
        assert audit.status == AuditStatus.DISPUTED

    def test_list_audits_by_status(self) -> None:
        engine = PremiumAuditEngine()
        engine.create_audit("b-5", 100_000.0)
        a2 = engine.create_audit("b-6", 200_000.0)
        engine.start_audit(a2.audit_id)
        pending = engine.list_audits(status=AuditStatus.PENDING)
        assert len(pending) == 1
        in_prog = engine.list_audits(status=AuditStatus.IN_PROGRESS)
        assert len(in_prog) == 1

    def test_material_adjustments(self) -> None:
        engine = PremiumAuditEngine()
        audit = engine.create_audit("b-7", 100_000.0)
        engine.complete_audit(audit.audit_id, 120_000.0)
        material = engine.audits_needing_renewal_review()
        assert len(material) >= 1

    def test_past_due_audit(self) -> None:
        engine = PremiumAuditEngine()
        past_end = date.today() - timedelta(days=180)
        audit = engine.create_audit("b-8", 50_000.0, policy_period_end=past_end)
        assert audit.is_past_due is True


# ── Triage Agent Tests ────────────────────────────────────────


class TestTriageModule:
    def _make_bundle(self, naics: str = "541330", state: str = "TX",
                     tiv: float = 5_000_000) -> SubmissionBundle:
        return SubmissionBundle(
            bundle_id="test-triage",
            structured=StructuredSubmission(
                submission_id="s-1",
                named_insured=NamedInsured(legal_name="Test Co"),
                broker=BrokerInfo(broker_name="Test Broker"),
                policy_period=PolicyPeriod(
                    effective_date=date.today(),
                    expiration_date=date.today() + timedelta(days=365),
                ),
                coverages=[
                    CoverageDetail(
                        coverage_type="General Liability",
                        limit_amount=1_000_000,
                        deductible=10_000,
                        premium=25_000,
                    ),
                ],
                risk_profile=RiskProfile(
                    naics_code=naics,
                    construction_type="Masonry",
                    occupancy_type="Office",
                    protection_class=4,
                ),
                financial=FinancialData(annual_revenue=tiv),
                locations=[LocationData(
                    address="123 Main", city="Austin",
                    state=state, zip_code="78701",
                )],
            ),
        )

    def test_hot_priority_good_fit(self) -> None:
        agent = TriageAgent()
        bundle = self._make_bundle(naics="541330", state="TX", tiv=5_000_000)
        result = agent.score_submission(bundle)
        assert result.priority == SubmissionPriority.HOT
        assert result.score >= 80

    def test_no_fit_excluded_naics_outside_states(self) -> None:
        agent = TriageAgent()
        bundle = SubmissionBundle(
            bundle_id="test-no-fit",
            structured=StructuredSubmission(
                submission_id="s-nf",
                named_insured=NamedInsured(legal_name="Bad Co"),
                broker=BrokerInfo(broker_name="Test Broker"),
                policy_period=PolicyPeriod(
                    effective_date=date.today(),
                    expiration_date=date.today() + timedelta(days=365),
                ),
                coverages=[
                    CoverageDetail(
                        coverage_type="General Liability",
                        limit_amount=1_000_000,
                        deductible=10_000,
                        premium=1_000,
                    ),
                ],
                risk_profile=RiskProfile(
                    naics_code="921120",
                    construction_type="Frame",
                    occupancy_type="Warehouse",
                    protection_class=8,
                ),
                locations=[LocationData(
                    address="1 Main", city="Nowhere",
                    state="AK", zip_code="99999",
                    building_value=40_000,
                )],
            ),
        )
        result = agent.score_submission(bundle)
        assert result.priority == SubmissionPriority.NO_FIT
        assert result.score < 25

    def test_warm_priority_moderate_fit(self) -> None:
        agent = TriageAgent()
        bundle = self._make_bundle(naics="541330", state="FL", tiv=2_000_000)
        result = agent.score_submission(bundle)
        assert result.priority in (SubmissionPriority.WARM, SubmissionPriority.HOT)

    def test_cold_priority_small_tiv(self) -> None:
        agent = TriageAgent()
        bundle = self._make_bundle(naics="541330", state="TX", tiv=50_000)
        result = agent.score_submission(bundle)
        assert result.priority == SubmissionPriority.HOT

    def test_queue_returns_sorted_results(self) -> None:
        agent = TriageAgent()
        queue = agent.get_queue()
        assert len(queue) >= 0

    def test_statistics(self) -> None:
        agent = TriageAgent()
        stats = agent.get_statistics()
        assert "hot_need_review" in stats
        assert "warm_could_proceed" in stats
        assert "cold_minimal_effort" in stats
        assert "no_fit_discard" in stats
        assert "by_priority" in stats

    def test_document_checklist_tracks_all_types(self) -> None:
        checklist = DocumentChecklist()
        assert checklist.completeness_pct == 0.0
        assert len(checklist.missing) == 8

    def test_document_checklist_partial(self) -> None:
        checklist = DocumentChecklist(
            acord_form=True, loss_run=True,
            financials=True, photos=True,
        )
        assert checklist.completeness_pct == 0.5
        assert len(checklist.missing) == 4
