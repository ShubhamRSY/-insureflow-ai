"""Tests for tacit knowledge store, pattern detector, edge case detector, heuristic learner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from insureflow.knowledge.edge_case_detector import EdgeCaseDetector
from insureflow.knowledge.heuristic_learner import HeuristicLearner
from insureflow.knowledge.pattern_detector import PatternDetector
from insureflow.knowledge.tacit_store import KnowledgeType, TacitKnowledgeStore, TacitRule

# ---------------------------------------------------------------------------
# TacitKnowledgeStore
# ---------------------------------------------------------------------------

class TestTacitKnowledgeStore:
    def _make_store(self, tmp: str) -> TacitKnowledgeStore:
        return TacitKnowledgeStore(persist_path=Path(tmp) / "knowledge.json")

    def test_add_and_retrieve_rule(self, tmp_path: Any) -> None:
        store = self._make_store(str(tmp_path))
        rule = TacitRule(
            rule_type=KnowledgeType.HEURISTIC,
            title="Decline restaurants with prior fire claims",
            description="When NAICS=722 and prior fire claims > 0, decline",
            trigger_conditions=["naics=722", "fire_claims>0"],
            action="decline",
            confidence=0.7,
        )
        store.add_rule(rule)
        retrieved = store.get_rule(rule.rule_id)
        assert retrieved is not None
        assert retrieved.title == "Decline restaurants with prior fire claims"
        assert retrieved.action == "decline"

    def test_persistence(self, tmp_path: Any) -> None:
        path = Path(tmp_path) / "knowledge.json"
        store1 = TacitKnowledgeStore(persist_path=path)
        rule = TacitRule(
            rule_type=KnowledgeType.PATTERN,
            title="Test rule",
            description="Test",
            trigger_conditions=["test"],
            action="accept",
        )
        store1.add_rule(rule)

        store2 = TacitKnowledgeStore(persist_path=path)
        store2.load()
        retrieved = store2.get_rule(rule.rule_id)
        assert retrieved is not None
        assert retrieved.title == "Test rule"

    def test_duplicate_rule_increments(self, tmp_path: Any) -> None:
        store = self._make_store(str(tmp_path))
        rule = TacitRule(
            rule_type=KnowledgeType.PATTERN,
            title="Test",
            description="Test",
            trigger_conditions=["test"],
            action="accept",
        )
        store.add_rule(rule)
        store.add_rule(rule)
        retrieved = store.get_rule(rule.rule_id)
        assert retrieved is not None
        assert retrieved.occurrence_count == 2

    def test_confirm_by_human(self, tmp_path: Any) -> None:
        store = self._make_store(str(tmp_path))
        rule = TacitRule(
            rule_type=KnowledgeType.HEURISTIC,
            title="Test",
            description="Test",
            trigger_conditions=[],
            action="decline",
            confidence=0.5,
        )
        store.add_rule(rule)
        store.confirm_by_human(rule.rule_id)
        retrieved = store.get_rule(rule.rule_id)
        assert retrieved is not None
        assert retrieved.confirmed_by_humans == 1
        assert retrieved.confidence > 0.5

    def test_reject_by_human_deactivates(self, tmp_path: Any) -> None:
        store = self._make_store(str(tmp_path))
        rule = TacitRule(
            rule_type=KnowledgeType.HEURISTIC,
            title="Test",
            description="Test",
            trigger_conditions=[],
            action="decline",
            confidence=0.15,
        )
        store.add_rule(rule)
        store.reject_by_human(rule.rule_id)
        retrieved = store.get_rule(rule.rule_id)
        assert retrieved is not None
        assert retrieved.is_active is False

    def test_query_by_type(self, tmp_path: Any) -> None:
        store = self._make_store(str(tmp_path))
        store.add_rule(TacitRule(rule_type=KnowledgeType.PATTERN, title="P1", description="", trigger_conditions=[], action="accept"))
        store.add_rule(TacitRule(rule_type=KnowledgeType.HEURISTIC, title="H1", description="", trigger_conditions=[], action="decline"))
        store.add_rule(TacitRule(rule_type=KnowledgeType.EDGE_CASE, title="E1", description="", trigger_conditions=[], action="refer"))

        patterns = store.query(rule_type=KnowledgeType.PATTERN)
        assert len(patterns) == 1
        assert patterns[0].title == "P1"

    def test_query_by_naics(self, tmp_path: Any) -> None:
        store = self._make_store(str(tmp_path))
        store.add_rule(TacitRule(rule_type=KnowledgeType.PATTERN, title="R1", description="", trigger_conditions=[], action="accept", naics_codes=["722"]))
        store.add_rule(TacitRule(rule_type=KnowledgeType.PATTERN, title="R2", description="", trigger_conditions=[], action="decline", naics_codes=["5417"]))

        results = store.query(naics_codes=["722"])
        assert len(results) == 1
        assert results[0].title == "R1"

    def test_match_submission(self, tmp_path: Any) -> None:
        store = self._make_store(str(tmp_path))
        store.add_rule(TacitRule(
            rule_type=KnowledgeType.HEURISTIC,
            title="Restaurant decline",
            description="Decline restaurants",
            trigger_conditions=["naics=722"],
            action="decline",
            naics_codes=["722"],
            confidence=0.8,
        ))
        submission = {"naics_code": "722", "state": "FL", "tiv": 500000}
        matches = store.match_submission(submission, min_score=0.3)
        assert len(matches) >= 1
        assert matches[0][0].title == "Restaurant decline"

    def test_get_stats(self, tmp_path: Any) -> None:
        store = self._make_store(str(tmp_path))
        store.add_rule(TacitRule(rule_type=KnowledgeType.PATTERN, title="P1", description="", trigger_conditions=[], action="accept"))
        store.add_rule(TacitRule(rule_type=KnowledgeType.HEURISTIC, title="H1", description="", trigger_conditions=[], action="decline"))
        stats = store.get_stats()
        assert stats["total_rules"] == 2
        assert stats["active_rules"] == 2
        assert stats["by_type"]["pattern"] == 1
        assert stats["by_type"]["heuristic"] == 1


# ---------------------------------------------------------------------------
# PatternDetector
# ---------------------------------------------------------------------------

class TestPatternDetector:
    def test_detects_naics_pattern(self, tmp_path: Any) -> None:
        store = TacitKnowledgeStore(persist_path=Path(tmp_path) / "knowledge.json")
        detector = PatternDetector(store=store, min_occurrences=3)

        for i in range(5):
            detector.record_decision(
                bundle_id=f"b-{i}",
                decision="decline",
                risk_score=0.8,
                naics_code="722",
                state="FL",
            )

        patterns = detector.get_patterns(min_confidence=0.0)
        naics_patterns = [p for p in patterns if "722" in p["title"]]
        assert len(naics_patterns) >= 1
        assert naics_patterns[0]["occurrences"] == 5

    def test_detects_state_pattern(self, tmp_path: Any) -> None:
        store = TacitKnowledgeStore(persist_path=Path(tmp_path) / "knowledge.json")
        detector = PatternDetector(store=store, min_occurrences=3)

        for i in range(4):
            detector.record_decision(
                bundle_id=f"b-{i}",
                decision="accept",
                risk_score=0.2,
                state="CA",
            )

        patterns = detector.get_patterns(min_confidence=0.0)
        ca_patterns = [p for p in patterns if "CA" in p["title"]]
        assert len(ca_patterns) >= 1

    def test_no_pattern_below_threshold(self, tmp_path: Any) -> None:
        store = TacitKnowledgeStore(persist_path=Path(tmp_path) / "knowledge.json")
        detector = PatternDetector(store=store, min_occurrences=3)

        detector.record_decision(bundle_id="b-1", decision="decline", risk_score=0.8, naics_code="722")
        detector.record_decision(bundle_id="b-2", decision="decline", risk_score=0.8, naics_code="722")

        patterns = detector.get_patterns(min_confidence=0.0)
        naics_patterns = [p for p in patterns if "722" in p.get("title", "")]
        assert len(naics_patterns) == 0

    def test_broker_pattern(self, tmp_path: Any) -> None:
        store = TacitKnowledgeStore(persist_path=Path(tmp_path) / "knowledge.json")
        detector = PatternDetector(store=store, min_occurrences=3)

        for i in range(4):
            detector.record_decision(
                bundle_id=f"b-{i}",
                decision="refer",
                risk_score=0.6,
                broker_name="ABC Insurance",
            )

        patterns = detector.get_patterns(min_confidence=0.0)
        broker_patterns = [p for p in patterns if "ABC" in p["title"]]
        assert len(broker_patterns) >= 1

    def test_history_tracking(self, tmp_path: Any) -> None:
        store = TacitKnowledgeStore(persist_path=Path(tmp_path) / "knowledge.json")
        detector = PatternDetector(store=store)
        detector.record_decision(bundle_id="b-1", decision="accept", risk_score=0.3)
        history = detector.get_history()
        assert len(history) == 1
        assert history[0]["bundle_id"] == "b-1"


# ---------------------------------------------------------------------------
# EdgeCaseDetector
# ---------------------------------------------------------------------------

class TestEdgeCaseDetector:
    def _make_detector(self, tmp: str) -> EdgeCaseDetector:
        store = TacitKnowledgeStore(persist_path=Path(tmp) / "knowledge.json")
        return EdgeCaseDetector(store=store)

    def test_no_signals_for_normal_data(self, tmp_path: Any) -> None:
        detector = self._make_detector(str(tmp_path))
        for i in range(20):
            detector.learn_from_submission({"tiv": 500000, "total_claims": 2, "state": "FL"})
        signals = detector.detect_edge_cases({"tiv": 520000, "total_claims": 2, "state": "FL"})
        numeric_outliers = [s for s in signals if s.signal_type == "numeric_outlier"]
        assert len(numeric_outliers) == 0

    def test_detects_numeric_outlier(self, tmp_path: Any) -> None:
        detector = self._make_detector(str(tmp_path))
        for i in range(20):
            detector.learn_from_submission({"tiv": 500000 + i * 10000, "total_claims": 2})
        signals = detector.detect_edge_cases({"tiv": 5000000, "total_claims": 2})
        numeric_outliers = [s for s in signals if s.signal_type == "numeric_outlier"]
        assert len(numeric_outliers) >= 1
        assert numeric_outliers[0].field == "tiv"

    def test_detects_rare_combination(self, tmp_path: Any) -> None:
        detector = self._make_detector(str(tmp_path))
        for i in range(25):
            detector.learn_from_submission({
                "construction_type": "Frame",
                "occupancy_type": "Office",
                "state": "FL",
            })
        signals = detector.detect_edge_cases({
            "construction_type": "Masonry",
            "occupancy_type": "Restaurant",
            "state": "FL",
        })
        rare = [s for s in signals if s.signal_type == "rare_combination"]
        assert len(rare) >= 1

    def test_risk_score_anomaly(self, tmp_path: Any) -> None:
        detector = self._make_detector(str(tmp_path))
        for i in range(10):
            detector.learn_from_submission({
                "naics_code": "722",
                "risk_score": 0.3,
            })
        signals = detector.detect_edge_cases({
            "naics_code": "722",
            "risk_score": 0.9,
        })
        risk_anomalies = [s for s in signals if s.signal_type == "risk_score_anomaly"]
        assert len(risk_anomalies) >= 1

    def test_stats(self, tmp_path: Any) -> None:
        detector = self._make_detector(str(tmp_path))
        detector.learn_from_submission({"tiv": 100, "state": "FL"})
        detector.learn_from_submission({"tiv": 200, "state": "CA"})
        stats = detector.get_stats()
        assert stats["submissions_learned"] == 2
        assert stats["tracked_fields"] >= 2


# ---------------------------------------------------------------------------
# HeuristicLearner
# ---------------------------------------------------------------------------

class TestHeuristicLearner:
    def _make_learner(self, tmp: str) -> HeuristicLearner:
        store = TacitKnowledgeStore(persist_path=Path(tmp) / "knowledge.json")
        return HeuristicLearner(store=store, min_occurrences=3, min_confidence=0.4)

    def test_override_pattern(self, tmp_path: Any) -> None:
        learner = self._make_learner(str(tmp_path))
        all_proposed: list[Any] = []
        for i in range(4):
            proposed = learner.ingest_decision(
                bundle_id=f"b-{i}",
                decision="accept",
                override_reason="Low loss ratio offsets concerns",
                risk_score=0.7,
            )
            all_proposed.extend(proposed)
        override_h = [h for h in all_proposed if "override" in h.title.lower() or "loss ratio" in h.description.lower()]
        assert len(override_h) >= 1

    def test_broker_pattern(self, tmp_path: Any) -> None:
        learner = self._make_learner(str(tmp_path))
        all_proposed: list[Any] = []
        for i in range(4):
            proposed = learner.ingest_decision(
                bundle_id=f"b-{i}",
                decision="decline",
                broker_name="Risky Brokers Inc",
                risk_score=0.8,
            )
            all_proposed.extend(proposed)
        broker_h = [h for h in all_proposed if "Risky Brokers" in h.title]
        assert len(broker_h) >= 1
        assert broker_h[0].action == "decline"

    def test_finding_pattern(self, tmp_path: Any) -> None:
        learner = self._make_learner(str(tmp_path))
        all_proposed: list[Any] = []
        for i in range(4):
            proposed = learner.ingest_decision(
                bundle_id=f"b-{i}",
                decision="decline",
                finding_categories=["fraud", "misrepresentation"],
                risk_score=0.9,
            )
            all_proposed.extend(proposed)
        fraud_h = [h for h in all_proposed if "fraud" in h.title.lower() or "misrepresentation" in h.title.lower()]
        assert len(fraud_h) >= 1

    def test_no_pattern_below_threshold(self, tmp_path: Any) -> None:
        learner = self._make_learner(str(tmp_path))
        learner.ingest_decision(bundle_id="b-1", decision="accept", broker_name="ABC")
        learner.ingest_decision(bundle_id="b-2", decision="accept", broker_name="ABC")
        heuristics = learner.get_proposed()
        broker_h = [h for h in heuristics if "ABC" in h["title"]]
        assert len(broker_h) == 0

    def test_propose_to_knowledge_base(self, tmp_path: Any) -> None:
        learner = self._make_learner(str(tmp_path))
        all_proposed: list[Any] = []
        for i in range(5):
            proposed = learner.ingest_decision(
                bundle_id=f"b-{i}",
                decision="decline",
                broker_name="Bad Broker",
                risk_score=0.9,
            )
            all_proposed.extend(proposed)
        assert len(all_proposed) >= 1
        accepted = learner.propose_to_knowledge_base(all_proposed)
        assert len(accepted) >= 1
        assert accepted[0].rule_type == KnowledgeType.HEURISTIC

    def test_stats(self, tmp_path: Any) -> None:
        learner = self._make_learner(str(tmp_path))
        learner.ingest_decision(bundle_id="b-1", decision="accept")
        learner.ingest_decision(bundle_id="b-2", decision="decline")
        stats = learner.get_stats()
        assert stats["total_decisions_ingested"] == 2
