from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_SOURCES_FILE = Path(__file__).parent / "sources.yaml"
_CHANGELOG_DIR = Path(__file__).parent / "changelog"


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


class RegulatoryChange:
    """A detected change in regulatory rules."""

    def __init__(
        self,
        state_code: str,
        line_of_business: str,
        rule_key: str,
        old_value: Any,
        new_value: Any,
        source: str,
        detected_at: str,
        source_url: str = "",
        confidence: str = "unverified",
    ) -> None:
        self.state_code = state_code
        self.line_of_business = line_of_business
        self.rule_key = rule_key
        self.old_value = old_value
        self.new_value = new_value
        self.source = source
        self.detected_at = detected_at
        self.source_url = source_url
        self.confidence = confidence
        self.reviewed = False
        self.applied = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_code": self.state_code,
            "line_of_business": self.line_of_business,
            "rule_key": self.rule_key,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "source": self.source,
            "detected_at": self.detected_at,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "reviewed": self.reviewed,
            "applied": self.applied,
        }


class RegulatoryMonitor:
    """Monitors regulatory sources, detects changes, and tracks changelog."""

    def __init__(self) -> None:
        self._sources: dict[str, Any] = {}
        self._loaded = False
        _ensure_dir(_CHANGELOG_DIR)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            self._sources = _load_yaml(_SOURCES_FILE).get("sources", {})
            self._loaded = True
            active = [k for k, v in self._sources.items() if v.get("enabled", False)]
            logger.info("Loaded %d regulatory sources (%d active)", len(self._sources), len(active))
        except Exception as exc:
            logger.warning("Failed to load regulatory sources: %s", exc)

    def get_sources(self) -> dict[str, Any]:
        self._ensure_loaded()
        return {
            name: {
                "name": src.get("name", name),
                "type": src.get("type", "unknown"),
                "enabled": src.get("enabled", False),
                "poll_interval_hours": src.get("poll_interval_hours", 24),
            }
            for name, src in self._sources.items()
        }

    def get_active_sources(self) -> dict[str, Any]:
        self._ensure_loaded()
        return {name: src for name, src in self._sources.items() if src.get("enabled", False)}

    def compute_freshness(self) -> dict[str, Any]:
        """Compute freshness scores for all rule files."""
        self._ensure_loaded()
        freshness_config = _load_yaml(_SOURCES_FILE).get("freshness", {})
        critical_days = freshness_config.get("critical_days", 90)
        warning_days = freshness_config.get("warning_days", 180)
        stale_days = freshness_config.get("stale_days", 365)
        high_activity = set(freshness_config.get("high_activity_states", []))

        now = datetime.now(timezone.utc)
        results: dict[str, Any] = {}

        for yaml_file in sorted(_DATA_DIR.glob("*.yaml")):
            try:
                data = _load_yaml(yaml_file)
                line_name = yaml_file.stem
                states = data.get("states", {})
                metadata = data.get("metadata", {})
                last_updated_str = metadata.get("last_updated", "unknown")

                state_scores: dict[str, Any] = {}
                stale_count = 0
                warning_count = 0
                critical_count = 0

                for code, state_data in states.items():
                    state_updated = state_data.get("last_updated", last_updated_str)
                    if state_updated == "unknown" or not state_updated:
                        days_old = stale_days + 1
                    else:
                        try:
                            updated_dt = datetime.strptime(state_updated, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                            days_old = (now - updated_dt).days
                        except (ValueError, TypeError):
                            days_old = stale_days + 1

                    is_high_activity = code.upper() in high_activity
                    effective_warning = warning_days // 2 if is_high_activity else warning_days

                    if days_old > stale_days:
                        severity = "stale"
                        stale_count += 1
                    elif days_old > effective_warning:
                        severity = "warning"
                        warning_count += 1
                    elif days_old > critical_days:
                        severity = "critical"
                        critical_count += 1
                    else:
                        severity = "fresh"

                    state_scores[code] = {
                        "days_old": days_old,
                        "severity": severity,
                        "last_updated": state_updated,
                        "high_activity": is_high_activity,
                    }

                total = len(state_scores) or 1
                results[line_name] = {
                    "source": metadata.get("sources", []),
                    "last_updated": last_updated_str,
                    "total_states": total,
                    "fresh": total - stale_count - warning_count - critical_count,
                    "critical": critical_count,
                    "warning": warning_count,
                    "stale": stale_count,
                    "freshness_score": round((total - stale_count - warning_count - critical_count) / total * 100, 1),
                    "states": state_scores,
                }
            except Exception as exc:
                logger.warning("Failed to compute freshness for %s: %s", yaml_file.name, exc)

        return results

    def record_change(self, change: RegulatoryChange) -> str:
        """Record a detected change to the changelog. Returns the changelog file path."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        changelog_file = _CHANGELOG_DIR / f"{date_str}.jsonl"

        entry = change.to_dict()
        entry["changelog_id"] = hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest()[:16]

        with open(changelog_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

        logger.info(
            "Recorded change: %s/%s.%s [%s]",
            change.state_code,
            change.line_of_business,
            change.rule_key,
            change.confidence,
        )
        return str(changelog_file)

    def get_changelog(
        self,
        *,
        state_code: str = "",
        line_of_business: str = "",
        since: str = "",
        reviewed_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Read changelog entries with optional filters."""
        entries: list[dict[str, Any]] = []
        if not _CHANGELOG_DIR.exists():
            return entries

        for changelog_file in sorted(_CHANGELOG_DIR.glob("*.jsonl"), reverse=True):
            if since and changelog_file.stem < since:
                continue
            with open(changelog_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if state_code and entry.get("state_code", "").upper() != state_code.upper():
                        continue
                    if line_of_business and entry.get("line_of_business", "") != line_of_business:
                        continue
                    if reviewed_only and not entry.get("reviewed", False):
                        continue
                    entries.append(entry)
                    if len(entries) >= 500:
                        return entries
        return entries

    def get_unreviewed_changes(self) -> list[dict[str, Any]]:
        """Get all changes that haven't been reviewed yet."""
        return self.get_changelog(reviewed_only=False)

    def mark_reviewed(self, changelog_id: str, approved: bool) -> bool:
        """Mark a changelog entry as reviewed."""
        for changelog_file in sorted(_CHANGELOG_DIR.glob("*.jsonl")):
            lines: list[str] = []
            found = False
            with open(changelog_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        lines.append(line)
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        lines.append(line)
                        continue
                    if entry.get("changelog_id") == changelog_id:
                        entry["reviewed"] = True
                        entry["applied"] = approved
                        entry["reviewed_at"] = datetime.now(timezone.utc).isoformat()
                        lines.append(json.dumps(entry, default=str) + "\n")
                        found = True
                    else:
                        lines.append(line)
            if found:
                with open(changelog_file, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return True
        return False

    def diff_rules(
        self,
        line: str,
        state_code: str,
        old_data: dict[str, Any],
        new_data: dict[str, Any],
        source: str = "",
    ) -> list[RegulatoryChange]:
        """Compare old and new state data, return list of changes."""
        now = datetime.now(timezone.utc).isoformat()
        changes: list[RegulatoryChange] = []
        all_keys = set(list(old_data.keys()) + list(new_data.keys()))

        for key in sorted(all_keys):
            if key == "name":
                continue
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            if old_val != new_val:
                changes.append(
                    RegulatoryChange(
                        state_code=state_code,
                        line_of_business=line,
                        rule_key=key,
                        old_value=old_val,
                        new_value=new_val,
                        source=source,
                        detected_at=now,
                    )
                )
        return changes
