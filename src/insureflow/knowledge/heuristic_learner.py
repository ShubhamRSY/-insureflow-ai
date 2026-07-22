"""Heuristic learner — mines audit trails for repeated decision patterns and proposes rules."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from insureflow.knowledge.tacit_store import KnowledgeType, TacitKnowledgeStore, TacitRule, get_tacit_store

logger = logging.getLogger(__name__)


class ProposedHeuristic:
    """A heuristic rule proposed by the learner from audit trail patterns."""

    __slots__ = ("heuristic_id", "title", "description", "trigger", "action", "confidence", "evidence_count", "source_bundles", "rejected")

    def __init__(
        self,
        heuristic_id: str,
        title: str,
        description: str,
        trigger: str,
        action: str,
        confidence: float,
        evidence_count: int,
        source_bundles: Optional[list[str]] = None,
    ) -> None:
        self.heuristic_id = heuristic_id
        self.title = title
        self.description = description
        self.trigger = trigger
        self.action = action
        self.confidence = confidence
        self.evidence_count = evidence_count
        self.source_bundles = source_bundles or []
        self.rejected = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "heuristic_id": self.heuristic_id,
            "title": self.title,
            "description": self.description,
            "trigger": self.trigger,
            "action": self.action,
            "confidence": round(self.confidence, 3),
            "evidence_count": self.evidence_count,
            "source_bundles": self.source_bundles[-5:],
            "rejected": self.rejected,
        }


class HeuristicLearner:
    """Mines audit trails for repeated decision patterns and proposes new heuristics."""

    def __init__(
        self,
        store: Optional[TacitKnowledgeStore] = None,
        min_occurrences: int = 3,
        min_confidence: float = 0.4,
    ) -> None:
        self.store = store or get_tacit_store()
        self.min_occurrences = min_occurrences
        self.min_confidence = min_confidence
        self._decisions: list[dict[str, Any]] = []

    def ingest_decision(
        self,
        bundle_id: str,
        decision: str,
        signed_by: str = "",
        override_reason: str = "",
        risk_score: float = 0.5,
        finding_categories: Optional[list[str]] = None,
        conditions: Optional[list[str]] = None,
        naics_code: str = "",
        state: str = "",
        tiv: float = 0.0,
        total_claims: int = 0,
        broker_name: str = "",
        coverage_types: Optional[list[str]] = None,
        construction_type: str = "",
        occupancy_type: str = "",
    ) -> list[ProposedHeuristic]:
        entry = {
            "bundle_id": bundle_id,
            "decision": decision,
            "signed_by": signed_by,
            "override_reason": override_reason,
            "risk_score": risk_score,
            "finding_categories": finding_categories or [],
            "conditions": conditions or [],
            "naics_code": naics_code,
            "state": state,
            "tiv": tiv,
            "total_claims": total_claims,
            "broker_name": broker_name,
            "coverage_types": coverage_types or [],
            "construction_type": construction_type,
            "occupancy_type": occupancy_type,
            "ingested_at": datetime.now(tz=timezone.utc),
        }
        self._decisions.append(entry)
        return self._mine_patterns(entry)

    def _mine_patterns(self, new_decision: dict[str, Any]) -> list[ProposedHeuristic]:
        proposed: list[ProposedHeuristic] = []
        proposed.extend(self._mine_override_patterns(new_decision))
        proposed.extend(self._mine_condition_patterns(new_decision))
        proposed.extend(self._mine_broker_patterns(new_decision))
        proposed.extend(self._mine_finding_patterns(new_decision))
        return proposed

    def _mine_override_patterns(self, new_decision: dict[str, Any]) -> list[ProposedHeuristic]:
        proposed: list[ProposedHeuristic] = []
        reason = new_decision.get("override_reason", "")
        if not reason:
            return proposed

        same_reason = [
            d for d in self._decisions
            if d.get("override_reason", "") == reason
        ]

        if len(same_reason) >= self.min_occurrences:
            decisions = [d["decision"] for d in same_reason]
            most_common = max(set(decisions), key=decisions.count)
            confidence = decisions.count(most_common) / len(decisions)

            if confidence >= self.min_confidence:
                heuristic_id = f"heuristic-override-{hashlib.sha256(reason.encode()).hexdigest()[:10]}"
                existing = self.store.get_rule(heuristic_id)
                if existing is None:
                    proposed.append(ProposedHeuristic(
                        heuristic_id=heuristic_id,
                        title=f"Override pattern: {reason[:50]}",
                        description=f"When UW overrides with reason '{reason}', they tend to {most_common} ({len(same_reason)} occurrences)",
                        trigger=f"override_reason={reason}",
                        action=most_common,
                        confidence=confidence,
                        evidence_count=len(same_reason),
                        source_bundles=[d["bundle_id"] for d in same_reason[-5:]],
                    ))

        return proposed

    def _mine_condition_patterns(self, new_decision: dict[str, Any]) -> list[ProposedHeuristic]:
        proposed: list[ProposedHeuristic] = []
        conditions = new_decision.get("conditions", [])
        if not conditions:
            return proposed

        for condition in conditions:
            same_condition = [
                d for d in self._decisions
                if condition in d.get("conditions", [])
            ]

            if len(same_condition) >= self.min_occurrences:
                decisions = [d["decision"] for d in same_condition]
                most_common = max(set(decisions), key=decisions.count)
                confidence = decisions.count(most_common) / len(same_condition)

                if confidence >= self.min_confidence:
                    heuristic_id = f"heuristic-condition-{hashlib.sha256(condition.encode()).hexdigest()[:10]}"
                    existing = self.store.get_rule(heuristic_id)
                    if existing is None:
                        proposed.append(ProposedHeuristic(
                            heuristic_id=heuristic_id,
                            title=f"Condition pattern: {condition[:50]}",
                            description=f"When condition '{condition}' is applied, UWs tend to {most_common} ({len(same_condition)} occurrences)",
                            trigger=f"condition={condition}",
                            action=most_common,
                            confidence=confidence,
                            evidence_count=len(same_condition),
                            source_bundles=[d["bundle_id"] for d in same_condition[-5:]],
                        ))

        return proposed

    def _mine_broker_patterns(self, new_decision: dict[str, Any]) -> list[ProposedHeuristic]:
        proposed: list[ProposedHeuristic] = []
        broker = new_decision.get("broker_name", "")
        if not broker:
            return proposed

        same_broker = [
            d for d in self._decisions
            if d.get("broker_name", "") == broker
        ]

        if len(same_broker) >= self.min_occurrences:
            decisions = [d["decision"] for d in same_broker]
            most_common = max(set(decisions), key=decisions.count)
            confidence = decisions.count(most_common) / len(same_broker)

            if confidence >= self.min_confidence:
                heuristic_id = f"heuristic-broker-{hashlib.sha256(broker.encode()).hexdigest()[:10]}"
                existing = self.store.get_rule(heuristic_id)
                if existing is None:
                    proposed.append(ProposedHeuristic(
                        heuristic_id=heuristic_id,
                        title=f"Broker pattern: {broker[:50]}",
                        description=f"Submissions from broker '{broker}' are consistently {most_common} ({len(same_broker)} occurrences)",
                        trigger=f"broker={broker}",
                        action=most_common,
                        confidence=confidence,
                        evidence_count=len(same_broker),
                        source_bundles=[d["bundle_id"] for d in same_broker[-5:]],
                    ))

        return proposed

    def _mine_finding_patterns(self, new_decision: dict[str, Any]) -> list[ProposedHeuristic]:
        proposed: list[ProposedHeuristic] = []
        finding_cats = new_decision.get("finding_categories", [])
        if not finding_cats:
            return proposed

        for cat in finding_cats:
            same_cat = [
                d for d in self._decisions
                if cat in d.get("finding_categories", [])
            ]

            if len(same_cat) >= self.min_occurrences:
                decisions = [d["decision"] for d in same_cat]
                most_common = max(set(decisions), key=decisions.count)
                confidence = decisions.count(most_common) / len(same_cat)

                if confidence >= self.min_confidence:
                    heuristic_id = f"heuristic-finding-{hashlib.sha256(cat.encode()).hexdigest()[:10]}"
                    existing = self.store.get_rule(heuristic_id)
                    if existing is None:
                        proposed.append(ProposedHeuristic(
                            heuristic_id=heuristic_id,
                            title=f"Finding pattern: {cat[:50]}",
                            description=f"When finding category '{cat}' appears, UWs tend to {most_common} ({len(same_cat)} occurrences)",
                            trigger=f"finding_category={cat}",
                            action=most_common,
                            confidence=confidence,
                            evidence_count=len(same_cat),
                            source_bundles=[d["bundle_id"] for d in same_cat[-5:]],
                        ))

        return proposed

    def propose_to_knowledge_base(self, heuristics: list[ProposedHeuristic]) -> list[TacitRule]:
        accepted: list[TacitRule] = []
        for h in heuristics:
            if h.rejected or h.confidence < self.min_confidence:
                continue

            rule = TacitRule(
                rule_id=h.heuristic_id,
                rule_type=KnowledgeType.HEURISTIC,
                title=h.title,
                description=h.description,
                trigger_conditions=[h.trigger],
                action=h.action,
                rationale=f"Mined from {h.evidence_count} audit decisions",
                confidence=h.confidence,
                source_bundles=h.source_bundles,
                tags=["heuristic", "auto_mined"],
                occurrence_count=h.evidence_count,
            )
            self.store.add_rule(rule)
            accepted.append(rule)
            logger.info("Proposed heuristic accepted: %s (confidence=%.2f)", h.title, h.confidence)

        return accepted

    def get_proposed(self, limit: int = 50) -> list[dict[str, Any]]:
        rules = self.store.query(rule_type=KnowledgeType.HEURISTIC)
        return [
            {
                "heuristic_id": r.rule_id,
                "title": r.title,
                "description": r.description,
                "trigger": r.trigger_conditions[0] if r.trigger_conditions else "",
                "action": r.action,
                "confidence": r.confidence,
                "occurrences": r.occurrence_count,
                "human_confirmed": r.confirmed_by_humans,
                "human_rejected": r.rejected_by_humans,
                "is_active": r.is_active,
            }
            for r in rules[:limit]
        ]

    def get_stats(self) -> dict[str, Any]:
        rules = self.store.query(rule_type=KnowledgeType.HEURISTIC)
        active = [r for r in rules if r.is_active]
        return {
            "total_decisions_ingested": len(self._decisions),
            "total_heuristics": len(rules),
            "active_heuristics": len(active),
            "avg_confidence": round(sum(r.confidence for r in active) / max(len(active), 1), 3),
        }
