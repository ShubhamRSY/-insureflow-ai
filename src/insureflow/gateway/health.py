from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from insureflow.config import settings

_BUNDLED_PREFIX = "/integrations/"


def bundled_gateway_health(base_url: str, api_key: str) -> dict[str, Any] | None:
    """In-process health for URLs routed to the bundled /integrations gateway."""
    path = urlparse(base_url).path
    if _BUNDLED_PREFIX not in path:
        return None
    expected = (settings.integration_gateway_api_key or "").strip()
    if expected and api_key.strip() != expected:
        return {"reachable": False, "mode": "misconfigured", "error": "invalid gateway API key"}
    service = path.split(_BUNDLED_PREFIX, 1)[-1].split("/")[0:3]
    return {
        "reachable": True,
        "mode": "live",
        "path": "/health",
        "bundled": True,
        "service": "/".join(service) if service else "integrations",
    }
