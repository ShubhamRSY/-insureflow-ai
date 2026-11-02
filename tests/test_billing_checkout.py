"""Tests for paid-plan checkout: pending plans, card validation, event monitoring."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _make_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BANK_MODE", "false")
    monkeypatch.setenv("ALLOW_OPEN_REGISTRATION", "true")
    monkeypatch.setenv("INSUREFLOW_AUTH_TESTING", "1")
    from insureflow.api import main as _main

    _main.limiter.enabled = False
    from insureflow.api.main import app

    return TestClient(app, raise_server_exceptions=False)


def _unique(prefix: str = "u") -> str:
    return f"{prefix}_{int(time.time() * 1000) % 100000}"


def _signup_free(client: TestClient) -> dict[str, Any]:
    uname = _unique("chk")
    resp = client.post(
        "/auth/signup",
        json={
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "StrongPass1!",
            "company_name": f"{uname} Corp",
            "plan": "free",
        },
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


def _auth(data: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {data['token']}"}


def _point_events_at(monkeypatch: pytest.MonkeyPatch, path) -> None:
    from insureflow.billing import events as billing_events

    monkeypatch.setattr(billing_events, "_event_log", billing_events.BillingEventLog(path=path))


class TestCheckoutFlow:
    def test_paid_signup_stays_pending_until_checkout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        uname = _unique("pend")
        resp = client.post(
            "/auth/signup",
            json={
                "username": uname,
                "email": f"{uname}@example.com",
                "password": "StrongPass1!",
                "company_name": "Pending Corp",
                "plan": "starter",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["plan"] == "starter"
        assert body["checkout_required"] is True
        assert body["plan_status"] == "checkout_required"

        usage = client.get("/pricing/usage", headers=_auth(body))
        assert usage.status_code == 200
        assert usage.json()["tier"] == "free"

    def test_checkout_completes_and_activates_plan(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        client = _make_client(monkeypatch)
        _point_events_at(monkeypatch, tmp_path / "events.jsonl")
        account = _signup_free(client)
        headers = _auth(account)

        start = client.post("/pricing/checkout", json={"tier": "pro"}, headers=headers)
        assert start.status_code == 201, start.text
        checkout = start.json()
        assert checkout["amount_due"] == 999.0
        assert checkout["status"] == "pending"

        confirm = client.post(
            f"/pricing/checkout/{checkout['checkout_id']}/confirm",
            json={
                "card_number": "4242424242424242",
                "card_exp": "12/30",
                "card_cvc": "123",
                "card_name": "Jane Buyer",
                "billing_zip": "78701",
            },
            headers=headers,
        )
        assert confirm.status_code == 200, confirm.text
        assert confirm.json()["plan_status"] == "active"
        assert confirm.json()["card_last4"] == "4242"

        usage = client.get("/pricing/usage", headers=headers)
        assert usage.json()["tier"] == "pro"

        events = client.get("/pricing/events", headers=headers).json()
        assert events["summary"]["checkouts_started"] == 1
        assert events["summary"]["checkouts_completed"] == 1
        assert events["summary"]["monthly_recurring_usd"] == 999.0
        assert events["summary"]["checkout_conversion"] == 1.0

    def test_invalid_card_is_rejected_and_logged(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        client = _make_client(monkeypatch)
        _point_events_at(monkeypatch, tmp_path / "events.jsonl")
        account = _signup_free(client)
        headers = _auth(account)

        checkout = client.post("/pricing/checkout", json={"tier": "starter"}, headers=headers).json()
        bad = client.post(
            f"/pricing/checkout/{checkout['checkout_id']}/confirm",
            json={"card_number": "1234", "card_exp": "12/30", "card_cvc": "12", "card_name": "X"},
            headers=headers,
        )
        assert bad.status_code == 400
        assert "Card number" in bad.json()["detail"]

        usage = client.get("/pricing/usage", headers=headers).json()
        assert usage["tier"] == "free"

        events = client.get("/pricing/events", headers=headers).json()
        assert events["summary"]["checkouts_failed"] == 1

    def test_expired_card_is_rejected(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        client = _make_client(monkeypatch)
        _point_events_at(monkeypatch, tmp_path / "events.jsonl")
        account = _signup_free(client)
        headers = _auth(account)

        checkout = client.post("/pricing/checkout", json={"tier": "pro"}, headers=headers).json()
        bad = client.post(
            f"/pricing/checkout/{checkout['checkout_id']}/confirm",
            json={"card_number": "4242424242424242", "card_exp": "01/20", "card_cvc": "123", "card_name": "X"},
            headers=headers,
        )
        assert bad.status_code == 400
        assert "expired" in bad.json()["detail"].lower()

    def test_free_plan_cannot_start_checkout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        account = _signup_free(client)
        resp = client.post("/pricing/checkout", json={"tier": "free"}, headers=_auth(account))
        assert resp.status_code == 400

    def test_checkout_requires_admin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        resp = client.post("/pricing/checkout", json={"tier": "pro"})
        assert resp.status_code in (401, 403)

    def test_cancel_reverts_to_free(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        client = _make_client(monkeypatch)
        _point_events_at(monkeypatch, tmp_path / "events.jsonl")
        account = _signup_free(client)
        headers = _auth(account)

        checkout = client.post("/pricing/checkout", json={"tier": "starter"}, headers=headers).json()
        cancel = client.post(f"/pricing/checkout/{checkout['checkout_id']}/cancel", headers=headers)
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        usage = client.get("/pricing/usage", headers=headers).json()
        assert usage["tier"] == "free"

        events = client.get("/pricing/events", headers=headers).json()
        assert events["summary"]["checkouts_cancelled"] == 1


class TestCheckoutIdempotency:
    def test_repeat_start_reuses_open_session(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        """Double-clicking 'Continue to payment' must not mint a second session."""
        client = _make_client(monkeypatch)
        _point_events_at(monkeypatch, tmp_path / "events.jsonl")
        account = _signup_free(client)
        headers = _auth(account)

        first = client.post("/pricing/checkout", json={"tier": "pro"}, headers=headers)
        assert first.status_code == 201
        second = client.post("/pricing/checkout", json={"tier": "pro"}, headers=headers)
        assert second.status_code == 200
        assert second.json()["checkout_id"] == first.json()["checkout_id"]
        assert second.json()["reused"] is True

        events = client.get("/pricing/events", headers=headers).json()
        assert events["summary"]["checkouts_started"] == 1

    def test_second_confirm_is_rejected(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        client = _make_client(monkeypatch)
        _point_events_at(monkeypatch, tmp_path / "events.jsonl")
        account = _signup_free(client)
        headers = _auth(account)

        checkout = client.post("/pricing/checkout", json={"tier": "pro"}, headers=headers).json()
        card = {
            "card_number": "4242424242424242",
            "card_exp": "12/30",
            "card_cvc": "123",
            "card_name": "Jane Buyer",
            "billing_zip": "78701",
        }
        first = client.post(f"/pricing/checkout/{checkout['checkout_id']}/confirm", json=card, headers=headers)
        assert first.status_code == 200
        second = client.post(f"/pricing/checkout/{checkout['checkout_id']}/confirm", json=card, headers=headers)
        assert second.status_code == 409

        events = client.get("/pricing/events", headers=headers).json()
        assert events["summary"]["checkouts_completed"] == 1

    def test_second_cancel_is_rejected(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        client = _make_client(monkeypatch)
        _point_events_at(monkeypatch, tmp_path / "events.jsonl")
        account = _signup_free(client)
        headers = _auth(account)

        checkout = client.post("/pricing/checkout", json={"tier": "starter"}, headers=headers).json()
        assert client.post(f"/pricing/checkout/{checkout['checkout_id']}/cancel", headers=headers).status_code == 200
        assert client.post(f"/pricing/checkout/{checkout['checkout_id']}/cancel", headers=headers).status_code == 409

        events = client.get("/pricing/events", headers=headers).json()
        assert events["summary"]["checkouts_cancelled"] == 1

    def test_cancelling_stale_session_keeps_paid_plan(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        """A leftover pending session must not reset a plan that was already paid for."""
        client = _make_client(monkeypatch)
        _point_events_at(monkeypatch, tmp_path / "events.jsonl")
        account = _signup_free(client)
        headers = _auth(account)

        starter = client.post("/pricing/checkout", json={"tier": "starter"}, headers=headers).json()
        # Switching plans supersedes the open starter session.
        pro = client.post("/pricing/checkout", json={"tier": "pro"}, headers=headers).json()
        client.post(
            f"/pricing/checkout/{pro['checkout_id']}/confirm",
            json={
                "card_number": "4242424242424242",
                "card_exp": "12/30",
                "card_cvc": "123",
                "card_name": "Jane Buyer",
                "billing_zip": "78701",
            },
            headers=headers,
        )
        # The abandoned starter session is already closed; the paid plan survives.
        assert client.post(f"/pricing/checkout/{starter['checkout_id']}/cancel", headers=headers).status_code == 409
        usage = client.get("/pricing/usage", headers=headers).json()
        assert usage["tier"] == "pro"


class TestPlanCatalog:
    def test_plans_mark_paid_tiers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        account = _signup_free(client)
        plans = client.get("/pricing/plans", headers=_auth(account)).json()["plans"]
        assert plans["free"]["is_paid"] is False
        assert plans["starter"]["is_paid"] is True
        assert plans["pro"]["is_paid"] is True
        assert plans["enterprise"]["is_paid"] is True
        assert plans["pro"]["checkout_required"] is True
