"""OpenObserve log + trace shipper (HTTP JSON ingest).

Disabled unless ``OPENOBSERVE_URL`` is set. Does not invent a live vendor —
local compose OpenObserve is the default sink.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _truthy(name: str, default: str = "") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def enabled() -> bool:
    return bool(os.getenv("OPENOBSERVE_URL", "").strip()) and _truthy("OPENOBSERVE_ENABLED", "true")


def _base_url() -> str:
    return os.getenv("OPENOBSERVE_URL", "").rstrip("/")


def _org() -> str:
    return os.getenv("OPENOBSERVE_ORG", "default").strip() or "default"


def _auth_header() -> str:
    user = os.getenv("OPENOBSERVE_USER", os.getenv("ZO_ROOT_USER_EMAIL", "")).strip()
    password = os.getenv("OPENOBSERVE_PASSWORD", os.getenv("ZO_ROOT_USER_PASSWORD", "")).strip()
    token = os.getenv("OPENOBSERVE_TOKEN", "").strip()
    if token:
        return f"Bearer {token}"
    if user and password:
        blob = base64.b64encode(f"{user}:{password}".encode()).decode()
        return f"Basic {blob}"
    return ""


def ingest_url(stream: str) -> str:
    return f"{_base_url()}/api/{_org()}/{stream}/_json"


def status() -> dict[str, Any]:
    return {
        "enabled": enabled(),
        "url": _base_url() or None,
        "org": _org(),
        "logs_stream": os.getenv("OPENOBSERVE_LOGS_STREAM", "rytera_logs"),
        "traces_stream": os.getenv("OPENOBSERVE_TRACES_STREAM", "rytera_traces"),
        "configured_auth": bool(_auth_header()),
    }


def _post(stream: str, records: list[dict[str, Any]], timeout: float = 2.5) -> bool:
    if not enabled() or not records:
        return False
    url = ingest_url(stream)
    headers = {"Content-Type": "application/json", "User-Agent": "rytera-openobserve/0.3"}
    auth = _auth_header()
    if auth:
        headers["Authorization"] = auth
    payload = json.dumps(records, default=str).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= int(getattr(resp, "status", 200)) < 300
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.debug("OpenObserve ingest failed (%s): %s", stream, exc)
        return False


def emit_logs(records: list[dict[str, Any]]) -> bool:
    stream = os.getenv("OPENOBSERVE_LOGS_STREAM", "rytera_logs")
    return _post(stream, records)


def emit_traces(records: list[dict[str, Any]]) -> bool:
    stream = os.getenv("OPENOBSERVE_TRACES_STREAM", "rytera_traces")
    return _post(stream, records)


def emit_pipeline_trace(summary: dict[str, Any]) -> None:
    if not enabled() or not summary:
        return
    now = datetime.now(tz=timezone.utc).isoformat()
    rec = {
        "_timestamp": now,
        "service": "insureflow-api",
        "event": "pipeline_complete",
        "bundle_id": summary.get("bundle_id"),
        "insurance_line": summary.get("insurance_line"),
        "ai_decision": summary.get("ai_decision"),
        "status": summary.get("status"),
        "quote_eligible": (summary.get("quote") or {}).get("eligible"),
        "adjusted_premium": (summary.get("quote") or {}).get("adjusted_premium"),
        "oracle_findings_count": summary.get("oracle_findings_count"),
        "org_id": summary.get("org_id"),
    }
    emit_traces([rec])


class OpenObserveLogHandler(logging.Handler):
    """Batches JSON log records to OpenObserve (best-effort, non-blocking)."""

    def __init__(self, *, flush_n: int = 20) -> None:
        super().__init__()
        self._buf: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._flush_n = max(int(flush_n), 1)

    def emit(self, record: logging.LogRecord) -> None:
        if not enabled():
            return
        payload = {
            "_timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": os.getenv("SERVICE_NAME", "insureflow-api"),
            "environment": os.getenv("ENVIRONMENT", "development"),
        }
        if record.exc_info:
            payload["exception"] = self.format(record)
        with self._lock:
            self._buf.append(payload)
            if len(self._buf) >= self._flush_n:
                batch = list(self._buf)
                self._buf.clear()
            else:
                batch = []
        if batch:
            threading.Thread(target=emit_logs, args=(batch,), daemon=True).start()


_handler_installed = False


def configure_openobserve_logging() -> bool:
    global _handler_installed
    if not enabled() or _handler_installed:
        return enabled() and _handler_installed
    root = logging.getLogger()
    handler = OpenObserveLogHandler()
    handler.setLevel(logging.INFO)
    root.addHandler(handler)
    _handler_installed = True
    logger.info("OpenObserve log shipper enabled → %s org=%s", _base_url(), _org())
    return True
