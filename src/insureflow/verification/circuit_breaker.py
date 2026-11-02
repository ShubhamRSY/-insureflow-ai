"""Circuit breaker for LLM and external service calls.

Stops processing when error rates exceed configurable thresholds.
Follows the standard three-state pattern: CLOSED (normal), OPEN (failing),
HALF_OPEN (probing recovery).

When REDIS_URL (or CELERY_BROKER_URL) points at Redis, breakers made by
``get_circuit_breaker`` share state, failure count and last-failure time
across processes, so every API and Celery worker opens together. If Redis is
unreachable, each process falls back to its own local state for 30s and retries.
"""

from __future__ import annotations

import logging
import os
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
        redis_client: Any = None,
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

        self._redis = redis_client
        self._redis_retry_at = 0.0
        self._key = f"insureflow:circuit:{name}"

    # --- shared state (Redis) -------------------------------------------------

    def _client(self) -> Any:
        if self._redis is None or time.time() < self._redis_retry_at:
            return None
        return self._redis

    def _redis_failed(self, exc: Exception) -> None:
        self._redis_retry_at = time.time() + _REDIS_RETRY_SECONDS
        logger.warning("circuit_breaker=%s Redis unavailable, using local state for %ss: %s", self.name, _REDIS_RETRY_SECONDS, exc)

    def _pull(self) -> None:
        r = self._client()
        if r is None:
            return
        try:
            raw = r.hgetall(self._key)
        except Exception as exc:
            self._redis_failed(exc)
            return
        self._state = CircuitState(raw.get("state", CircuitState.CLOSED.value))
        self._failure_count = int(raw.get("failures", 0))
        self._last_failure_time = float(raw.get("last_failure", 0.0))

    def _push(self) -> None:
        r = self._client()
        if r is None:
            return
        try:
            pipe = r.pipeline()
            pipe.hset(
                self._key,
                mapping={"state": self._state.value, "failures": self._failure_count, "last_failure": self._last_failure_time},
            )
            pipe.expire(self._key, _REDIS_KEY_TTL_SECONDS)
            pipe.execute()
        except Exception as exc:
            self._redis_failed(exc)

    def _add_failures(self, delta: int) -> int:
        """Change the failure count atomically (shared when Redis is up); never below 0."""
        r = self._client()
        if r is not None:
            try:
                pipe = r.pipeline()
                pipe.hincrby(self._key, "failures", delta)
                if delta > 0:
                    pipe.hset(self._key, "last_failure", self._last_failure_time)
                pipe.expire(self._key, _REDIS_KEY_TTL_SECONDS)
                count = int(pipe.execute()[0])
                if count < 0:
                    r.hset(self._key, "failures", 0)
                return max(0, count)
            except Exception as exc:
                self._redis_failed(exc)
        return max(0, self._failure_count + delta)

    # --- breaker ----------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        self._pull()
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
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
        self._push()
        logger.info("circuit_breaker=%s %s -> %s reason=%s", self.name, old.value, new_state.value, reason)

    def record_success(self) -> None:
        self._pull()
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._failure_count = 0
                self._success_count = 0
                self._half_open_calls = 0
                self._transition(CircuitState.CLOSED, "half-open probe succeeded")
        elif self._state == CircuitState.CLOSED:
            self._failure_count = self._add_failures(-1)

    def record_failure(self) -> None:
        self._pull()
        self._last_failure_time = time.time()
        self._failure_count = self._add_failures(1)

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
        else:
            self._push()

    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "history_length": len(self._history),
            "shared": self._client() is not None,
        }

    def recent_events(self, limit: int = 10) -> list[CircuitBreakerEvent]:
        return self._history[-limit:]


_REDIS_RETRY_SECONDS = 30.0
_REDIS_KEY_TTL_SECONDS = 86400

_breakers: dict[str, CircuitBreaker] = {}


def _shared_redis() -> Any:
    """Redis client for shared breaker state, or None to keep state per process."""
    url = (os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "")).strip()
    if not url.startswith("redis"):
        return None
    try:
        import redis as _redis

        return _redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
    except Exception as exc:  # pragma: no cover - import/config dependent
        logger.warning("circuit breaker: Redis client not created, state stays per process: %s", exc)
        return None


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
            redis_client=_shared_redis(),
        )
    return _breakers[name]
