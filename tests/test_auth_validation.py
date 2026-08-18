from __future__ import annotations

import pytest

from insureflow.auth.validation import (
    validate_company_email,
    validate_registration,
)


def test_validate_company_email_accepts_ryterainc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REGISTRATION_EMAIL_DOMAINS", raising=False)
    result = validate_company_email("shubham@ryterainc.com")
    assert result.valid is True


def test_validate_company_email_rejects_personal_domains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REGISTRATION_EMAIL_DOMAINS", raising=False)
    result = validate_company_email("user@gmail.com")
    assert result.valid is False
    assert "company email" in result.errors[0].lower()


def test_validate_registration_enforces_company_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REGISTRATION_EMAIL_DOMAINS", raising=False)
    result = validate_registration(
        username="newuser",
        email="user@gmail.com",
        password="ValidPass1!",
        company_name="Acme Insurance",
    )
    assert result.valid is False
    assert any("company email" in err.lower() for err in result.errors)


def test_validate_company_email_respects_custom_domains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGISTRATION_EMAIL_DOMAINS", "carrier.com,ryterainc.com")
    assert validate_company_email("uw@carrier.com").valid is True
    assert validate_company_email("uw@gmail.com").valid is False


def test_validate_company_email_skips_domain_check_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGISTRATION_EMAIL_DOMAINS", "")
    assert validate_company_email("anyone@example.com").valid is True
