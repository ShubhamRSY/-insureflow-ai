"""Production monitoring snapshot for Railway / ops dashboards."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any


_STARTED_AT = time.time()


def collect_ops_snapshot(job_store: Any | None = None) -> dict[str, Any]:
    """Lightweight health + job latency signals (no external deps required)."""
    from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness, is_shadow_mode
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
        alerts.append({"severity": "info", "code": "shadow_mode", "message": "PILOT_SHADOW_MODE active — bind disabled"})

    return {
        "ok": True,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "uptime_seconds": uptime_s,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "bank_mode": os.getenv("BANK_MODE", "false").lower() in {"1", "true", "yes"},
        "shadow_mode": is_shadow_mode(),
        "job_store": type(store).__name__,
        "sandbox_overall": readiness.get("overall"),
        "required_feeds": f"{readiness.get('required_ready')}/{readiness.get('required_total')}",
        "jobs": by_ns,
        "totals": {"processing": processing, "completed": completed, "failed": failed},
        "alerts": alerts,
        "railway_healthcheck": "/health",
        "ops_endpoint": "/ops/snapshot",
    }
