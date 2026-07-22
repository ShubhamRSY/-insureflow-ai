"""Budget enforcement for LLM usage — daily/monthly limits, alerts, hard stops."""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from insureflow.llm.tracker import TokenUsageTracker, get_token_tracker

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when a hard budget limit is exceeded and the request must be blocked."""

    def __init__(self, limit_type: str, limit: float, current: float) -> None:
        self.limit_type = limit_type
        self.limit = limit
        self.current = current
        super().__init__(f"Budget exceeded: {limit_type} limit ${limit:.2f} reached (${current:.2f} spent)")


class BudgetManager:
    """Enforces daily and monthly cost limits with configurable alert thresholds."""

    def __init__(
        self,
        daily_limit: float = 0.0,
        monthly_limit: float = 0.0,
        alert_threshold: float = 0.80,
        hard_stop: bool = True,
        tracker: Optional[TokenUsageTracker] = None,
    ) -> None:
        self.daily_limit = daily_limit or float(os.getenv("LLM_DAILY_BUDGET_LIMIT", "0"))
        self.monthly_limit = monthly_limit or float(os.getenv("LLM_MONTHLY_BUDGET_LIMIT", "0"))
        self.alert_threshold = alert_threshold
        self.hard_stop = hard_stop
        self.tracker = tracker or get_token_tracker()
        self._lock = threading.Lock()
        self._alert_callbacks: list[Callable[[str, float, float], None]] = []
        self._alerts_fired: set[str] = set()

    def add_alert_callback(self, callback: Callable[[str, float, float], None]) -> None:
        self._alert_callbacks.append(callback)

    def check_budget(self) -> dict[str, Any]:
        now = datetime.now(tz=timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        records = self.tracker.get_records(limit=10000)
        daily_cost = 0.0
        monthly_cost = 0.0

        for r in records:
            ts = datetime.fromisoformat(r["timestamp"])
            if ts >= month_start:
                monthly_cost += r["cost"]
                if ts >= today_start:
                    daily_cost += r["cost"]

        daily_pct = (daily_cost / self.daily_limit * 100) if self.daily_limit > 0 else 0
        monthly_pct = (monthly_cost / self.monthly_limit * 100) if self.monthly_limit > 0 else 0

        result = {
            "daily_limit": self.daily_limit,
            "daily_spent": round(daily_cost, 6),
            "daily_remaining": round(max(0, self.daily_limit - daily_cost), 6) if self.daily_limit > 0 else None,
            "daily_pct": round(daily_pct, 2),
            "monthly_limit": self.monthly_limit,
            "monthly_spent": round(monthly_cost, 6),
            "monthly_remaining": round(max(0, self.monthly_limit - monthly_cost), 6) if self.monthly_limit > 0 else None,
            "monthly_pct": round(monthly_pct, 2),
            "hard_stop": self.hard_stop,
            "budget_exceeded": False,
        }

        if self.daily_limit > 0:
            if daily_cost >= self.daily_limit:
                result["budget_exceeded"] = True
                self._fire_alert("daily_limit_exceeded", daily_cost, self.daily_limit)
            elif daily_cost >= self.daily_limit * self.alert_threshold:
                self._fire_alert("daily_limit_warning", daily_cost, self.daily_limit)

        if self.monthly_limit > 0:
            if monthly_cost >= self.monthly_limit:
                result["budget_exceeded"] = True
                self._fire_alert("monthly_limit_exceeded", monthly_cost, self.monthly_limit)
            elif monthly_cost >= self.monthly_limit * self.alert_threshold:
                self._fire_alert("monthly_limit_warning", monthly_cost, self.monthly_limit)

        return result

    def enforce(self) -> None:
        """Raise BudgetExceededError if hard budget limits are breached."""
        if not self.hard_stop:
            return
        status = self.check_budget()
        if status["daily_limit"] > 0 and status["daily_spent"] >= status["daily_limit"]:
            raise BudgetExceededError("daily", status["daily_limit"], status["daily_spent"])
        if status["monthly_limit"] > 0 and status["monthly_spent"] >= status["monthly_limit"]:
            raise BudgetExceededError("monthly", status["monthly_limit"], status["monthly_spent"])

    def _fire_alert(self, alert_type: str, current: float, limit: float) -> None:
        key = f"{alert_type}_{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}"
        with self._lock:
            if key in self._alerts_fired:
                return
            self._alerts_fired.add(key)

        logger.warning("Budget alert: %s — $%.2f / $%.2f", alert_type, current, limit)
        for cb in self._alert_callbacks:
            try:
                cb(alert_type, current, limit)
            except Exception:
                logger.debug("Alert callback failed", exc_info=True)

    def reset_alerts(self) -> None:
        with self._lock:
            self._alerts_fired.clear()


_budget_manager: Optional[BudgetManager] = None


def get_budget_manager() -> BudgetManager:
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = BudgetManager()
    return _budget_manager
