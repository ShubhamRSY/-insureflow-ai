"""Billing lifecycle events — durable JSONL for monitoring plan and checkout activity.

Every plan selection, checkout start, purchase, failure and cancellation is
appended as one JSON object per line under ``audit_logs/billing/events.jsonl``
so the numbers survive restarts and can be tailed by log shippers. No paid
processor is wired in; a checkout is completed in-product and this log is the
source of truth for what was chosen, paid and abandoned.

Event types:
    plan_selected        — the plan chosen during signup
    checkout_started     — a paid plan entered checkout
    checkout_completed   — checkout finished, subscription activated
    checkout_failed      — payment details rejected
    checkout_cancelled   — the user abandoned checkout
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_TESTING = os.environ.get("INSUREFLOW_AUTH_TESTING") == "1"

EVENT_TYPES = (
    "plan_selected",
    "checkout_started",
    "checkout_completed",
    "checkout_failed",
    "checkout_cancelled",
)


def _events_path() -> Path:
    override = os.getenv("BILLING_EVENTS_PATH", "").strip()
    if override:
        return Path(override)
    if _TESTING:
        return Path(tempfile.gettempdir()) / "insureflow_test" / "billing_events.jsonl"
    try:
        from insureflow.config import settings

        return Path(settings.audit_log_path) / "billing" / "events.jsonl"
    except Exception:  # pragma: no cover - settings import is always available in-app
        return Path("./audit_logs/billing/events.jsonl")


class BillingEventLog:
    """Append-only JSONL log of billing events with a rollup summary."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = Path(path) if path is not None else _events_path()
        self._lock = threading.RLock()

    @property
    def path(self) -> Path:
        return self._path

    def record(
        self,
        event_type: str,
        *,
        org_id: str = "",
        plan: str = "",
        amount: Optional[float] = None,
        checkout_id: str = "",
        actor: str = "",
        status: str = "",
        reason: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Append one event. Never raises — monitoring must not break onboarding."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "org_id": org_id,
            "plan": plan,
            "amount": amount,
            "checkout_id": checkout_id,
            "actor": actor,
            "status": status,
            "reason": reason,
            "metadata": metadata or {},
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event, default=str) + "\n")
        except OSError:
            logger.warning("Failed to persist billing event %s", event_type, exc_info=True)
        return event

    def list_events(
        self,
        limit: int = 100,
        org_id: str = "",
        event_type: str = "",
    ) -> list[dict[str, Any]]:
        """Return the most recent ``limit`` events, oldest first."""
        if not self._path.exists():
            return []
        try:
            with self._lock:
                raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return []
        events: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if org_id and event.get("org_id") != org_id:
                continue
            if event_type and event.get("event_type") != event_type:
                continue
            events.append(event)
        if limit > 0:
            events = events[-limit:]
        return events

    def summary(self) -> dict[str, Any]:
        """Rollup for the monitoring endpoint: counts, conversion, revenue."""
        events = self.list_events(limit=0)
        by_type: dict[str, int] = {}
        by_plan: dict[str, int] = {}
        started = completed = failed = cancelled = 0
        revenue = 0.0
        for event in events:
            etype = str(event.get("event_type") or "")
            by_type[etype] = by_type.get(etype, 0) + 1
            plan = str(event.get("plan") or "unknown")
            by_plan[plan] = by_plan.get(plan, 0) + 1
            if etype == "checkout_started":
                started += 1
            elif etype == "checkout_completed":
                completed += 1
                amount = event.get("amount")
                if isinstance(amount, (int, float)):
                    revenue += float(amount)
            elif etype == "checkout_failed":
                failed += 1
            elif etype == "checkout_cancelled":
                cancelled += 1
        return {
            "total_events": len(events),
            "by_type": by_type,
            "by_plan": by_plan,
            "checkouts_started": started,
            "checkouts_completed": completed,
            "checkouts_failed": failed,
            "checkouts_cancelled": cancelled,
            "checkout_conversion": round(completed / started, 4) if started else 0.0,
            "monthly_recurring_usd": round(revenue, 2),
            "events_path": str(self._path),
        }


_event_log: Optional[BillingEventLog] = None


def get_billing_event_log() -> BillingEventLog:
    global _event_log
    if _event_log is None:
        _event_log = BillingEventLog()
    return _event_log


def record_billing_event(event_type: str, **kwargs: Any) -> dict[str, Any]:
    """Module-level convenience wrapper used by the API layer."""
    return get_billing_event_log().record(event_type, **kwargs)
