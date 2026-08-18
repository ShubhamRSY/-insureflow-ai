from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from insureflow.regulatory.monitor import RegulatoryMonitor

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_REVIEW_DIR = Path(__file__).parent / "review_queue"


class ReviewDecision:
    """A human review decision on a detected change."""

    def __init__(self, changelog_id: str, reviewer: str, approved: bool, notes: str = "") -> None:
        self.changelog_id = changelog_id
        self.reviewer = reviewer
        self.approved = approved
        self.notes = notes
        self.decided_at: str = datetime.now(timezone.utc).isoformat()


class RegulatoryReviewService:
    """Manages the human review workflow for regulatory changes."""

    def __init__(self) -> None:
        self._monitor = RegulatoryMonitor()
        _REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    def get_pending_reviews(self) -> list[dict[str, Any]]:
        """Get all changes awaiting human review."""
        unreviewed = self._monitor.get_unreviewed_changes()
        pending: list[dict[str, Any]] = []
        for entry in unreviewed:
            if not entry.get("reviewed", False):
                pending.append(entry)
        return pending

    def get_review_stats(self) -> dict[str, Any]:
        """Get review queue statistics."""
        all_entries = self._monitor.get_changelog()
        pending = [e for e in all_entries if not e.get("reviewed", False)]
        approved = [e for e in all_entries if e.get("reviewed") and e.get("applied")]
        rejected = [e for e in all_entries if e.get("reviewed") and not e.get("applied")]

        by_line: dict[str, int] = {}
        by_state: dict[str, int] = {}
        for entry in pending:
            line = entry.get("line_of_business", "unknown")
            state = entry.get("state_code", "unknown")
            by_line[line] = by_line.get(line, 0) + 1
            by_state[state] = by_state.get(state, 0) + 1

        return {
            "total": len(all_entries),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "pending_by_line": by_line,
            "pending_by_state": by_state,
        }

    def submit_decision(self, decision: ReviewDecision) -> dict[str, Any]:
        """Record a reviewer's decision on a change."""
        success = self._monitor.mark_reviewed(decision.changelog_id, decision.approved)
        if not success:
            return {"status": "error", "message": "Changelog entry not found"}

        decision_file = _REVIEW_DIR / f"{decision.changelog_id}.json"
        decision_record: dict[str, Any] = {
            "changelog_id": decision.changelog_id,
            "reviewer": decision.reviewer,
            "approved": decision.approved,
            "notes": decision.notes,
            "decided_at": decision.decided_at,
        }
        with open(decision_file, "w", encoding="utf-8") as f:
            json.dump(decision_record, f, indent=2)

        if decision.approved:
            applied = self.apply_approved_change(decision.changelog_id)
            return {
                "status": "approved",
                "applied": applied,
                "changelog_id": decision.changelog_id,
            }

        return {
            "status": "rejected",
            "changelog_id": decision.changelog_id,
        }

    def apply_approved_change(self, changelog_id: str) -> bool:
        """Apply an approved change to the actual YAML rule file."""
        entry = self._find_changelog_entry(changelog_id)
        if entry is None:
            logger.warning("Changelog entry %s not found for apply", changelog_id)
            return False

        state_code = entry.get("state_code", "")
        line_of_business = entry.get("line_of_business", "")
        rule_key = entry.get("rule_key", "")
        new_value = entry.get("new_value", "")

        if not state_code or not line_of_business or not rule_key:
            logger.warning("Incomplete changelog entry %s: missing state/line/key", changelog_id)
            return False

        yaml_path = _DATA_DIR / f"{line_of_business}.yaml"
        if not yaml_path.exists():
            logger.warning("YAML file not found: %s", yaml_path)
            return False

        try:
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as exc:
            logger.error("Failed to load YAML %s: %s", yaml_path, exc)
            return False

        states = data.get("states", {})
        if state_code not in states:
            logger.warning("State %s not found in %s", state_code, yaml_path)
            return False

        states[state_code][rule_key] = new_value
        states[state_code]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        metadata = data.get("metadata", {})
        metadata["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        data["metadata"] = metadata

        try:
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    data,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        except Exception as exc:
            logger.error("Failed to write YAML %s: %s", yaml_path, exc)
            return False

        logger.info(
            "Applied change %s: %s/%s.%s = %s",
            changelog_id,
            state_code,
            line_of_business,
            rule_key,
            new_value,
        )
        return True

    def _find_changelog_entry(self, changelog_id: str) -> dict[str, Any] | None:
        """Find a specific changelog entry by its ID."""
        entries: list[dict[str, Any]] = self._monitor.get_changelog()
        for entry in entries:
            if entry.get("changelog_id") == changelog_id:
                return entry
        return None

    def get_review_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get history of all review decisions."""
        history: list[dict[str, Any]] = []
        for decision_file in sorted(_REVIEW_DIR.glob("*.json"), reverse=True):
            if len(history) >= limit:
                break
            try:
                with open(decision_file, encoding="utf-8") as f:
                    record = json.load(f)
                history.append(record)
            except Exception as exc:
                logger.warning("Failed to read decision file %s: %s", decision_file, exc)
        return history
