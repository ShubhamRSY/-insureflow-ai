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
    posture = resolve_security_posture()
    errors = validate_startup_secrets(
        secret_key="a" * 32,
        encryption_key="fernet-or-derived-key-value",
        posture=posture,
    )
    assert errors == []


def test_dev_posture_allows_open_registration(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("BANK_MODE", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ALLOW_OPEN_REGISTRATION", raising=False)
    posture = resolve_security_posture()
    assert posture.bank_mode is False
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
