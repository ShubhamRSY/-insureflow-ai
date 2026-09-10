"""Regression test: an unhandled exception must return the API's normal
JSON error shape, not Starlette's bare plain-text 500 — a client that
unconditionally parses response.json() would otherwise crash on top of
whatever the original bug was."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.routing import Route


def _make_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BANK_MODE", "false")
    monkeypatch.setenv("INSUREFLOW_AUTH_TESTING", "1")
    from insureflow.api import main as _main

    _main.limiter.enabled = False
    from insureflow.api.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_unhandled_exception_returns_json_not_plaintext(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)

    def _crash(request: object) -> None:
        raise ValueError("simulated unexpected bug")

    client.app.router.routes.insert(0, Route("/__test_unhandled_crash__", _crash))  # type: ignore[attr-defined]

    resp = client.get("/__test_unhandled_crash__")
    assert resp.status_code == 500
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert body["detail"] == "Internal server error"
    assert "error_id" in body
    # Never echo the actual exception message back to the caller.
    assert "simulated unexpected bug" not in resp.text


def test_http_exception_is_unaffected_by_the_catchall(monkeypatch: pytest.MonkeyPatch) -> None:
    """The catch-all must never shadow a deliberate, specific HTTPException —
    FastAPI/Starlette should always prefer the more specific handler."""
    client = _make_client(monkeypatch)

    def _explicit_404(request: object) -> None:
        raise HTTPException(status_code=404, detail="Explicit not found")

    client.app.router.routes.insert(0, Route("/__test_http_exception__", _explicit_404))  # type: ignore[attr-defined]

    resp = client.get("/__test_http_exception__")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Explicit not found"
