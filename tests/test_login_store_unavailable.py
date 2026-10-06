"""Login must say the account database is down, not "Invalid credentials"."""

from __future__ import annotations

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from insureflow.auth import db, store


def test_pg_store_unavailable_only_when_configured_and_down(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("INSUREFLOW_AUTH_TEST_PG_ALLOW", "1")
    monkeypatch.setattr(store, "_init_pg_store", lambda: None)

    monkeypatch.setattr(db, "_build_database_url", lambda: "")
    assert not store.pg_store_unavailable()  # no Postgres configured: file store is the real store

    monkeypatch.setattr(db, "_build_database_url", lambda: "postgresql://x@localhost:1/x")
    assert store.pg_store_unavailable()


def test_login_returns_503_when_account_db_unreachable(monkeypatch: MonkeyPatch) -> None:
    from insureflow.api import app, main

    monkeypatch.setattr(main, "pg_store_unavailable", lambda: True)
    resp = TestClient(app).post("/auth/login", json={"username": "Shubham", "password": "whatever"})
    assert resp.status_code == 503
    assert "account database" in resp.json()["detail"]
