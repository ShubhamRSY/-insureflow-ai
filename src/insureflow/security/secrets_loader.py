"""Load secrets from AWS Secrets Manager when BANK_MODE / AWS is enabled."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def load_secrets_from_aws(secret_id: str | None = None) -> dict[str, str]:
    """Fetch a JSON secret and inject missing keys into os.environ.

    No-op when AWS_SECRETS_ARN / AWS_SECRET_ID is unset or boto3 is missing.
    """
    secret_id = secret_id or os.getenv("AWS_SECRETS_ARN") or os.getenv("AWS_SECRET_ID")
    if not secret_id:
        return {}

    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not installed — cannot load AWS Secrets Manager secret %s", secret_id)
        return {}

    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    client = boto3.client("secretsmanager", region_name=region)
    resp = client.get_secret_value(SecretId=secret_id)
    raw = resp.get("SecretString") or ""
    if not raw:
        return {}

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("AWS secret %s is not valid JSON", secret_id)
        return {}

    injected: dict[str, str] = {}
    for key, value in data.items():
        if value is None:
            continue
        text = str(value)
        if key not in os.environ or not os.environ.get(key):
            os.environ[key] = text
            injected[key] = "***"
    logger.info("Loaded %d keys from AWS Secrets Manager (%s)", len(injected), secret_id)
    return injected
