"""Tacit knowledge store — captures and queries unwritten underwriting rules and patterns."""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KnowledgeType(str, Enum):
    PATTERN = "pattern"
    HEURISTIC = "heuristic"
    EDGE_CASE = "edge_case"
    WARNING = "warning"
    EXCEPTION = "exception"


class TacitRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: f"rule-{uuid.uuid4().hex[:12]}")
    rule_type: KnowledgeType
    title: str
    description: str
    trigger_conditions: list[str] = Field(default_factory=list)
    action: str = ""
    rationale: str = ""
    confidence: float = 0.5
    source_bundles: list[str] = Field(default_factory=list)
    source_agents: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    naics_codes: list[str] = Field(default_factory=list)
    coverage_types: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    min_tiv: Optional[float] = None
    max_tiv: Optional[float] = None
    min_claims: Optional[int] = None
    occurrence_count: int = 1
    confirmed_by_humans: int = 0
    rejected_by_humans: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    is_active: bool = True

    def matches_submission(self, submission: dict[str, Any]) -> float:
        """Return a match score (0.0-1.0) against a submission's risk profile."""
        score = 0.0
        checks = 0

        if self.naics_codes:
            checks += 1
            sub_naics = submission.get("naics_code", "")
            if sub_naics in self.naics_codes:
                score += 1.0

        if self.coverage_types:
            checks += 1
            sub_coverages = set(submission.get("coverage_types", []))
            if sub_coverages & set(self.coverage_types):
                score += 1.0

        if self.states:
            checks += 1
            sub_state = submission.get("state", "")
            if sub_state in self.states:
                score += 1.0

        if self.min_tiv is not None:
            checks += 1
            if submission.get("tiv", 0) >= self.min_tiv:
                score += 1.0

        if self.max_tiv is not None:
            checks += 1
            if submission.get("tiv", 0) <= self.max_tiv:
                score += 1.0

        if self.min_claims is not None:
            checks += 1
            if submission.get("total_claims", 0) >= self.min_claims:
                score += 1.0

        if self.trigger_conditions:
            for condition in self.trigger_conditions:
                checks += 1
                if condition.lower() in json.dumps(submission).lower():
                    score += 1.0

        return score / max(checks, 1)


class TacitKnowledgeStore:
    """Persistent, thread-safe store of tacit underwriting knowledge."""

    def __init__(self, persist_path: Optional[Path] = None) -> None:
        self._lock = threading.Lock()
        self._rules: dict[str, TacitRule] = {}
        self._persist_path = persist_path or Path(os.getenv("TACIT_KNOWLEDGE_PATH", "./audit_logs/tacit_knowledge.json"))

    def add_rule(self, rule: TacitRule) -> TacitRule:
        with self._lock:
            if rule.rule_id in self._rules:
                existing = self._rules[rule.rule_id]
                existing.occurrence_count += 1
                existing.last_seen_at = datetime.now(tz=timezone.utc)
                existing.confidence = min(1.0, existing.confidence + 0.05)
                self._persist()
                return existing
            self._rules[rule.rule_id] = rule
            self._persist()
            return rule

    def get_rule(self, rule_id: str) -> Optional[TacitRule]:
        with self._lock:
            return self._rules.get(rule_id)

    _ALLOWED_UPDATE_ATTRS = frozenset({
        "title", "description", "trigger_conditions", "action", "rationale",
        "tags", "naics_codes", "coverage_types", "states",
        "min_tiv", "max_tiv", "min_claims",
    })

    def update_rule(self, rule_id: str, **kwargs: Any) -> Optional[TacitRule]:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return None
            for key, value in kwargs.items():
                if key in self._ALLOWED_UPDATE_ATTRS and hasattr(rule, key):
                    setattr(rule, key, value)
            rule.last_seen_at = datetime.now(tz=timezone.utc)
            self._persist()
            return rule

    def confirm_by_human(self, rule_id: str) -> Optional[TacitRule]:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return None
            rule.confirmed_by_humans += 1
            rule.confidence = min(1.0, rule.confidence + 0.15)
            rule.last_seen_at = datetime.now(tz=timezone.utc)
            self._persist()
            return rule

    def reject_by_human(self, rule_id: str) -> Optional[TacitRule]:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return None
            rule.rejected_by_humans += 1
            rule.confidence = max(0.0, rule.confidence - 0.2)
            if rule.confidence <= 0.0:
                rule.is_active = False
            rule.last_seen_at = datetime.now(tz=timezone.utc)
            self._persist()
            return rule

    def query(
        self,
        rule_type: Optional[KnowledgeType] = None,
        tags: Optional[list[str]] = None,
        naics_codes: Optional[list[str]] = None,
        coverage_types: Optional[list[str]] = None,
        states: Optional[list[str]] = None,
        min_confidence: float = 0.0,
        active_only: bool = True,
    ) -> list[TacitRule]:
        with self._lock:
            results = list(self._rules.values())

        if active_only:
            results = [r for r in results if r.is_active]
        if rule_type is not None:
            results = [r for r in results if r.rule_type == rule_type]
        if tags is not None:
            tag_set = set(tags)
            results = [r for r in results if tag_set & set(r.tags)]
        if naics_codes is not None:
            naics_set = set(naics_codes)
            results = [r for r in results if naics_set & set(r.naics_codes)]
        if coverage_types is not None:
            cov_set = set(coverage_types)
            results = [r for r in results if cov_set & set(r.coverage_types)]
        if states is not None:
            state_set = set(states)
            results = [r for r in results if state_set & set(r.states)]
        if min_confidence > 0:
            results = [r for r in results if r.confidence >= min_confidence]

        return sorted(results, key=lambda r: (-r.confidence, -r.occurrence_count))

    def match_submission(self, submission: dict[str, Any], min_score: float = 0.3) -> list[tuple[TacitRule, float]]:
        matches: list[tuple[TacitRule, float]] = []
        with self._lock:
            rules = [r for r in self._rules.values() if r.is_active]

        for rule in rules:
            score = rule.matches_submission(submission)
            if score >= min_score:
                matches.append((rule, score))

        return sorted(matches, key=lambda x: (-x[1], -x[0].confidence))

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            rules = list(self._rules.values())
        active = [r for r in rules if r.is_active]
        by_type: dict[str, int] = {}
        for r in active:
            by_type[r.rule_type.value] = by_type.get(r.rule_type.value, 0) + 1
        return {
            "total_rules": len(rules),
            "active_rules": len(active),
            "by_type": by_type,
            "avg_confidence": round(sum(r.confidence for r in active) / max(len(active), 1), 3),
            "total_human_confirmations": sum(r.confirmed_by_humans for r in rules),
            "total_human_rejections": sum(r.rejected_by_humans for r in rules),
        }

    def _persist(self) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {rid: rule.model_dump() for rid, rule in self._rules.items()}
            self._persist_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except OSError:
            logger.debug("Failed to persist tacit knowledge", exc_info=True)

    def load(self) -> None:
        if not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            with self._lock:
                for rid, rule_data in data.items():
                    self._rules[rid] = TacitRule(**rule_data)
        except (json.JSONDecodeError, OSError):
            logger.debug("Failed to load tacit knowledge", exc_info=True)


_store: Optional[TacitKnowledgeStore] = None


def get_tacit_store() -> TacitKnowledgeStore:
    global _store
    if _store is None:
        _store = TacitKnowledgeStore()
        _store.load()
    return _store
