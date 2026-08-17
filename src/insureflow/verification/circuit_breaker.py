"""Circuit breaker for LLM and external service calls.

Stops processing when error rates exceed configurable thresholds.
Follows the standard three-state pattern: CLOSED (normal), OPEN (failing),
HALF_OPEN (probing recovery).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    state_from: CircuitState
    state_to: CircuitState
    reason: str = ""


class CircuitBreaker:
    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._history: list[CircuitBreakerEvent] = []

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN, "recovery timeout elapsed")
        return self._state

    @property
    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def _transition(self, new_state: CircuitState, reason: str = "") -> None:
        old = self._state
        self._state = new_state
        event = CircuitBreakerEvent(state_from=old, state_to=new_state, reason=reason)
        self._history.append(event)
        logger.info("circuit_breaker=%s %s -> %s reason=%s", self.name, old.value, new_state.value, reason)

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._failure_count = 0
                self._success_count = 0
                self._half_open_calls = 0
                self._transition(CircuitState.CLOSED, "half-open probe succeeded")
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN, "half-open probe failed")
        elif self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
            self._transition(CircuitState.OPEN, f"failure count {self._failure_count} >= threshold {self.failure_threshold}")

    def reset(self) -> None:
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        if self._state != CircuitState.CLOSED:
            self._transition(CircuitState.CLOSED, "manual reset")

    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "history_length": len(self._history),
        }

    def recent_events(self, limit: int = 10) -> list[CircuitBreakerEvent]:
        return self._history[-limit:]


_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str = "llm",
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _breakers[name]
