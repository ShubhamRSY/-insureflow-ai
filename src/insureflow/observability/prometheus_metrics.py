"""Prometheus metrics for Rytera API + UW pipeline.

Scrape ``GET /metrics``. Multi-worker uvicorn: set ``PROMETHEUS_MULTIPROC_DIR``.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Iterable

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, Info, generate_latest
from prometheus_client import REGISTRY as _DEFAULT_REGISTRY
from prometheus_client.core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

# Queues a Celery worker can be listening on — see tasks/celery_app.py and
# tasks/dispatch.py (LARGE_FILE_QUEUE). Kept here, not imported from dispatch,
# to avoid a circular import: dispatch reports through this module instead.
_CELERY_QUEUES = ("agents", "pipeline", "pipeline-large", "mortgage")

_PATH_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_PATH_HEX = re.compile(r"/[0-9a-f]{16,}(?=/|$)", re.I)
_PATH_DEMO = re.compile(r"/demo-[0-9a-f]+", re.I)
_PATH_NUM = re.compile(r"/\d+(?=/|$)")


def _mp_dir() -> str:
    return (os.getenv("PROMETHEUS_MULTIPROC_DIR") or "").strip()


class JobStoreCollector(Collector):
    """Scrape-time job counts — avoids multiprocess Gauge staleness."""

    def __init__(self) -> None:
        self._cache: tuple[float, dict[str, Any]] | None = None

    def _snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._cache and now - self._cache[0] < 10.0:
            return self._cache[1]
        try:
            from insureflow.observability.ops_snapshot import collect_ops_snapshot

            snap = collect_ops_snapshot()
        except Exception:
            snap = {}
        self._cache = (now, snap)
        return snap

    def collect(self) -> Iterable[Metric]:
        g = GaugeMetricFamily(
            "rytera_jobs",
            "Job-store counts by namespace and status",
            labels=["namespace", "status"],
        )
        jobs = (self._snapshot() or {}).get("jobs") or {}
        for ns, counts in jobs.items():
            if not isinstance(counts, dict):
                continue
            for status in ("processing", "completed", "failed"):
                g.add_metric([str(ns), status], float(counts.get(status) or 0))
        yield g


class CeleryQueueDepthCollector(Collector):
    """Scrape-time depth (``LLEN``) of each Celery/Redis queue.

    A Redis list backs each queue name directly, so its length is exactly
    "how many tasks are waiting for a worker" — the signal you need to notice
    ``pipeline-large`` backing up (or the default ``pipeline`` queue getting
    starved behind it) before someone complains about a stuck submission.
    Cached briefly like ``JobStoreCollector`` so a Prometheus scrape can't
    turn into a Redis hot loop.
    """

    def __init__(self) -> None:
        self._cache: tuple[float, dict[str, int]] | None = None

    def _snapshot(self) -> dict[str, int]:
        now = time.monotonic()
        if self._cache and now - self._cache[0] < 10.0:
            return self._cache[1]
        depths: dict[str, int] = {}
        url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or ""
        if url.startswith("redis"):
            try:
                import redis as _redis

                client = _redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
                pipe = client.pipeline()
                for q in _CELERY_QUEUES:
                    pipe.llen(q)
                results = pipe.execute()
                depths = dict(zip(_CELERY_QUEUES, (int(r) for r in results), strict=False))
            except Exception:
                depths = {}
        self._cache = (now, depths)
        return depths

    def collect(self) -> Iterable[Metric]:
        g = GaugeMetricFamily(
            "rytera_celery_queue_depth",
            "Tasks waiting (not yet claimed by a worker) in each Celery queue",
            labels=["queue"],
        )
        depths = self._snapshot()
        for q in _CELERY_QUEUES:
            g.add_metric([q], float(depths.get(q, 0)))
        yield g


def _build_metrics() -> dict[str, Any]:
    http_requests = Counter(
        "rytera_http_requests_total",
        "HTTP requests",
        ["method", "path", "status"],
    )
    http_duration = Histogram(
        "rytera_http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
    )
    pipeline_runs = Counter(
        "rytera_pipeline_runs_total",
        "Insurance pipeline completions",
        ["line", "decision", "status"],
    )
    quotes = Counter(
        "rytera_quotes_total",
        "Quotes produced by the rating engine",
        ["eligible", "line"],
    )
    binds = Counter(
        "rytera_binds_total",
        "Bind attempts",
        ["result"],
    )
    oracle_findings = Counter(
        "rytera_oracle_findings_total",
        "Oracle / bureau findings",
        ["severity"],
    )
    oversized_document_rejections = Counter(
        "rytera_oversized_document_rejections_total",
        "Inline document submissions rejected for exceeding the per-document size cap",
        ["endpoint"],
    )
    doc_quality_decisions = Counter(
        "rytera_doc_quality_decisions_total",
        "Document-quality gate decisions (pass/warn/block)",
        ["decision"],
    )
    pipeline_dispatch = Counter(
        "rytera_pipeline_dispatch_total",
        "Pipeline job dispatch outcomes — which queue/backend a job actually ran on",
        ["queue", "backend"],
    )
    inprocess_job_slots_in_use = Gauge(
        "rytera_inprocess_job_slots_in_use",
        "In-process (BackgroundTasks fallback) pipeline job slots currently held",
        multiprocess_mode="livesum",
    )
    info = Info("rytera", "Rytera build identity")
    info.info({"version": os.getenv("RYTERA_VERSION", "0.3.1"), "service": "insureflow-api"})
    return {
        "http_requests": http_requests,
        "http_duration": http_duration,
        "pipeline_runs": pipeline_runs,
        "quotes": quotes,
        "binds": binds,
        "oracle_findings": oracle_findings,
        "oversized_document_rejections": oversized_document_rejections,
        "doc_quality_decisions": doc_quality_decisions,
        "pipeline_dispatch": pipeline_dispatch,
        "inprocess_job_slots_in_use": inprocess_job_slots_in_use,
    }


_METRICS = _build_metrics()
_JOB_COLLECTOR = JobStoreCollector()
_QUEUE_DEPTH_COLLECTOR = CeleryQueueDepthCollector()
_JOB_REGISTERED = False


def _ensure_job_collector() -> None:
    global _JOB_REGISTERED
    if _JOB_REGISTERED:
        return
    for collector in (_JOB_COLLECTOR, _QUEUE_DEPTH_COLLECTOR):
        try:
            _DEFAULT_REGISTRY.register(collector)
        except ValueError:
            pass
    _JOB_REGISTERED = True


_ensure_job_collector()


def available() -> bool:
    return True


def normalize_path(path: str) -> str:
    raw = (path or "/").split("?", 1)[0]
    raw = _PATH_UUID.sub("{id}", raw)
    raw = _PATH_DEMO.sub("/{id}", raw)
    raw = _PATH_HEX.sub("/{id}", raw)
    raw = _PATH_NUM.sub("/{n}", raw)
    if len(raw) > 120:
        raw = raw[:120]
    return raw or "/"


def observe_http(method: str, path: str, status: int, duration_seconds: float) -> None:
    if not _METRICS:
        return
    route = normalize_path(path)
    meth = (method or "GET").upper()
    _METRICS["http_requests"].labels(method=meth, path=route, status=str(status)).inc()
    _METRICS["http_duration"].labels(method=meth, path=route).observe(max(duration_seconds, 0.0))


def observe_pipeline(summary: dict[str, Any] | None) -> None:
    if not _METRICS or not summary:
        return
    line = str(summary.get("insurance_line") or summary.get("product_line") or "unknown")[:48]
    decision = str(summary.get("ai_decision") or summary.get("outcome") or "unknown")[:48]
    status = str(summary.get("status") or "unknown")[:32]
    _METRICS["pipeline_runs"].labels(line=line, decision=decision, status=status).inc()
    quote = summary.get("quote") or {}
    if quote:
        eligible = "true" if quote.get("eligible", True) else "false"
        _METRICS["quotes"].labels(eligible=eligible, line=line).inc()
    findings_n = int(summary.get("oracle_findings_count") or 0)
    if findings_n:
        _METRICS["oracle_findings"].labels(severity="mixed").inc(findings_n)
    _emit_cloudwatch("PipelineRuns", 1.0, {"line": line, "decision": decision, "status": status})


def observe_bind(result: str) -> None:
    if not _METRICS:
        return
    label = str(result or "unknown")[:32]
    _METRICS["binds"].labels(result=label).inc()
    _emit_cloudwatch("Binds", 1.0, {"result": label})


def observe_oversized_document_rejection(endpoint: str) -> None:
    if not _METRICS:
        return
    _METRICS["oversized_document_rejections"].labels(endpoint=str(endpoint or "unknown")[:64]).inc()


def observe_doc_quality_decision(decision: str) -> None:
    if not _METRICS:
        return
    _METRICS["doc_quality_decisions"].labels(decision=str(decision or "unknown")[:16]).inc()


def observe_pipeline_dispatch(queue: str, backend: str) -> None:
    if not _METRICS:
        return
    _METRICS["pipeline_dispatch"].labels(queue=str(queue or "unknown")[:32], backend=str(backend or "unknown")[:16]).inc()


def inprocess_job_slot_acquired() -> None:
    if not _METRICS:
        return
    _METRICS["inprocess_job_slots_in_use"].inc()


def inprocess_job_slot_released() -> None:
    if not _METRICS:
        return
    _METRICS["inprocess_job_slots_in_use"].dec()


def _emit_cloudwatch(name: str, value: float, dimensions: dict[str, str] | None = None) -> None:
    try:
        from insureflow.observability.cloudwatch import emit_metric

        emit_metric(name, value, dimensions=dimensions)
    except Exception:
        pass


def render_metrics() -> tuple[bytes, str]:
    """Return (body, content_type) for ``GET /metrics``."""
    mp = _mp_dir()
    if mp:
        from prometheus_client import multiprocess

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
        registry.register(JobStoreCollector())
        registry.register(CeleryQueueDepthCollector())
        return generate_latest(registry), CONTENT_TYPE_LATEST
    _ensure_job_collector()
    return generate_latest(_DEFAULT_REGISTRY), CONTENT_TYPE_LATEST
