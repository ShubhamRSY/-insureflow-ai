from __future__ import annotations

from insureflow.config import settings
from insureflow.integrations.http_client import IntegrationHTTPClient


def resolve_integration_mode(mode: str, http: IntegrationHTTPClient) -> str:
    normalized = (mode or "auto").lower()
    if normalized == "simulated":
        return "simulated"
    if not http.configured:
        return "misconfigured" if normalized == "live" else "simulated"
    if normalized in ("live", "auto"):
        return "live"
    return "simulated"


def build_oracle_http(api_key: str, base_url: str) -> IntegrationHTTPClient:
    return IntegrationHTTPClient(
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=settings.integration_timeout_seconds,
        max_retries=settings.integration_max_retries,
    )
