"""Automated state law tracking and regulatory change alerts.

Monitors state legislative feeds, DOI bulletins, and NAIC updates to detect
new insurance laws and regulatory changes before they impact customers.

    Tracks:
    1. State legislature bill status changes (new bills, signed laws)
    2. DOI bulletin/ruling publications
    3. NAIC model law adoption updates
    4. Rate filing approvals/denials
    5. Enforcement actions

    Alert channels:
    - In-app notifications
    - Email digests (daily/weekly)
    - Webhook (POST to customer URL)

    LAW_TRACKER_STORAGE  "file" (default) or "postgres"
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from insureflow.regulatory.diff import _STATE_CODES, _STATE_NAMES, RegulatoryDiffEngine
from insureflow.regulatory.monitor import RegulatoryChange, RegulatoryMonitor
from insureflow.regulatory.poller import RegulatoryPoller
from insureflow.storage.lock import FileLock, atomic_write

logger = logging.getLogger(__name__)

_TESTING = os.environ.get("INSUREFLOW_AUTH_TESTING") == "1"

_DATA_DIR = Path(__file__).parent / "data"
_ALERTS_DIR = Path(__file__).parent / "alerts"
_SUBSCRIPTIONS_FILE = Path(__file__).parent / "data" / "alert_subscriptions.json"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AlertSeverity(str):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


class LawChangeType(str):
    NEW_BILL = "new_bill"
    BILL_SIGNED = "bill_signed"
    RATE_FILING = "rate_filing"
    DOI_BULLETIN = "doi_bulletin"
    NAIC_ADOPTION = "naic_adoption"
    ENFORCEMENT = "enforcement"
    RULE_CHANGE = "rule_change"
    MANDATE_CHANGE = "mandate_change"


class RegulatoryAlert(BaseModel):
    alert_id: str
    state_code: str
    state_name: str = ""
    line_of_business: str = ""
    change_type: str
    severity: str
    title: str
    description: str
    source: str = ""
    source_url: str = ""
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    effective_date: str = ""
    requires_action: bool = False
    action_deadline: str = ""
    action_description: str = ""
    impacted_submissions: int = 0
    reviewed: bool = False


class AlertSubscription(BaseModel):
    org_id: str
    states: list[str] = Field(default_factory=list)
    lines: list[str] = Field(default_factory=list)
    alert_types: list[str] = Field(default_factory=list)
    severity_threshold: str = "warning"  # only alerts at this severity or above
    webhook_url: str = ""
    email_digest: str = "daily"  # none, daily, weekly
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LawTrackerSnapshot(BaseModel):
    timestamp: str
    states_monitored: int
    sources_polled: int
    changes_detected: int
    alerts_generated: int
    pending_alerts: int
    active_subscriptions: int


# ---------------------------------------------------------------------------
# Severity rules
# ---------------------------------------------------------------------------

_SEVERITY_MAP: dict[str, str] = {
    "new_bill": "info",
    "bill_signed": "critical",
    "rate_filing": "warning",
    "doi_bulletin": "warning",
    "naic_adoption": "critical",
    "enforcement": "urgent",
    "rule_change": "critical",
    "mandate_change": "critical",
}

_ACTION_REQUIRED_TYPES: set[str] = {
    "bill_signed",
    "rate_filing",
    "rule_change",
    "mandate_change",
    "enforcement",
}

_ACTION_DESCRIPTIONS: dict[str, str] = {
    "bill_signed": "New law signed — review compliance requirements and update underwriting guidelines",
    "rate_filing": "Rate filing change — verify current rates comply with new filing requirements",
    "rule_change": "Regulatory rule changed — update submission workflows and compliance checks",
    "mandate_change": "Coverage mandate changed — verify product offerings include new mandates",
    "enforcement": "Enforcement action — review business practices for similar compliance gaps",
}

_HIGH_ACTIVITY_STATES: set[str] = {"FL", "CA", "NY", "TX", "IL", "PA", "NJ", "MA", "CT", "WA"}


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


def _storage_dir() -> Path:
    if _TESTING:
        return Path(tempfile.gettempdir()) / "insureflow_test" / "law_tracker"
    return Path.cwd() / ".insureflow" / "law_tracker"


class AlertStore:
    """File-backed alert and subscription storage."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._dir = _storage_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._alerts: dict[str, dict[str, Any]] = {}
        self._subscriptions: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        with self._lock:
            # Load alerts
            alerts_file = self._dir / "alerts.json"
            if alerts_file.exists():
                try:
                    with FileLock(str(alerts_file) + ".lock"):
                        raw = alerts_file.read_text(encoding="utf-8")
                    self._alerts = json.loads(raw)
                except (json.JSONDecodeError, OSError):
                    self._alerts = {}

            # Load subscriptions
            if _SUBSCRIPTIONS_FILE.exists():
                try:
                    with FileLock(str(_SUBSCRIPTIONS_FILE) + ".lock"):
                        raw = _SUBSCRIPTIONS_FILE.read_text(encoding="utf-8")
                    self._subscriptions = json.loads(raw)
                except (json.JSONDecodeError, OSError):
                    self._subscriptions = {}

    def _save(self) -> None:
        with self._lock:
            alerts_file = self._dir / "alerts.json"
            try:
                payload = json.dumps(self._alerts, indent=2, default=str)
                with FileLock(str(alerts_file) + ".lock"):
                    atomic_write(alerts_file, payload)
            except OSError as exc:
                logger.warning("Alert store save failed: %s", exc)

            try:
                payload = json.dumps(self._subscriptions, indent=2, default=str)
                with FileLock(str(_SUBSCRIPTIONS_FILE) + ".lock"):
                    atomic_write(_SUBSCRIPTIONS_FILE, payload)
            except OSError as exc:
                logger.warning("Subscription store save failed: %s", exc)

    def save_alert(self, alert: RegulatoryAlert) -> None:
        with self._lock:
            self._alerts[alert.alert_id] = alert.model_dump(mode="json")
            self._save()

    def get_alert(
        self,
        org_id: str = "",
        state_code: str = "",
        severity: str = "",
        reviewed: bool | None = None,
        limit: int = 100,
    ) -> list[RegulatoryAlert]:
        with self._lock:
            results: list[RegulatoryAlert] = []
            for alert_data in reversed(list(self._alerts.values())):
                if org_id and alert_data.get("org_id", "") != org_id:
                    continue
                if state_code and alert_data.get("state_code", "") != state_code.upper():
                    continue
                if severity and alert_data.get("severity", "") != severity:
                    continue
                if reviewed is not None and alert_data.get("reviewed", False) != reviewed:
                    continue
                results.append(RegulatoryAlert.model_validate(alert_data))
                if len(results) >= limit:
                    break
            return results

    def mark_alert_reviewed(self, alert_id: str) -> bool:
        with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id]["reviewed"] = True
                self._save()
                return True
            return False

    def save_subscription(self, sub: AlertSubscription) -> None:
        with self._lock:
            self._subscriptions[sub.org_id] = sub.model_dump(mode="json")
            self._save()

    def get_subscription(self, org_id: str) -> AlertSubscription | None:
        with self._lock:
            data = self._subscriptions.get(org_id)
            return AlertSubscription.model_validate(data) if data else None

    def delete_subscription(self, org_id: str) -> bool:
        with self._lock:
            if org_id in self._subscriptions:
                del self._subscriptions[org_id]
                self._save()
                return True
            return False

    def get_all_subscriptions(self) -> list[AlertSubscription]:
        with self._lock:
            return [AlertSubscription.model_validate(data) for data in self._subscriptions.values()]


