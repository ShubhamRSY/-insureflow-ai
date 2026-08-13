"""ASGI middleware: Prometheus HTTP metrics + request timing."""

from __future__ import annotations

import time
from typing import Any, Callable

from insureflow.observability.prometheus_metrics import observe_http

_SKIP_PREFIXES = ("/metrics", "/favicon.ico")


class PrometheusHTTPMiddleware:
    def __init__(self, app: Callable[..., Any]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path") or "/")
        method = str(scope.get("method") or "GET")
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_box = {"code": 500}

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                status_box["code"] = int(message.get("status") or 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            observe_http(method, path, status_box["code"], time.perf_counter() - start)
