"""Regression test: POST /documents/presign must be rate-limited.

Presigning itself never touches S3 (it's a local signing operation), so
nothing stopped a caller from hammering it indefinitely before this limit
existed — cheap per-call, but technically unbounded resource use.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


def _make_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BANK_MODE", "false")
    monkeypatch.setenv("ALLOW_OPEN_REGISTRATION", "true")
    monkeypatch.setenv("INSUREFLOW_AUTH_TESTING", "1")
    from insureflow.api import main as _main

    # Unlike most tests, we deliberately leave the limiter ENABLED here —
    # that's the exact behavior under test.
    _main.limiter.enabled = True
    _main.limiter.reset()
    from insureflow.api.main import app

    return TestClient(app, raise_server_exceptions=False)


def _unique(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000) % 100000}"


def test_presign_endpoint_enforces_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch)
    uname = _unique("ratelimit")
    resp = client.post(
        "/auth/signup",
        json={
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "StrongPass1!",
            "company_name": "Rate Limit Co",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    bundle_resp = client.post("/pipeline/bundles", json={"name": "rl-bundle"}, headers=headers)
    assert bundle_resp.status_code == 201
    bundle_id = bundle_resp.json()["bundle_id"]

    statuses = []
    for i in range(22):
        resp = client.post(
            f"/pipeline/bundles/{bundle_id}/documents/presign",
            json={"filename": f"file{i}.pdf"},
            headers=headers,
        )
        statuses.append(resp.status_code)

    # The endpoint's limit is 20/minute — the first 20 calls should succeed
    # (or fail for an unrelated reason like "not configured", never 429), and
    # at least one of the last two must be throttled.
    assert 429 in statuses, f"expected rate limiting to kick in, got: {statuses}"
    assert statuses.count(429) <= 2