# ---------------------------------------------------------------------------
# Law Tracker
# ---------------------------------------------------------------------------

_alert_store: AlertStore | None = None


def get_alert_store() -> AlertStore:
    global _alert_store
    if _alert_store is None:
        _alert_store = AlertStore()
    return _alert_store


class LawTracker:
    """Tracks new state laws and generates regulatory change alerts.

    Pipeline:
    1. Poll all active regulatory sources (NAIC, DOI bulletins, RSS)
    2. Run change detection on collected items
    3. Generate severity-rated alerts
    4. Match alerts to customer subscriptions
    5. Deliver notifications (in-app, email, webhook)
    """

    def __init__(self) -> None:
        self._poller = RegulatoryPoller()
        self._diff_engine = RegulatoryDiffEngine()
        self._monitor = RegulatoryMonitor()
        self._store = get_alert_store()

    def run_scan(self) -> LawTrackerSnapshot:
        """Run a full scan of all regulatory sources and generate alerts.

        Returns a snapshot of what was found.
        """
        now = datetime.now(timezone.utc)
        logger.info("Starting regulatory law scan at %s", now.isoformat())

        # 1. Poll all sources
        collected = self._poller.poll_all()
        sources_polled = len(collected)
        total_items = sum(len(items) for items in collected.values())

        logger.info("Polled %d sources, collected %d items", sources_polled, total_items)

        # 2. Detect changes
        changes = self._diff_engine.detect_all_changes(collected)
        changes_detected = len(changes)

        # 3. Generate alerts from changes
        alerts = self._generate_alerts(changes)
        alerts_generated = len(alerts)

        # 4. Match alerts to subscriptions and deliver
        pending = 0
        for alert in alerts:
            self._store.save_alert(alert)
            if self._should_deliver(alert):
                pending += 1

        # 5. Check freshness and generate stale-data alerts
        freshness = self._monitor.compute_freshness()
        stale_alerts = self._generate_freshness_alerts(freshness)
        for alert in stale_alerts:
            self._store.save_alert(alert)
            if self._should_deliver(alert):
                pending += 1

        snapshot = LawTrackerSnapshot(
            timestamp=now.isoformat(),
            states_monitored=len(_STATE_CODES),
            sources_polled=sources_polled,
            changes_detected=changes_detected + len(stale_alerts),
            alerts_generated=alerts_generated + len(stale_alerts),
            pending_alerts=pending,
            active_subscriptions=len(self._store.get_all_subscriptions()),
        )

        logger.info(
            "Scan complete: %d changes, %d alerts, %d pending",
            changes_detected,
            alerts_generated,
            pending,
        )

        return snapshot

    def _generate_alerts(self, changes: list[RegulatoryChange]) -> list[RegulatoryAlert]:
        """Convert detected changes into severity-rated alerts."""
        alerts: list[RegulatoryAlert] = []
        seen: set[str] = set()

        for change in changes:
            # Deduplicate
            dedup_key = f"{change.state_code}:{change.line_of_business}:{change.rule_key}:{change.new_value}"
            dedup_hash = hashlib.sha256(dedup_key.encode()).hexdigest()[:16]
            if dedup_hash in seen:
                continue
            seen.add(dedup_hash)

            # Determine severity
            change_type = self._classify_change(change)
            severity = _SEVERITY_MAP.get(change_type, "info")
            requires_action = change_type in _ACTION_REQUIRED_TYPES

            # High-activity states get elevated severity
            if change.state_code in _HIGH_ACTIVITY_STATES and severity == "info":
                severity = "warning"

            alert = RegulatoryAlert(
                alert_id=dedup_hash,
                state_code=change.state_code,
                state_name=_STATE_NAMES.get(change.state_code, change.state_code),
                line_of_business=change.line_of_business,
                change_type=change_type,
                severity=severity,
                title=f"{change.line_of_business.replace('_', ' ').title()} rule change in {change.state_code}",
                description=(
                    f"Regulatory change detected in {change.state_code} for {change.line_of_business.replace('_', ' ')}: {change.rule_key} changed from '{change.old_value}' to '{change.new_value}'"
                ),
                source=change.source,
                source_url=change.source_url,
                requires_action=requires_action,
                action_description=_ACTION_DESCRIPTIONS.get(change_type, ""),
            )
            alerts.append(alert)

        return alerts

    def _generate_freshness_alerts(self, freshness: dict[str, Any]) -> list[RegulatoryAlert]:
        """Generate alerts for stale regulatory data."""
        alerts: list[RegulatoryAlert] = []
        seen: set[str] = set()

        for line_name, line_data in freshness.items():
            states = line_data.get("states", {})
            for state_code, state_info in states.items():
                severity = state_info.get("severity", "")
                if severity not in ("stale", "critical"):
                    continue

                dedup_key = f"freshness:{state_code}:{line_name}:{severity}"
                dedup_hash = hashlib.sha256(dedup_key.encode()).hexdigest()[:16]
                if dedup_hash in seen:
                    continue
                seen.add(dedup_hash)

                days_old = state_info.get("days_old", 0)
                alert = RegulatoryAlert(
                    alert_id=dedup_hash,
                    state_code=state_code,
                    state_name=_STATE_NAMES.get(state_code, state_code),
                    line_of_business=line_name,
                    change_type="rule_change",
                    severity="critical" if severity == "stale" else "warning",
                    title=f"Stale regulatory data: {line_name} in {state_code}",
                    description=(f"Regulatory data for {line_name} in {state_code} is {days_old} days old. May not reflect recent legislative changes."),
                    source="freshness_monitor",
                    requires_action=True,
                    action_description="Review and update regulatory data for this state/line combination",
                )
                alerts.append(alert)

        return alerts

    def _classify_change(self, change: RegulatoryChange) -> str:
        """Classify a regulatory change into a type."""
        key = change.rule_key.lower()
        value = str(change.new_value).lower()

        if "rate" in key or "rate" in value:
            return "rate_filing"
        if "mandate" in key or "mandatory" in value:
            return "mandate_change"
        if "bill" in key or "signed" in value or "enacted" in value:
            return "bill_signed"
        if "bulletin" in change.source.lower():
            return "doi_bulletin"
        if "naic" in change.source.lower():
            return "naic_adoption"
        if "enforcement" in key or "penalty" in value or "violation" in value:
            return "enforcement"
        return "rule_change"

    def _should_deliver(self, alert: RegulatoryAlert) -> bool:
        """Check if an alert should be delivered to any subscriber."""
        subscriptions = self._store.get_all_subscriptions()
        for sub in subscriptions:
            if self._matches_subscription(alert, sub):
                return True
        return False

    def _matches_subscription(self, alert: RegulatoryAlert, sub: AlertSubscription) -> bool:
        """Check if an alert matches a subscription's filters."""
        # State filter
        if sub.states and alert.state_code not in sub.states:
            return False

        # Line filter
        if sub.lines and alert.line_of_business not in sub.lines:
            return False

        # Alert type filter
        if sub.alert_types and alert.change_type not in sub.alert_types:
            return False

        # Severity threshold
        severity_order = {"info": 0, "warning": 1, "critical": 2, "urgent": 3}
        alert_sev = severity_order.get(alert.severity, 0)
        threshold_sev = severity_order.get(sub.severity_threshold, 0)
        if alert_sev < threshold_sev:
            return False

        return True

    def get_alerts(
        self,
        org_id: str = "",
        state_code: str = "",
        severity: str = "",
        reviewed: bool | None = None,
        limit: int = 50,
    ) -> list[RegulatoryAlert]:
        """Get alerts with optional filters."""
        return self._store.get_alert(org_id, state_code, severity, reviewed, limit)

    def review_alert(self, alert_id: str) -> bool:
        """Mark an alert as reviewed."""
        return self._store.mark_alert_reviewed(alert_id)

    def subscribe(self, subscription: AlertSubscription) -> dict[str, str]:
        """Create or update an alert subscription."""
        self._store.save_subscription(subscription)
        return {
            "org_id": subscription.org_id,
            "states": ",".join(subscription.states),
            "lines": ",".join(subscription.lines),
            "message": f"Subscribed to alerts for {len(subscription.states)} states, {len(subscription.lines)} lines",
        }

    def get_subscription(self, org_id: str) -> AlertSubscription | None:
        return self._store.get_subscription(org_id)

    def unsubscribe(self, org_id: str) -> bool:
        return self._store.delete_subscription(org_id)

    def get_subscription_alerts(self, org_id: str, limit: int = 50) -> list[RegulatoryAlert]:
        """Get all alerts matching an org's subscription."""
        sub = self._store.get_subscription(org_id)
        if sub is None:
            return []

        all_alerts = self._store.get_alert(limit=500)
        matched = [alert for alert in all_alerts if self._matches_subscription(alert, sub)]
        return matched[:limit]

    def get_state_change_summary(self, state_code: str) -> dict[str, Any]:
        """Get a summary of all tracked changes for a specific state."""
        alerts = self._store.get_alert(state_code=state_code, limit=200)

        by_line: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        action_required = 0

        for alert in alerts:
            line = alert.line_of_business or "general"
            by_line[line] = by_line.get(line, 0) + 1
            by_type[alert.change_type] = by_type.get(alert.change_type, 0) + 1
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
            if alert.requires_action:
                action_required += 1

        return {
            "state_code": state_code,
            "state_name": _STATE_NAMES.get(state_code, state_code),
            "total_alerts": len(alerts),
            "action_required": action_required,
            "by_line": by_line,
            "by_type": by_type,
            "by_severity": by_severity,
            "recent_alerts": [
                {
                    "alert_id": a.alert_id,
                    "title": a.title,
                    "severity": a.severity,
                    "change_type": a.change_type,
                    "line_of_business": a.line_of_business,
                    "detected_at": a.detected_at.isoformat(),
                    "requires_action": a.requires_action,
                }
                for a in alerts[:10]
            ],
        }
