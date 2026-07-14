"""Structured logging → stdout (picked up by CloudWatch Logs agent / FireLens / ECS awslogs)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any


class CloudWatchJsonFormatter(logging.Formatter):
    """Emit JSON logs suitable for CloudWatch Logs Insights."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": os.getenv("SERVICE_NAME", "insureflow-api"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "bank_mode": os.getenv("BANK_MODE", "false"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("bundle_id", "org_id", "request_id", "agent", "user"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def configure_cloudwatch_logging(level: int = logging.INFO) -> None:
    """Attach JSON formatter to root logger when CLOUDWATCH_LOGS=true or BANK_MODE."""
    enabled = os.getenv("CLOUDWATCH_LOGS", "").lower() in {"1", "true", "yes"}
    bank = os.getenv("BANK_MODE", "").lower() in {"1", "true", "yes"}
    env = os.getenv("ENVIRONMENT", "").lower()
    if not (enabled or bank or env == "production"):
        return

    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(CloudWatchJsonFormatter())
    # Replace plain handlers so ECS awslogs driver gets one JSON line per event
    root.handlers.clear()
    root.addHandler(handler)


def emit_metric(name: str, value: float, unit: str = "Count", dimensions: dict[str, str] | None = None) -> None:
    """Best-effort CloudWatch custom metric (no-op without boto3 / AWS credentials)."""
    if os.getenv("CLOUDWATCH_METRICS", "true").lower() not in {"1", "true", "yes"}:
        return
    try:
        import boto3
    except ImportError:
        return

    namespace = os.getenv("CLOUDWATCH_NAMESPACE", "Rytera/InsureFlow")
    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    metric: dict[str, Any] = {
        "MetricName": name,
        "Value": value,
        "Unit": unit,
    }
    if dimensions:
        metric["Dimensions"] = [{"Name": k, "Value": v} for k, v in dimensions.items()]
    try:
        boto3.client("cloudwatch", region_name=region).put_metric_data(
            Namespace=namespace,
            MetricData=[metric],
        )
    except Exception:
        logging.getLogger(__name__).debug("CloudWatch metric emit failed", exc_info=True)
