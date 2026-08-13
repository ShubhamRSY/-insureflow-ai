"""Prometheus metrics for Rytera API + UW pipeline.

Scrape ``GET /metrics``. Multi-worker uvicorn: set ``PROMETHEUS_MULTIPROC_DIR``.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Iterable

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, Info, generate_latest
from prometheus_client import REGISTRY as _DEFAULT_REGISTRY
from prometheus_client.core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector

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
    info = Info("rytera", "Rytera build identity")
    info.info({"version": os.getenv("RYTERA_VERSION", "0.3.1"), "service": "insureflow-api"})
    return {
        "http_requests": http_requests,
        "http_duration": http_duration,
        "pipeline_runs": pipeline_runs,
        "quotes": quotes,
        "binds": binds,
        "oracle_findings": oracle_findings,
    }


_METRICS = _build_metrics()
_JOB_COLLECTOR = JobStoreCollector()
_JOB_REGISTERED = False


def _ensure_job_collector() -> None:
    global _JOB_REGISTERED
    if _JOB_REGISTERED:
        return
    try:
        _DEFAULT_REGISTRY.register(_JOB_COLLECTOR)
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


def observe_bind(result: str) -> None:
    if not _METRICS:
        return
    _METRICS["binds"].labels(result=str(result or "unknown")[:32]).inc()


def render_metrics() -> tuple[bytes, str]:
    """Return (body, content_type) for ``GET /metrics``."""
    mp = _mp_dir()
    if mp:
        from prometheus_client import multiprocess

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
        registry.register(JobStoreCollector())
        return generate_latest(registry), CONTENT_TYPE_LATEST
    _ensure_job_collector()
    return generate_latest(_DEFAULT_REGISTRY), CONTENT_TYPE_LATEST
