from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class IntegrationHTTPError(Exception):
    def __init__(self, message: str, status_code: int = 0, body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


@dataclass
class HTTPResponse:
    status_code: int
    data: dict[str, Any] | list[Any] | str
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json_dict(self) -> dict[str, Any]:
        if isinstance(self.data, dict):
            return self.data
        if isinstance(self.data, list):
            return {"items": self.data}
        if isinstance(self.data, str):
            try:
                parsed = json.loads(self.data)
                return parsed if isinstance(parsed, dict) else {"items": parsed}
            except json.JSONDecodeError:
                return {"raw": self.data}
        return {}


class IntegrationHTTPClient:
    """Production HTTP client for carrier integrations (stdlib, retries, timeouts)."""

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "",
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer ",
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix
        self.extra_headers = extra_headers or {}

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json", **self.extra_headers}
        if self.api_key:
            headers[self.auth_header] = f"{self.auth_prefix}{self.api_key}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
    ) -> HTTPResponse:
        if not self.base_url:
            raise IntegrationHTTPError("Integration base URL not configured")

        url = f"{self.base_url}/{path.lstrip('/')}"
        if query:
            params = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in query.items() if v is not None)
            if params:
                url = f"{url}?{params}"

        payload = None
        if json_body is not None:
            payload = json.dumps(json_body).encode("utf-8")

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            req = urllib.request.Request(url, data=payload, headers=self._headers(), method=method.upper())
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                    parsed: dict[str, Any] | list[Any] | str
                    if raw:
                        try:
                            parsed = json.loads(raw)
                        except json.JSONDecodeError:
                            parsed = raw
                    else:
                        parsed = {}
                    return HTTPResponse(status_code=resp.status, data=parsed, headers=dict(resp.headers))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
                if exc.code in (429, 502, 503, 504) and attempt < self.max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    last_error = IntegrationHTTPError(f"HTTP {exc.code}", exc.code, body)
                    continue
                raise IntegrationHTTPError(f"HTTP {exc.code}: {body[:300]}", exc.code, body) from exc
            except urllib.error.URLError as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise IntegrationHTTPError(f"Connection failed: {exc.reason}") from exc

        raise IntegrationHTTPError(str(last_error or "Request failed"))

    def get(self, path: str, *, query: dict[str, str] | None = None) -> HTTPResponse:
        return self.request("GET", path, query=query)

    def post(self, path: str, json_body: dict[str, Any]) -> HTTPResponse:
        return self.request("POST", path, json_body=json_body)

    def health_check(self, paths: tuple[str, ...] = ("/health", "/status", "/")) -> dict[str, Any]:
        if not self.configured:
            return {"reachable": False, "mode": "misconfigured", "error": "API key or base URL missing"}
        for path in paths:
            try:
                resp = self.get(path)
                if resp.ok:
                    return {"reachable": True, "mode": "live", "path": path, "status_code": resp.status_code}
            except IntegrationHTTPError as exc:
                if exc.status_code in (401, 403):
                    return {"reachable": True, "mode": "live", "path": path, "status_code": exc.status_code, "note": "auth_required"}
                continue
        return {"reachable": False, "mode": "unreachable", "error": "Health check failed on all paths"}


def build_http_client(api_key: str, base_url: str, **kwargs: object) -> IntegrationHTTPClient:
    from insureflow.config import settings

    return IntegrationHTTPClient(
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=float(kwargs.get("timeout_seconds", settings.integration_timeout_seconds)),  # type: ignore[arg-type]
        max_retries=int(kwargs.get("max_retries", settings.integration_max_retries)),  # type: ignore[arg-type]
    )


# late import to avoid circular issues in typing only
import urllib.parse  # noqa: E402
