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
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

_BROKER_ENVS = ("REDIS_URL", "CELERY_BROKER_URL")

# A submission is routed here instead of the default "pipeline" queue once it
# has any document uploaded via the large-file (S3 presigned) path — see
# object_storage.py. Keeping these on their own queue means a burst of GB-scale
# submissions queues up behind each other, not behind (or in front of) the
# fast, small submissions that make up most day-to-day traffic. A worker must
# actually be listening on this queue (``-Q ...,pipeline-large``) or jobs sent
# here just sit unclaimed — see docker-compose.yml / infra/aws/main.tf.
LARGE_FILE_QUEUE = "pipeline-large"

# The default per-task time limits (celery_app.py) assume a normal, fast
# submission. A near-200MB (MAX_PROCESSABLE_BYTES) document being OCR'd can
# plausibly run long past that, so large-file jobs get a longer leash instead
# of being SIGKILL'd mid-run.
_LARGE_FILE_SOFT_TIME_LIMIT = 1700
_LARGE_FILE_TIME_LIMIT = 1800

# Bounds how many pipeline/mortgage runs execute inside the API process at
# once. Only matters when Celery is unavailable and jobs fall back to
# BackgroundTasks (see should_use_celery) — without a cap, a burst of large
# submissions during a broker outage could spawn unboundedly many concurrent
# OCR/LLM runs in the same process that's serving API traffic, competing with
# it for memory/CPU instead of just running slower.
_MAX_INPROCESS_JOBS = int(os.getenv("INSURANCE_MAX_INPROCESS_JOBS", "3"))
_inprocess_job_semaphore = threading.BoundedSemaphore(_MAX_INPROCESS_JOBS)

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


def _has_large_file_document(request_data: dict[str, Any]) -> bool:
    """True when any document in the request was uploaded via the S3
    presigned path (``encoding: "s3_ref"``) rather than inlined as base64 —
    that path only exists for files over the 25MB inline cap, so its mere
    presence is a cheap, no-I/O signal that this submission is "large"."""
    for doc in request_data.get("documents") or []:
        if isinstance(doc, dict) and doc.get("encoding") == "s3_ref":
            return True
    return False


def send_pipeline_task(job_id: str, request_data: dict[str, Any], org_id: str) -> str:
    """Dispatch an insurance pipeline job to a Celery queue.

    Large-file submissions (any document uploaded via S3 presigned upload)
    are routed to ``LARGE_FILE_QUEUE`` with an extended time limit instead of
    the default ``pipeline`` queue, so they queue and time out independently
    of the small, fast submissions most traffic consists of.

    Returns the Celery task id. Raises on broker/serialization failure so the
    caller can fall back to in-process execution.
    """
    from insureflow.tasks.celery_app import celery_app

    large = _has_large_file_document(request_data)
    queue = LARGE_FILE_QUEUE if large else "pipeline"
    extra: dict[str, Any] = {"soft_time_limit": _LARGE_FILE_SOFT_TIME_LIMIT, "time_limit": _LARGE_FILE_TIME_LIMIT} if large else {}

    async_result = celery_app.send_task(
        "insureflow.tasks.pipeline_tasks.run_pipeline",
        args=[job_id, request_data, org_id],
        queue=queue,
        **extra,
    )
    _observe_dispatch(queue, "celery")
    return str(async_result.id)


def send_mortgage_task(job_id: str, request_data: dict[str, Any], org_id: str) -> str:
    """Dispatch a mortgage pipeline job to the ``mortgage`` Celery queue."""
    from insureflow.tasks.celery_app import celery_app

    async_result = celery_app.send_task(
        "insureflow.tasks.mortgage_tasks.run_mortgage_pipeline",
        args=[job_id, request_data, org_id],
        queue="mortgage",
    )
    _observe_dispatch("mortgage", "celery")
    return str(async_result.id)


def _observe_dispatch(queue: str, backend: str) -> None:
    try:
        from insureflow.observability.prometheus_metrics import observe_pipeline_dispatch

        observe_pipeline_dispatch(queue, backend)
    except Exception:
        pass


def _slot_acquired() -> None:
    try:
        from insureflow.observability.prometheus_metrics import inprocess_job_slot_acquired

        inprocess_job_slot_acquired()
    except Exception:
        pass


def _slot_released() -> None:
    try:
        from insureflow.observability.prometheus_metrics import inprocess_job_slot_released

        inprocess_job_slot_released()
    except Exception:
        pass


@contextmanager
def in_process_job_slot() -> Iterator[None]:
    """Throttle in-process pipeline execution to ``INSURANCE_MAX_INPROCESS_JOBS``
    concurrent runs (default 3).

    Wrap the body of every BackgroundTasks fallback executor (pipeline,
    pipeline v2, mortgage) in this. Acquiring blocks rather than rejecting, so
    excess jobs queue up in the threadpool instead of being dropped — the
    same backpressure a small Celery worker pool would give you, applied to
    the in-process fallback path.

    Reports through ``rytera_pipeline_dispatch_total{queue="in_process",...}``
    and ``rytera_inprocess_job_slots_in_use`` so a burst of in-process
    fallback runs (e.g. during a broker outage) is visible on a dashboard,
    not just inferred after the fact from CPU/memory graphs.
    """
    _observe_dispatch("in_process", "in_process")
    _inprocess_job_semaphore.acquire()
    try:
        _slot_acquired()
        yield
    finally:
        _slot_released()
        _inprocess_job_semaphore.release()
