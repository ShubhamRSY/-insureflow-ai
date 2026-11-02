"""Circuit breaker state shared through Redis (two breakers = two worker processes)."""

from __future__ import annotations

import time

from insureflow.verification.circuit_breaker import CircuitBreaker, CircuitState


class _FakeRedis:
    """Just the hash commands the breaker uses; pipeline runs commands immediately."""

    def __init__(self) -> None:
        self.data: dict[str, dict[str, str]] = {}
        self._results: list[object] = []

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.data.get(key, {}))

    def hset(self, key: str, field: str | None = None, value: object = None, mapping: dict | None = None) -> int:
        h = self.data.setdefault(key, {})
        for k, v in (mapping or {field: value}).items():
            h[k] = str(v)
        self._results.append(1)
        return 1

    def hincrby(self, key: str, field: str, amount: int) -> int:
        h = self.data.setdefault(key, {})
        h[field] = str(int(h.get(field, 0)) + amount)
        self._results.append(int(h[field]))
        return int(h[field])

    def expire(self, key: str, ttl: int) -> bool:
        self._results.append(True)
        return True

    def pipeline(self) -> _FakeRedis:
        self._results = []
        return self

    def execute(self) -> list[object]:
        return self._results


class _DownRedis:
    def __getattr__(self, name: str):
        def fail(*a, **k):
            raise ConnectionError("redis down")

        return fail


def test_failures_in_one_worker_open_the_breaker_in_another() -> None:
    redis = _FakeRedis()
    api = CircuitBreaker(name="llm:x", failure_threshold=3, recovery_timeout=0.05, redis_client=redis)
    celery = CircuitBreaker(name="llm:x", failure_threshold=3, recovery_timeout=0.05, redis_client=redis)

    api.record_failure()
    celery.record_failure()
    assert api.state == CircuitState.CLOSED
    celery.record_failure()  # 3rd failure overall, split across workers
    assert api.state == CircuitState.OPEN
    assert api.is_available is False

    time.sleep(0.06)
    assert celery.state == CircuitState.HALF_OPEN
    api.record_success()
    assert celery.state == CircuitState.CLOSED
    assert celery.status()["failure_count"] == 0

    # success decay never drives the shared count below zero
    api.record_success()
    assert int(redis.data["insureflow:circuit:llm:x"]["failures"]) == 0


def test_redis_down_falls_back_to_local_state() -> None:
    cb = CircuitBreaker(name="llm:y", failure_threshold=2, redis_client=_DownRedis())
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.status()["shared"] is False
