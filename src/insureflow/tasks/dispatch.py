"""Async dispatch helpers — prefer Celery, fall back to in-process execution.

A multi-worker web deployment must not run the 13-agent pipeline swarm on an
API event loop: one heavy submission would stall the worker serving it. The
default is therefore to dispatch through Celery whenever a broker is
configured and reachable, and to degrade gracefully to in-process background
tasks when the broker is down — so a Redis hiccup never drops a submission.

Explicit escapes:
- ``INSURANCE_USE_CELERY=1`` / ``=0`` — force Celery on/off.
- ``INSURANCE_IN_PROCESS=1`` — force in-process (testing, tiny deploys).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_BROKER_ENVS = ("REDIS_URL", "CELERY_BROKER_URL")

_probe_lock = threading.Lock()
_celery_available: bool | None = None
_probe_at: float = 0.0

# How long to trust a broker reachability probe before re-pinging. Keeps us
# honest when Redis flaps during a deploy.
_PROBE_TTL_SECONDS = 15.0

_TRUE_ENV = {"1", "true", "yes", "on"}
_FALSE_ENV = {"0", "false", "no", "off"}


def broker_configured() -> bool:
    """True when any broker env var is present and looks like Redis."""
    return any(os.getenv(name, "").strip().startswith("redis") for name in _BROKER_ENVS)


def _probe_broker() -> bool:
    url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "") or ""
    try:
        import redis as _redis

        client = _redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return True
    except Exception as exc:  # pragma: no cover - network dependent
        logger.warning("Celery broker not reachable at %s: %s", url, exc)
        return False


def broker_reachable() -> bool:
    """True when a broker is configured AND responds to PING (cached, TTL'd)."""
    global _celery_available, _probe_at
    if not broker_configured():
        return False
    now = time.monotonic()
    if _celery_available is None or now - _probe_at > _PROBE_TTL_SECONDS:
        with _probe_lock:
            if _celery_available is None or time.monotonic() - _probe_at > _PROBE_TTL_SECONDS:
                _celery_available = _probe_broker()
                _probe_at = time.monotonic()
    return bool(_celery_available)


def should_use_celery(requested: bool | None = None) -> bool:
    """Decide whether a pipeline run should dispatch through Celery.

    Precedence:
    1. ``INSURANCE_USE_CELERY=1/0`` or ``INSURANCE_IN_PROCESS=1`` — explicit.
    2. Explicit request on the submission (``req.use_celery``).
    3. Default: Celery when the broker is configured and reachable.
    """
    env = os.getenv("INSURANCE_USE_CELERY", "").strip().lower()
    if env in _TRUE_ENV:
        return True
    if env in _FALSE_ENV:
        return False
    if os.getenv("INSURANCE_IN_PROCESS", "").strip().lower() in _TRUE_ENV:
        return False
    if requested is True:
        return True
    if requested is False:
        return False
    return broker_reachable()


def send_pipeline_task(job_id: str, request_data: dict[str, Any], org_id: str) -> str:
    """Dispatch an insurance pipeline job to the ``pipeline`` Celery queue.

    Returns the Celery task id. Raises on broker/serialization failure so the
    caller can fall back to in-process execution.
    """
    from insureflow.tasks.celery_app import celery_app

    async_result = celery_app.send_task(
        "insureflow.tasks.pipeline_tasks.run_pipeline",
        args=[job_id, request_data, org_id],
        queue="pipeline",
    )
    return str(async_result.id)


def send_mortgage_task(job_id: str, request_data: dict[str, Any], org_id: str) -> str:
    """Dispatch a mortgage pipeline job to the ``mortgage`` Celery queue."""
    from insureflow.tasks.celery_app import celery_app

    async_result = celery_app.send_task(
        "insureflow.tasks.mortgage_tasks.run_mortgage_pipeline",
        args=[job_id, request_data, org_id],
        queue="mortgage",
    )
    return str(async_result.id)
