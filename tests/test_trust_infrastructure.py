"""Tests for the underwriter trust infrastructure — all 5 pillars."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

# ── Pillar 4a: Audit Hash Chain ──────────────────────────────────────────────


class TestAuditHashChain:
    def test_append_and_retrieve(self):
        from insureflow.audit.hash_chain import AuditHashChain

        chain = AuditHashChain(org_id="test-org")
        r1 = chain.append("r1", "b1", "extraction_start", message="started")
        r2 = chain.append("r2", "b1", "extraction_complete", message="done")
        assert chain.length == 2
        assert chain.head_hash == r2.record_hash
        assert chain.get("r1") is r1
        assert chain.get("r2") is r2
        assert chain.get("r3") is None

    def test_hash_links_previous(self):
        from insureflow.audit.hash_chain import AuditHashChain

        chain = AuditHashChain()
        r1 = chain.append("r1", "b1", "event")
        r2 = chain.append("r2", "b1", "event")
        assert r1.previous_hash == ""
        assert r2.previous_hash == r1.record_hash

    def test_verify_clean_chain(self):
        from insureflow.audit.hash_chain import AuditHashChain

        chain = AuditHashChain()
        chain.append("r1", "b1", "event")
        chain.append("r2", "b1", "event")
        chain.append("r3", "b1", "event")
        result = chain.verify()
        assert result.valid is True
        assert result.chain_length == 3

    def test_verify_detects_tampering(self):
        from insureflow.audit.hash_chain import AuditHashChain

        chain = AuditHashChain()
        chain.append("r1", "b1", "event")
        chain.append("r2", "b1", "event")
        chain._records[0].message = "TAMPERED"
        result = chain.verify()
        assert result.valid is False
        assert result.broken_record_id == "r1"

    def test_verify_detects_broken_link(self):
        from insureflow.audit.hash_chain import AuditHashChain

        chain = AuditHashChain()
        chain.append("r1", "b1", "event")
        chain.append("r2", "b1", "event")
        chain._records[1].previous_hash = "fake-hash"
        result = chain.verify()
        assert result.valid is False
        assert result.broken_record_id == "r2"

    def test_verify_empty_chain(self):
        from insureflow.audit.hash_chain import AuditHashChain

        chain = AuditHashChain()
        result = chain.verify()
        assert result.valid is True
        assert result.chain_length == 0

    def test_records_for_bundle(self):
        from insureflow.audit.hash_chain import AuditHashChain

        chain = AuditHashChain()
        chain.append("r1", "b1", "event")
        chain.append("r2", "b2", "event")
        chain.append("r3", "b1", "event")
        b1_records = chain.records_for_bundle("b1")
        assert len(b1_records) == 2

    def test_export_and_import(self):
        from insureflow.audit.hash_chain import AuditHashChain

        chain = AuditHashChain(org_id="test")
        chain.append("r1", "b1", "event")
        chain.append("r2", "b1", "event")
        exported = chain.export_chain()
        restored = AuditHashChain.from_export(exported, org_id="test")
        assert restored.length == 2
        assert restored.verify().valid is True

    def test_compute_hash_deterministic(self):
        from insureflow.audit.hash_chain import ChainedAuditRecord

        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        r1 = ChainedAuditRecord(
            record_id="r1",
            bundle_id="b1",
            org_id="o1",
            event_kind="test",
            timestamp=now,
        )
        r2 = ChainedAuditRecord(
            record_id="r1",
            bundle_id="b1",
            org_id="o1",
            event_kind="test",
            timestamp=now,
        )
        assert r1.compute_hash() == r2.compute_hash()


# ── Pillar 5a: Decision Abstention ───────────────────────────────────────────


class TestAbstention:
    def test_sufficient_data_no_abstention(self):
        from insureflow.underwriting.abstention import evaluate_abstention

        fields = {
            "total_assets": "1000000",
            "named_insured": "Acme Corp",
            "premium": "50000",
            "coverage": "CGL",
            "effective_date": "2026-01-01",
            "limit": "1000000",
            "deductible": "5000",
        }
        verdict = evaluate_abstention(fields)
        assert verdict.abstain is False

    def test_insufficient_data_abstains(self):
        from insureflow.underwriting.abstention import AbstentionReason, evaluate_abstention

        fields = {"total_assets": "1000000"}
        verdict = evaluate_abstention(fields)
        assert verdict.abstain is True
        assert AbstentionReason.INSUFFICIENT_DATA in verdict.reasons

    def test_low_confidence_abstains(self):
        from insureflow.underwriting.abstention import AbstentionReason, evaluate_abstention

        fields = {f"field_{i}": f"val_{i}" for i in range(5)}
        verdict = evaluate_abstention(fields, field_confidences=[0.1, 0.2, 0.15, 0.1, 0.2])
        assert verdict.abstain is True
        assert AbstentionReason.LOW_CONFIDENCE in verdict.reasons

    def test_verification_failed_abstains(self):
        from insureflow.underwriting.abstention import AbstentionReason, evaluate_abstention

        report = MagicMock()
        report.passed = False
        report.issues = []
        fields = {f"field_{i}": f"val_{i}" for i in range(5)}
        verdict = evaluate_abstention(fields, verification_report=report)
        assert verdict.abstain is True
        assert AbstentionReason.VERIFICATION_FAILED in verdict.reasons

    def test_high_error_ratio_abstains(self):
        from insureflow.underwriting.abstention import AbstentionReason, evaluate_abstention

        issues = []
        for i in range(4):
            issue = MagicMock()
            issue.severity = "error"
            issues.append(issue)
        for i in range(2):
            issue = MagicMock()
            issue.severity = "warning"
            issues.append(issue)
        report = MagicMock()
        report.passed = True
        report.issues = issues
        fields = {f"field_{i}": f"val_{i}" for i in range(5)}
        verdict = evaluate_abstention(fields, verification_report=report)
        assert verdict.abstain is True
        assert AbstentionReason.HIGH_ERROR_RATIO in verdict.reasons

    def test_missing_critical_fields_abstains(self):
        from insureflow.underwriting.abstention import AbstentionReason, evaluate_abstention

        fields = {"random_field_1": "x", "random_field_2": "y", "random_field_3": "z"}
        verdict = evaluate_abstention(fields)
        assert verdict.abstain is True
        assert AbstentionReason.MISSING_CRITICAL_FIELDS in verdict.reasons

    def test_message_populated_on_abstain(self):
        from insureflow.underwriting.abstention import evaluate_abstention

        fields = {"f": "v"}
        verdict = evaluate_abstention(fields)
        assert verdict.abstain is True
        assert verdict.message != ""


# ── Pillar 5b: Circuit Breaker ───────────────────────────────────────────────


class TestCircuitBreaker:
    def test_starts_closed(self):
        from insureflow.verification.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_available is True

    def test_opens_after_threshold(self):
        from insureflow.verification.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_available is False

    def test_recovery_to_half_open(self):
        import time

        from insureflow.verification.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN  # type: ignore[comparison-overlap]
        assert cb.is_available is True

    def test_half_open_success_closes(self):
        import time

        from insureflow.verification.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.05, half_open_max_calls=1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.1)
        _ = cb.state
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        import time

        from insureflow.verification.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.05)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.1)
        _ = cb.state
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_decrements_failures(self):
        from insureflow.verification.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        status = cb.status()
        assert status["failure_count"] == 1

    def test_reset(self):
        from insureflow.verification.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker(name="test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN  # type: ignore[comparison-overlap]
        cb.reset()
        assert cb.state == CircuitState.CLOSED  # type: ignore[comparison-overlap]
        assert cb.status()["failure_count"] == 0

    def test_history_tracked(self):
        from insureflow.verification.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        events = cb.recent_events()
        assert len(events) >= 1

    def test_status_dict(self):
        from insureflow.verification.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(name="test")
        s = cb.status()
        assert s["name"] == "test"
        assert "state" in s
        assert "failure_count" in s


# ── Pillar 2a: Confidence Routing ────────────────────────────────────────────


class TestConfidenceRouting:
    def test_high_confidence_stp(self):
        from insureflow.underwriting.confidence_routing import RoutingTier, route_decision

        fields = {f"f{i}": f"v{i}" for i in range(8)}
        confidences = [0.98] * 8
        decision = route_decision(fields, field_confidences=confidences)
        assert decision.tier == RoutingTier.STP

    def test_low_confidence_routes_up(self):
        from insureflow.underwriting.confidence_routing import RoutingTier, route_decision

        fields = {f"f{i}": f"v{i}" for i in range(8)}
        confidences = [0.2] * 8
        decision = route_decision(fields, field_confidences=confidences)
        assert decision.tier in (RoutingTier.CUO, RoutingTier.SENIOR)

    def test_few_fields_complexity(self):
        from insureflow.underwriting.confidence_routing import RoutingTier, route_decision

        fields = {"f1": "v1", "f2": "v2"}
        decision = route_decision(fields)
        assert decision.tier != RoutingTier.STP or decision.complexity_score > 0

    def test_co_sign_for_high_complexity(self):
        from insureflow.underwriting.confidence_routing import route_decision

        fields = {f"f{i}": f"v{i}" for i in range(8)}
        confidences = [0.1] * 8
        decision = route_decision(fields, field_confidences=confidences)
        assert decision.requires_co_sign is True

    def test_reasons_populated(self):
        from insureflow.underwriting.confidence_routing import route_decision

        fields = {f"f{i}": f"v{i}" for i in range(8)}
        decision = route_decision(fields, field_confidences=[0.5] * 8)
        assert len(decision.reasons) > 0

    def test_confidence_score_computed(self):
        from insureflow.underwriting.confidence_routing import route_decision

        fields = {f"f{i}": f"v{i}" for i in range(5)}
        decision = route_decision(fields, field_confidences=[0.6, 0.7, 0.8, 0.9, 1.0])
        assert 0.6 <= decision.confidence_score <= 1.0


# ── Pillar 4b: Bias Monitoring ───────────────────────────────────────────────


class TestBiasMonitor:
    def test_record_and_bucketize(self):
        from insureflow.analytics.bias_monitor import BiasDimension, BiasMonitor

        mon = BiasMonitor()
        mon.record("s1", "accept", {"state": "CA"}, 50000, 0.9)
        mon.record("s2", "decline", {"state": "NY"}, 30000, 0.4)
        mon.record("s3", "accept", {"state": "CA"}, 60000, 0.85)
        report = mon.generate_report([BiasDimension.STATE])
        assert report.total_submissions == 3
        assert len(report.buckets) == 2

    def test_disparate_impact_detection(self):
        from insureflow.analytics.bias_monitor import BiasDimension, BiasMonitor

        mon = BiasMonitor()
        for i in range(10):
            mon.record(f"s{i}", "accept", {"state": "CA"}, 50000, 0.9)
        for i in range(10):
            mon.record(f"d{i}", "decline", {"state": "NY"}, 30000, 0.4)
        report = mon.generate_report([BiasDimension.STATE])
        assert len(report.alerts) >= 1
        assert report.alerts[0].ratio < 1.0

    def test_no_alerts_when_balanced(self):
        from insureflow.analytics.bias_monitor import BiasDimension, BiasMonitor

        mon = BiasMonitor()
        for i in range(5):
            mon.record(f"s{i}", "accept", {"state": "CA"})
            mon.record(f"d{i}", "accept", {"state": "NY"})
        report = mon.generate_report([BiasDimension.STATE])
        assert len(report.alerts) == 0

    def test_approval_rate_computed(self):
        from insureflow.analytics.bias_monitor import BiasDimension, BiasMonitor

        mon = BiasMonitor()
        mon.record("s1", "accept", {"state": "CA"})
        mon.record("s2", "decline", {"state": "CA"})
        mon.record("s3", "accept", {"state": "CA"})
        report = mon.generate_report([BiasDimension.STATE])
        assert report.overall_approval_rate == pytest.approx(2 / 3, abs=0.01)

    def test_summary_fields(self):
        from insureflow.analytics.bias_monitor import BiasReport

        report = BiasReport(total_submissions=10, overall_approval_rate=0.7)
        assert report.total_submissions == 10


# ── Pillar 2b: Active Learning ───────────────────────────────────────────────


class TestActiveLearning:
    def test_record_correction(self):
        from insureflow.outcomes.active_learning import ActiveLearningEngine

        engine = ActiveLearningEngine()
        signal = engine.record_correction("b1", "premium", "50000", "55000", confidence=0.8)
        assert signal.ai_value == "50000"
        assert signal.human_value == "55000"
        assert len(engine._signals) == 1

    def test_signals_for_field(self):
        from insureflow.outcomes.active_learning import ActiveLearningEngine

        engine = ActiveLearningEngine()
        engine.record_correction("b1", "premium", "50000", "55000")
        engine.record_correction("b2", "coverage", "CGL", "GL")
        engine.record_correction("b3", "premium", "60000", "65000")
        premium_signals = engine.signals_for_field("premium")
        assert len(premium_signals) == 2

    def test_detect_patterns(self):
        from insureflow.outcomes.active_learning import ActiveLearningEngine

        engine = ActiveLearningEngine()
        for i in range(5):
            engine.record_correction(f"b{i}", "premium", "50000", "55000", confidence=0.7)
        patterns = engine.detect_patterns()
        assert len(patterns) >= 1
        assert patterns[0].field_name == "premium"
        assert patterns[0].sample_count == 5

    def test_calibration_adjustments(self):
        from insureflow.outcomes.active_learning import ActiveLearningEngine

        engine = ActiveLearningEngine()
        for i in range(5):
            engine.record_correction(f"b{i}", "total_assets", "1M", "900K", confidence=0.9)
        adj = engine.calibration_adjustments()
        assert len(adj) >= 1
        assert adj[0].field_name == "total_assets"

    def test_summary(self):
        from insureflow.outcomes.active_learning import ActiveLearningEngine

        engine = ActiveLearningEngine(org_id="test")
        engine.record_correction("b1", "f1", "a", "b")
        engine.record_correction("b2", "f2", "c", "d")
        s = engine.summary()
        assert s["total_corrections"] == 2
        assert s["unique_fields"] == 2
        assert s["org_id"] == "test"


# ── Pillar 1a: Explain ──────────────────────────────────────────────────────


class TestExplain:
    def _make_field(self, name: str, value: str, confidence: float = 0.9) -> MagicMock:
        f = MagicMock()
        f.value = value
        f.confidence = confidence
        f.source = f"doc_{name}.pdf"
        f.page_number = 1
        f.evidence = [f"evidence for {name}"]
        f.source_quote = f"quote for {name}"
        return f

    def test_build_explanation_basic(self):
        from insureflow.trust.explain import build_explanation

        fields = {
            "premium": [self._make_field("premium", "50000")],
            "total_assets": [self._make_field("total_assets", "1000000")],
        }
        tree = build_explanation("b1", fields, decision="accept")
        assert tree.bundle_id == "b1"
        assert tree.decision == "accept"
        assert len(tree.field_explanations) == 2
        assert len(tree.decision_path) >= 2

    def test_field_confidence_captured(self):
        from insureflow.trust.explain import build_explanation

        fields = {"f1": [self._make_field("f1", "v1", confidence=0.45)]}
        tree = build_explanation("b1", fields)
        assert tree.field_explanations[0].confidence == 0.45
        assert tree.field_explanations[0].verification_status == "low_confidence"

    def test_verification_issues_in_fields(self):
        from insureflow.trust.explain import build_explanation

        issue = MagicMock()
        issue.field_name = "premium"
        issue.severity = "error"
        issue.message = "Low confidence"
        report = MagicMock()
        report.issues = [issue]
        fields = {"premium": [self._make_field("premium", "50000")]}
        tree = build_explanation("b1", fields, verification_report=report)
        assert tree.field_explanations[0].issues == ["Low confidence"]
        assert tree.guardian_flags == ["Low confidence"]

    def test_abstention_in_tree(self):
        from insureflow.trust.explain import build_explanation

        verdict = MagicMock()
        verdict.abstain = True
        verdict.reasons = ["insufficient_data"]
        fields = {"f1": [self._make_field("f1", "v1")]}
        tree = build_explanation("b1", fields, abstention_verdict=verdict, decision="abstain")
        assert tree.abstained is True
        assert "insufficient_data" in tree.abstention_reasons

    def test_routing_in_tree(self):
        from insureflow.trust.explain import build_explanation

        routing = MagicMock()
        routing.tier.value = "senior"
        fields = {"f1": [self._make_field("f1", "v1")]}
        tree = build_explanation("b1", fields, routing_decision=routing)
        assert tree.routing_tier == "senior"

    def test_decision_path_steps(self):
        from insureflow.trust.explain import build_explanation

        fields = {f"f{i}": [self._make_field(f"f{i}", f"v{i}")] for i in range(5)}
        tree = build_explanation("b1", fields, decision="refer")
        assert len(tree.decision_path) >= 2
        assert tree.decision_path[-1].outcome == "refer"


# ── Pillar 2c: Review Queue ──────────────────────────────────────────────────


class TestReviewQueue:
    def test_add_and_get(self):
        from insureflow.trust.review_queue import ReviewQueue

        q = ReviewQueue()
        item = q.add("b1", reason="low confidence", confidence_score=0.3)
        assert q.get(item.item_id) is item
        assert q.get("nonexistent") is None

    def test_priority_scoring(self):
        from insureflow.trust.review_queue import PriorityLevel, ReviewQueue

        q = ReviewQueue()
        item = q.add(
            "b1",
            verification_issues=6,
            confidence_score=0.1,
        )
        assert item.priority == PriorityLevel.HOT

    def test_assign(self):
        from insureflow.trust.review_queue import ReviewQueue

        q = ReviewQueue()
        item = q.add("b1")
        q.assign(item.item_id, "uw_smith")
        updated = q.get(item.item_id)
        assert updated is not None
        assert updated.assigned_to == "uw_smith"

    def test_complete_removes(self):
        from insureflow.trust.review_queue import ReviewQueue

        q = ReviewQueue()
        item = q.add("b1")
        removed = q.complete(item.item_id)
        assert removed is item
        assert q.get(item.item_id) is None

    def test_queue_sorted_by_priority(self):
        from insureflow.trust.review_queue import ReviewQueue

        q = ReviewQueue()
        q.add("b1", confidence_score=0.9, verification_issues=0)
        q.add("b2", confidence_score=0.1, verification_issues=6)
        items = q.queue()
        assert items[0].bundle_id == "b2"

    def test_queue_filter_by_priority(self):
        from insureflow.trust.review_queue import PriorityLevel, ReviewQueue

        q = ReviewQueue()
        q.add("b1", confidence_score=0.9, verification_issues=0)
        q.add("b2", confidence_score=0.1, verification_issues=6)
        hot_items = q.queue(priority=PriorityLevel.HOT)
        assert all(i.priority == PriorityLevel.HOT for i in hot_items)

    def test_queue_filter_by_assignment(self):
        from insureflow.trust.review_queue import ReviewQueue

        q = ReviewQueue()
        i1 = q.add("b1")
        q.add("b2")
        q.assign(i1.item_id, "uw_jones")
        jones_items = q.queue(assigned_to="uw_jones")
        assert len(jones_items) == 1
        assert jones_items[0].bundle_id == "b1"

    def test_stats(self):
        from insureflow.trust.review_queue import ReviewQueue

        q = ReviewQueue(org_id="test")
        q.add("b1", confidence_score=0.1, verification_issues=6)
        q.add("b2", confidence_score=0.8)
        stats = q.stats()
        assert stats["total_pending"] == 2
        assert stats["org_id"] == "test"

    def test_age_oldest(self):
        from insureflow.trust.review_queue import ReviewQueue

        q = ReviewQueue()
        q.add("b1")
        age = q.age_oldest()
        assert age >= 0.0

    def test_singleton(self):
        from insureflow.trust.review_queue import get_review_queue

        q1 = get_review_queue("test-org")
        q2 = get_review_queue("test-org")
        assert q1 is q2

    def test_limit(self):
        from insureflow.trust.review_queue import ReviewQueue

        q = ReviewQueue()
        for i in range(20):
            q.add(f"b{i}", confidence_score=0.5)
        items = q.queue(limit=5)
        assert len(items) == 5
