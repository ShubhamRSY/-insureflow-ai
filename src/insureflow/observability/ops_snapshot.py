"""Production monitoring snapshot for Railway / ops dashboards."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

_STARTED_AT = time.time()


def collect_ops_snapshot(job_store: Any | None = None) -> dict[str, Any]:
    """Lightweight health + job latency signals (no external deps required)."""
    from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness, bind_is_allowed, is_ready_mode, is_shadow_mode, operating_mode
    from insureflow.storage.job_store import get_job_store

    store = job_store or get_job_store()
    namespaces = ("insurance", "mortgage", "lending")
    by_ns: dict[str, Any] = {}
    failed = 0
    processing = 0
    completed = 0
    for ns in namespaces:
        try:
            ids = store.list_ids(ns, org_id="default")[:200]
        except Exception:
            ids = []
        counts = {"processing": 0, "completed": 0, "failed": 0}
        for jid in ids:
            job = store.get(ns, jid, org_id="default") or {}
            status = str(job.get("status") or "unknown")
            if status in counts:
                counts[status] += 1
        failed += counts["failed"]
        processing += counts["processing"]
        completed += counts["completed"]
        by_ns[ns] = {"jobs_sampled": len(ids), **counts}

    readiness = assess_sandbox_readiness(ping=False)
    uptime_s = int(time.time() - _STARTED_AT)

    alerts: list[dict[str, str]] = []
    if failed > 0:
        alerts.append({"severity": "warning", "code": "failed_jobs", "message": f"{failed} failed jobs in sample"})
    if readiness.get("overall") == "not_ready":
        alerts.append({"severity": "warning", "code": "sandbox_not_ready", "message": "Sandbox overall=not_ready"})
    if is_shadow_mode():
        alerts.append({"severity": "info", "code": "shadow_mode", "message": "Shadow mode active — bind disabled"})
    elif is_ready_mode() and not bind_is_allowed():
        alerts.append(
            {
                "severity": "warning",
                "code": "ready_pas_missing",
                "message": "Ready mode on but Guidewire/BriteCore credentials missing — bind blocked",
            }
        )
    elif is_ready_mode():
        alerts.append({"severity": "info", "code": "ready_mode", "message": "Ready mode — bind enabled when UW-approved"})

    return {
        "ok": True,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "uptime_seconds": uptime_s,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "bank_mode": os.getenv("BANK_MODE", "false").lower() in {"1", "true", "yes"},
        "operating_mode": operating_mode(),
        "shadow_mode": is_shadow_mode(),
        "ready_mode": is_ready_mode(),
        "bind_allowed": bind_is_allowed(),
        "job_store": type(store).__name__,
        "sandbox_overall": readiness.get("overall"),
        "required_feeds": f"{readiness.get('required_ready')}/{readiness.get('required_total')}",
        "jobs": by_ns,
        "totals": {"processing": processing, "completed": completed, "failed": failed},
        "alerts": alerts,
        "railway_healthcheck": "/health",
        "ops_endpoint": "/ops/snapshot",
        "metrics_endpoint": "/metrics",
        "observability": _observability_status(),
    }


def _observability_status() -> dict[str, Any]:
    try:
        from insureflow.observability.openobserve import status as openobserve_status
        from insureflow.observability.prometheus_metrics import available as prometheus_available

        return {
            "prometheus": {"metrics_path": "/metrics", "client_available": prometheus_available()},
            "openobserve": openobserve_status(),
            "grafana": {"local_url": os.getenv("GRAFANA_URL", "http://localhost:3000")},
        }
    except Exception as exc:
        return {"error": str(exc)}
