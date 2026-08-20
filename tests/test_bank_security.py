"""Banking security posture, JWT secret resolution, WORM, SSO stubs."""

from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch

from insureflow.auth.jwt import create_access_token, decode_access_token
from insureflow.security.posture import resolve_security_posture, validate_startup_secrets


def test_jwt_uses_env_secret_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-at-least-32-chars!!")
    token = create_access_token({"sub": "alice", "role": "admin", "org_id": "bank-a"})
    data = decode_access_token(token)
    assert data is not None
    assert data.username == "alice"
    assert data.org_id == "bank-a"
    # Wrong secret must fail
    assert decode_access_token(token, secret_key="other-secret-key-xxxxxxxxxxxxxxx") is None


def test_bank_mode_posture_locks_registration_and_reset(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.delenv("ALLOW_OPEN_REGISTRATION", raising=False)
    monkeypatch.delenv("ALLOW_AUTH_RESET", raising=False)
    posture = resolve_security_posture()
    assert posture.bank_mode is True
    assert posture.allow_open_registration is False
    assert posture.allow_auth_reset is False
    assert posture.require_encryption is True
    assert posture.min_password_length >= 12


def test_validate_startup_secrets_bank_requires_keys(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "true")
    posture = resolve_security_posture()
    errors = validate_startup_secrets(
        secret_key="CHANGE_ME_TO_A_LONG_SECRET_KEY_IN_PRODUCTION",
        encryption_key="",
        posture=posture,
    )
    assert len(errors) >= 2


def test_validate_startup_secrets_ok_when_strong(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.setenv("ALLOW_OPEN_REGISTRATION", "false")
    monkeypatch.setenv("ALLOW_AUTH_RESET", "false")
    monkeypatch.setenv("INTEGRATION_GATEWAY_API_KEY", "prod-gateway-key-not-the-dev-placeholder-xx")
    monkeypatch.setenv("JOB_STORE_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    for key in (
        "CLUE_API_KEY",
        "APLUS_API_KEY",
        "NCCI_API_KEY",
        "CAT_API_KEY",
        "GUIDEWIRE_API_KEY",
        "BRITECORE_API_KEY",
        "ISO_RATING_API_KEY",
    ):
        monkeypatch.setenv(key, "prod-vendor-key-xxxxxxxxxxxxxxxxxxxx")
    posture = resolve_security_posture()
    errors = validate_startup_secrets(
        secret_key="a" * 32,
        encryption_key="fernet-or-derived-key-value",
        posture=posture,
    )
    assert errors == []


def test_validate_startup_rejects_dev_gateway_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.setenv("ALLOW_OPEN_REGISTRATION", "false")
    monkeypatch.setenv("ALLOW_AUTH_RESET", "false")
    monkeypatch.setenv("INTEGRATION_GATEWAY_API_KEY", "rytera-dev-gateway-key-change-in-production")
    monkeypatch.setenv("JOB_STORE_BACKEND", "redis")
    posture = resolve_security_posture()
    errors = validate_startup_secrets(
        secret_key="a" * 32,
        encryption_key="fernet-or-derived-key-value",
        posture=posture,
    )
    assert any("INTEGRATION_GATEWAY_API_KEY" in e for e in errors)


def test_dev_posture_defaults_open_registration(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ALLOW_OPEN_REGISTRATION", raising=False)
    posture = resolve_security_posture()
    assert posture.bank_mode is False
    assert posture.allow_open_registration is True


def test_dev_posture_can_opt_in_open_registration(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_OPEN_REGISTRATION", "true")
    posture = resolve_security_posture()
    assert posture.allow_open_registration is True


def test_worm_seal_and_verify(tmp_path: Path) -> None:
    from insureflow.audit.worm import WormAuditStore

    store = WormAuditStore(base_path=tmp_path / "worm", retention_days=2555)
    record = store.seal("org-1", "bundle-abc", {"decision": "ACCEPT", "premium": 1000})
    assert record["sealed"] is True
    assert Path(record["path"]).exists()
    assert store.verify(record["path"]) is True
    # Immutability: same path collision uses unique timestamp+hash filenames — sealing again OK
    record2 = store.seal("org-1", "bundle-abc", {"decision": "ACCEPT", "premium": 1000})
    assert record2["path"] != record["path"]


def test_sso_status_disabled_by_default(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SSO_ENABLED", raising=False)
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("COGNITO_DOMAIN", raising=False)
    monkeypatch.delenv("OKTA_DOMAIN", raising=False)
    from insureflow.auth.sso import sso_status

    assert sso_status()["enabled"] is False


def test_cloudwatch_formatter_json() -> None:
    import logging

    from insureflow.observability.cloudwatch import CloudWatchJsonFormatter

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello bank",
        args=(),
        exc_info=None,
    )
    payload = json.loads(CloudWatchJsonFormatter().format(record))
    assert payload["message"] == "hello bank"
    assert payload["level"] == "INFO"


def test_auth_reset_blocked_in_bank_mode(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.setenv("ALLOW_AUTH_RESET", "false")
    from insureflow.security.posture import resolve_security_posture

    posture = resolve_security_posture()
    assert posture.allow_auth_reset is False


def test_hardened_ops_endpoints_require_auth(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.delenv("METRICS_BEARER", raising=False)
    from fastapi.testclient import TestClient

    from insureflow.api import app

    client = TestClient(app)
    assert client.get("/system/diagnostics").status_code == 401
    assert client.get("/security/status").status_code == 401
    assert client.get("/metrics").status_code == 401
    assert client.get("/health").status_code == 200


def test_sso_required_off_by_default(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SSO_REQUIRED", raising=False)
    from insureflow.auth.sso import sso_required

    assert sso_required() is False


def test_pkce_s256_rfc7636() -> None:
    from insureflow.auth.sso import _code_challenge

    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert _code_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_token_endpoint_okta_vs_cognito(monkeypatch: MonkeyPatch) -> None:
    from insureflow.auth.sso import OIDCConfig, _token_endpoint

    monkeypatch.setattr("insureflow.auth.sso._openid_config", lambda _issuer: {})
    monkeypatch.setenv("OKTA_DOMAIN", "bank.okta.com")
    monkeypatch.delenv("COGNITO_DOMAIN", raising=False)
    okta = OIDCConfig(
        enabled=True,
        provider="okta",
        issuer="https://bank.okta.com",
        client_id="cid",
        client_secret="",
        redirect_uri="https://app.example/cb",
    )
    assert _token_endpoint(okta) == "https://bank.okta.com/oauth2/v1/token"

    custom = OIDCConfig(
        enabled=True,
        provider="okta",
        issuer="https://bank.okta.com/oauth2/default",
        client_id="cid",
        client_secret="",
        redirect_uri="https://app.example/cb",
    )
    assert _token_endpoint(custom) == "https://bank.okta.com/oauth2/default/v1/token"

    monkeypatch.delenv("OKTA_DOMAIN", raising=False)
    monkeypatch.setenv("COGNITO_DOMAIN", "myapp.auth.us-east-1.amazoncognito.com")
    cognito = OIDCConfig(
        enabled=True,
        provider="cognito",
        issuer="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xx",
        client_id="cid",
        client_secret="",
        redirect_uri="https://app.example/cb",
    )
    assert _token_endpoint(cognito) == "https://myapp.auth.us-east-1.amazoncognito.com/oauth2/token"


def test_start_authorization_keeps_verifier_server_side(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SSO_ENABLED", "true")
    monkeypatch.setenv("SSO_PROVIDER", "okta")
    monkeypatch.setenv("OIDC_ISSUER", "https://bank.okta.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "cid")
    monkeypatch.setenv("OKTA_DOMAIN", "bank.okta.com")
    monkeypatch.setattr("insureflow.auth.sso._openid_config", lambda _issuer: {})
    from insureflow.auth.sso import start_authorization

    out = start_authorization()
    assert "code_verifier" not in out
    assert "authorize_url" in out and "state" in out
    assert "code_challenge=" in out["authorize_url"]
    assert "code_challenge_method=S256" in out["authorize_url"]


def test_password_login_blocked_when_sso_required(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SSO_REQUIRED", "true")
    from fastapi.testclient import TestClient

    from insureflow.api import app

    client = TestClient(app)
    resp = client.post("/auth/login", json={"username": "alice", "password": "secret"})
    assert resp.status_code == 403
    assert "SSO" in resp.json()["detail"]


def test_auth_status_includes_sso_flags() -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app

    client = TestClient(app)
    resp = client.get("/auth/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "sso" in body
    assert "sso_required" in body
    assert body["sso_required"] is False


def test_sso_callback_get_redirects_to_spa() -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app

    client = TestClient(app, follow_redirects=False)
    resp = client.get("/auth/sso/callback?code=abc&state=xyz")
    assert resp.status_code in {302, 307}
    loc = resp.headers.get("location") or ""
    assert "/dashboard/sso/callback" in loc
    assert "code=abc" in loc
    assert "state=xyz" in loc


def test_billing_usage_requires_auth() -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app

    client = TestClient(app)
    assert client.get("/billing/usage").status_code == 401


def test_ingestion_status_requires_auth() -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app

    client = TestClient(app)
    assert client.get("/ingestion/status").status_code == 401


def test_platform_stack_requires_auth() -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app

    client = TestClient(app)
    assert client.get("/platform/stack").status_code == 401


def test_security_headers_on_health() -> None:
    from fastapi.testclient import TestClient

    from insureflow.api import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "no-referrer"
    assert "camera=()" in (resp.headers.get("permissions-policy") or "")
    https = client.get("/health", headers={"x-forwarded-proto": "https"})
    assert "max-age=" in (https.headers.get("strict-transport-security") or "")


def test_signed_in_users_can_run_demo_presets_in_production(monkeypatch: MonkeyPatch) -> None:
    from insureflow.security.posture import allow_demo_presets

    monkeypatch.setenv("BANK_MODE", "true")
    monkeypatch.delenv("ALLOW_DEMO_PRESETS", raising=False)
    assert allow_demo_presets(signed_in=True) is True
    assert allow_demo_presets(signed_in=False) is False


def test_allow_demo_presets_explicit_off(monkeypatch: MonkeyPatch) -> None:
    from insureflow.security.posture import allow_demo_presets

    monkeypatch.setenv("ALLOW_DEMO_PRESETS", "false")
    assert allow_demo_presets(signed_in=True) is False
