"""Pattern detector — learns recurring UW decisions into queryable patterns."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from insureflow.knowledge.tacit_store import KnowledgeType, TacitKnowledgeStore, TacitRule, get_tacit_store

logger = logging.getLogger(__name__)


class DecisionPattern:
    """A recurring pattern extracted from multiple UW decisions."""

    __slots__ = (
        "pattern_id", "description", "decision", "conditions",
        "occurrence_count", "avg_risk_score", "sample_bundles",
        "confidence", "created_at",
    )

    def __init__(
        self,
        pattern_id: str,
        description: str,
        decision: str,
        conditions: dict[str, Any],
        occurrence_count: int = 1,
        avg_risk_score: float = 0.0,
        sample_bundles: Optional[list[str]] = None,
    ) -> None:
        self.pattern_id = pattern_id
        self.description = description
        self.decision = decision
        self.conditions = conditions
        self.occurrence_count = occurrence_count
        self.avg_risk_score = avg_risk_score
        self.sample_bundles = sample_bundles or []
        self.confidence = min(1.0, occurrence_count / 5.0)
        self.created_at = datetime.now(tz=timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "description": self.description,
            "decision": self.decision,
            "conditions": self.conditions,
            "occurrence_count": self.occurrence_count,
            "avg_risk_score": round(self.avg_risk_score, 3),
            "confidence": round(self.confidence, 3),
            "sample_bundles": self.sample_bundles[-5:],
            "created_at": self.created_at.isoformat(),
        }


class PatternDetector:
    """Detects recurring patterns from UW decision history."""

    def __init__(self, store: Optional[TacitKnowledgeStore] = None, min_occurrences: int = 3) -> None:
        self.store = store or get_tacit_store()
        self.min_occurrences = min_occurrences
        self._decision_history: list[dict[str, Any]] = []

    def record_decision(
        self,
        bundle_id: str,
        decision: str,
        risk_score: float,
        naics_code: str = "",
        coverage_types: Optional[list[str]] = None,
        state: str = "",
        tiv: float = 0.0,
        total_claims: int = 0,
        construction_type: str = "",
        occupancy_type: str = "",
        protection_class: int = 0,
        broker_name: str = "",
        finding_categories: Optional[list[str]] = None,
    ) -> None:
        entry = {
            "bundle_id": bundle_id,
            "decision": decision,
            "risk_score": risk_score,
            "naics_code": naics_code,
            "coverage_types": coverage_types or [],
            "state": state,
            "tiv": tiv,
            "total_claims": total_claims,
            "construction_type": construction_type,
            "occupancy_type": occupancy_type,
            "protection_class": protection_class,
            "broker_name": broker_name,
            "finding_categories": finding_categories or [],
            "recorded_at": datetime.now(tz=timezone.utc),
        }
        self._decision_history.append(entry)
        self._check_for_patterns(entry)

    def _make_condition_key(self, entry: dict[str, Any], dimension: str) -> str:
        if dimension == "naics":
            return entry.get("naics_code", "")
        elif dimension == "state":
            return entry.get("state", "")
        elif dimension == "construction":
            return entry.get("construction_type", "")
        elif dimension == "occupancy":
            return entry.get("occupancy_type", "")
        elif dimension == "broker":
            return entry.get("broker_name", "")
        elif dimension == "coverage_combo":
            return "|".join(sorted(entry.get("coverage_types", [])))
        elif dimension == "decision_risk_band":
            score = entry.get("risk_score", 0.5)
            band = "low" if score < 0.3 else "medium" if score < 0.6 else "high" if score < 0.8 else "critical"
            return f"{entry.get('decision', 'unknown')}_{band}"
        return ""

    def _check_for_patterns(self, new_entry: dict[str, Any]) -> None:
        dimensions = ["naics", "state", "construction", "occupancy", "broker", "coverage_combo", "decision_risk_band"]

        for dimension in dimensions:
            key = self._make_condition_key(new_entry, dimension)
            if not key:
                continue

            matching = [
                e for e in self._decision_history
                if self._make_condition_key(e, dimension) == key
                and e["decision"] == new_entry["decision"]
            ]

            if len(matching) >= self.min_occurrences:
                pattern_id = hashlib.sha256(
                    f"{dimension}:{key}:{new_entry['decision']}".encode()
                ).hexdigest()[:16]

                existing = self.store.get_rule(f"pattern-{pattern_id}")
                if existing is not None:
                    existing.occurrence_count = len(matching)
                    existing.confidence = min(1.0, len(matching) / 5.0)
                    from insureflow.knowledge.tacit_store import get_tacit_store
                    get_tacit_store()._persist()
                    continue

                bundles = [e["bundle_id"] for e in matching[-5:]]

                description = self._build_description(dimension, key, new_entry["decision"], len(matching))

                rule = TacitRule(
                    rule_id=f"pattern-{pattern_id}",
                    rule_type=KnowledgeType.PATTERN,
                    title=f"Pattern: {new_entry['decision']} when {dimension}={key}",
                    description=description,
                    trigger_conditions=[f"{dimension}={key}"],
                    action=new_entry["decision"],
                    rationale=f"Observed {len(matching)} times across {len(set(e['bundle_id'] for e in matching))} submissions",
                    confidence=min(1.0, len(matching) / 5.0),
                    source_bundles=bundles,
                    tags=[f"pattern:{dimension}"],
                    naics_codes=[key] if dimension == "naics" else [],
                    states=[key] if dimension == "state" else [],
                    occurrence_count=len(matching),
                )
                self.store.add_rule(rule)
                logger.info("Discovered pattern: %s (occurrences=%d)", rule.title, len(matching))

    def _build_description(self, dimension: str, key: str, decision: str, count: int) -> str:
        dimension_labels = {
            "naics": "NAICS code",
            "state": "state",
            "construction": "construction type",
            "occupancy": "occupancy type",
            "broker": "broker",
            "coverage_combo": "coverage combination",
            "decision_risk_band": "risk band",
        }
        label = dimension_labels.get(dimension, dimension)
        return f"UWs consistently {decision} submissions when {label}={key} ({count} occurrences)"

    def get_patterns(self, min_confidence: float = 0.3) -> list[dict[str, Any]]:
        rules = self.store.query(rule_type=KnowledgeType.PATTERN, min_confidence=min_confidence)
        return [
            {
                "pattern_id": r.rule_id,
                "title": r.title,
                "description": r.description,
                "decision": r.action,
                "confidence": r.confidence,
                "occurrences": r.occurrence_count,
                "human_confirmed": r.confirmed_by_humans,
            }
            for r in rules
        ]

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return [
            {k: v for k, v in e.items() if k != "recorded_at"}
            for e in self._decision_history[-limit:]
        ]
