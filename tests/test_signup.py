"""Tests for self-serve signup flow: endpoint, plan alignment, dev-mode defaults."""

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

    # Bypass rate limiter in tests
    _main.limiter.enabled = False
    from insureflow.api.main import app

    return TestClient(app, raise_server_exceptions=False)


def _unique(prefix: str = "u") -> str:
    return f"{prefix}_{int(time.time() * 1000) % 100000}"


class TestSignupEndpoint:
    def test_signup_creates_user_org_and_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        uname = _unique("su1")
        resp = client.post(
            "/auth/signup",
            json={
                "username": uname,
                "email": f"{uname}@example.com",
                "password": "StrongPass1!",
                "company_name": "Test Corp",
                "plan": "free",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"].startswith("Account created")
        assert "token" in data
        assert data["org_id"]
        assert data["plan"] == "free"
        assert data["api_key"].startswith("ifly_")
        assert data["role"] == "admin"

    def test_signup_sets_plan_in_pricing_store(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        uname = _unique("plan")
        resp = client.post(
            "/auth/signup",
            json={
                "username": uname,
                "email": f"{uname}@example.com",
                "password": "StrongPass1!",
                "company_name": "Plan Corp",
                "plan": "starter",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["plan"] == "starter"

    def test_signup_returns_valid_jwt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        uname = _unique("jwt")
        resp = client.post(
            "/auth/signup",
            json={
                "username": uname,
                "email": f"{uname}@example.com",
                "password": "StrongPass1!",
                "company_name": "JWT Corp",
                "plan": "free",
            },
        )
        assert resp.status_code == 201
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["username"] == uname
        assert me.json()["role"] == "admin"

    def test_signup_rejects_duplicate_username(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        uname = _unique("dup")
        body = {
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "StrongPass1!",
            "company_name": "Dup Corp",
        }
        resp1 = client.post("/auth/signup", json=body)
        assert resp1.status_code == 201
        resp2 = client.post("/auth/signup", json=body)
        assert resp2.status_code == 409

    def test_signup_rejects_short_password(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        resp = client.post(
            "/auth/signup",
            json={
                "username": _unique("spw"),
                "email": "short@example.com",
                "password": "Ab1!",
                "company_name": "Short Corp",
            },
        )
        assert resp.status_code == 400

    def test_signup_rejects_missing_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        resp = client.post(
            "/auth/signup",
            json={
                "username": _unique("ne"),
                "email": "",
                "password": "StrongPass1!",
                "company_name": "No Email Corp",
            },
        )
        assert resp.status_code == 400

    def test_signup_rejects_missing_company_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        resp = client.post(
            "/auth/signup",
            json={
                "username": _unique("nc"),
                "email": "no@example.com",
                "password": "StrongPass1!",
                "company_name": "",
            },
        )
        assert resp.status_code == 400

    def test_signup_defaults_to_free_plan(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        uname = _unique("dfp")
        resp = client.post(
            "/auth/signup",
            json={
                "username": uname,
                "email": f"{uname}@example.com",
                "password": "StrongPass1!",
                "company_name": "Default Corp",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["plan"] == "free"

    def test_signup_blocked_when_registration_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BANK_MODE", "true")
        monkeypatch.setenv("ALLOW_OPEN_REGISTRATION", "false")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("INSUREFLOW_AUTH_TESTING", "1")
        from insureflow.api.main import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/auth/signup",
            json={
                "username": _unique("blk"),
                "email": "blocked@example.com",
                "password": "StrongPass1!",
                "company_name": "Blocked Corp",
            },
        )
        assert resp.status_code == 403

    def test_signup_allows_all_email_domains_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        uname = _unique("ae")
        resp = client.post(
            "/auth/signup",
            json={
                "username": uname,
                "email": f"{uname}@anydomain.com",
                "password": "StrongPass1!",
                "company_name": "Any Domain Corp",
            },
        )
        assert resp.status_code == 201

    def test_signup_with_enterprise_plan(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        uname = _unique("ent")
        resp = client.post(
            "/auth/signup",
            json={
                "username": uname,
                "email": f"{uname}@example.com",
                "password": "StrongPass1!",
                "company_name": "Enterprise Corp",
                "plan": "enterprise",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["plan"] == "enterprise"


class TestPlanAlignment:
    def test_free_maps_to_pilot(self) -> None:
        from insureflow.billing.plan import resolve_plan

        assert resolve_plan("free").plan_id == "pilot"

    def test_starter_maps_to_desk(self) -> None:
        from insureflow.billing.plan import resolve_plan

        assert resolve_plan("starter").plan_id == "desk"

    def test_pro_maps_to_book(self) -> None:
        from insureflow.billing.plan import resolve_plan

        assert resolve_plan("pro").plan_id == "book"

    def test_enterprise_stays_enterprise(self) -> None:
        from insureflow.billing.plan import resolve_plan

        assert resolve_plan("enterprise").plan_id == "enterprise"

    def test_explorer_maps_to_desk(self) -> None:
        from insureflow.billing.plan import resolve_plan

        assert resolve_plan("explorer").plan_id == "desk"

    def test_unknown_plan_defaults_to_pilot(self) -> None:
        from insureflow.billing.plan import resolve_plan

        assert resolve_plan("nonexistent").plan_id == "pilot"

    def test_pilot_allows_demo_rate_book(self) -> None:
        from insureflow.billing.plan import resolve_plan

        plan = resolve_plan("pilot")
        assert plan.allow_demo_rate_book is True
        assert plan.require_live_oracles is False

    def test_desk_requires_live_oracles(self) -> None:
        from insureflow.billing.plan import resolve_plan

        plan = resolve_plan("desk")
        assert plan.require_live_oracles is True
        assert plan.require_carrier_book is True

    def test_book_requires_live_pas(self) -> None:
        from insureflow.billing.plan import resolve_plan

        plan = resolve_plan("book")
        assert plan.require_live_pas is True
        assert plan.allow_simulated_pas is False


class TestDevModeDefaults:
    def test_dev_allows_open_registration(self) -> None:
        import os

        from insureflow.security.posture import resolve_security_posture

        old_env = {k: os.environ.get(k) for k in ("ENVIRONMENT", "BANK_MODE", "ALLOW_OPEN_REGISTRATION")}
        os.environ["ENVIRONMENT"] = "development"
        os.environ["BANK_MODE"] = "false"
        os.environ.pop("ALLOW_OPEN_REGISTRATION", None)
        try:
            posture = resolve_security_posture()
            assert posture.allow_open_registration is True
            assert posture.allow_auth_reset is True
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_bank_mode_blocks_open_registration(self) -> None:
        import os

        from insureflow.security.posture import resolve_security_posture

        old = {k: os.environ.get(k) for k in ("BANK_MODE", "ALLOW_OPEN_REGISTRATION")}
        os.environ["BANK_MODE"] = "true"
        os.environ.pop("ALLOW_OPEN_REGISTRATION", None)
        try:
            posture = resolve_security_posture()
            assert posture.allow_open_registration is False
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_email_domain_default_allows_all(self) -> None:
        import os

        from insureflow.auth.validation import validate_company_email

        old = os.environ.get("REGISTRATION_EMAIL_DOMAINS")
        os.environ.pop("REGISTRATION_EMAIL_DOMAINS", None)
        try:
            result = validate_company_email("anyone@anywhere.com")
            assert result.valid is True
        finally:
            if old is not None:
                os.environ["REGISTRATION_EMAIL_DOMAINS"] = old

    def test_email_domain_can_restrict(self) -> None:
        import os

        from insureflow.auth.validation import validate_company_email

        old = os.environ.get("REGISTRATION_EMAIL_DOMAINS")
        os.environ["REGISTRATION_EMAIL_DOMAINS"] = "acme.com"
        try:
            assert validate_company_email("user@acme.com").valid is True
            assert validate_company_email("user@gmail.com").valid is False
        finally:
            if old is not None:
                os.environ["REGISTRATION_EMAIL_DOMAINS"] = old
            else:
                os.environ.pop("REGISTRATION_EMAIL_DOMAINS", None)


class TestForgotPassword:
    def test_forgot_password_returns_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client(monkeypatch)
        resp = client.post(
            "/auth/forgot-password",
            json={
                "username": "nonexistent",
                "email": "nope@example.com",
            },
        )
        assert resp.status_code == 200
        assert "message" in resp.json()
