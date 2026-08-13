from __future__ import annotations

from insureflow.config import settings
from insureflow.integrations.http_client import IntegrationHTTPClient

_GATEWAY_URL_MARKERS = (
    "integrations.rytera.ai",
    "127.0.0.1:8002",
    "localhost:8002",
    "[::1]:8002",
)
_GATEWAY_KEY_MARKERS = (
    "rytera-dev-gateway-key",
    "rytera-dev-gateway",
)


def is_bundled_gateway_url(url: str, api_key: str = "") -> bool:
    """True when the endpoint is Rytera's synthetic gateway, not a vendor/PAS sandbox."""
    key = (api_key or "").strip().lower()
    if any(m in key for m in _GATEWAY_KEY_MARKERS):
        return True
    blob = (url or "").strip().lower()
    return any(m in blob for m in _GATEWAY_URL_MARKERS)


def resolve_integration_mode(mode: str, http: IntegrationHTTPClient) -> str:
    normalized = (mode or "auto").lower()
    if normalized == "simulated":
        return "simulated"
    if is_bundled_gateway_url(getattr(http, "base_url", ""), getattr(http, "api_key", "")):
        return "gateway_synthetic"
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
