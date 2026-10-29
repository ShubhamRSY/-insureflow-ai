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


def test_validate_company_email_rejects_personal_domains_when_restricted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGISTRATION_EMAIL_DOMAINS", "ryterainc.com")
    result = validate_company_email("user@gmail.com")
    assert result.valid is False
    assert "company email" in result.errors[0].lower()


def test_validate_registration_enforces_company_email_when_restricted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGISTRATION_EMAIL_DOMAINS", "ryterainc.com")
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


def test_validate_registration_reports_each_error_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REGISTRATION_EMAIL_DOMAINS", raising=False)
    result = validate_registration(
        username="not an email@example.com",
        email="not-an-email",
        password="ValidPass1!",
        company_name="Acme Insurance",
    )
    assert result.valid is False
    assert result.errors.count("Invalid email format") == 1
    assert any("Username may only contain" in err for err in result.errors)


@pytest.mark.parametrize(
    "email",
    ["a@gmail.com", "a@GMAIL.com", "a@yahoo.co.in", "a@hotmail.fr", "a@outlook.com", "a@icloud.com", "a@proton.me", "a@mailinator.com"],
)
def test_personal_email_always_rejected(monkeypatch: pytest.MonkeyPatch, email: str) -> None:
    monkeypatch.delenv("REGISTRATION_EMAIL_DOMAINS", raising=False)
    result = validate_company_email(email)
    assert result.valid is False
    assert "company email" in result.errors[0].lower()


@pytest.mark.parametrize("email", ["uw@acme-insurance.com", "a@livewire.io", "a@gmailer.co", "a@ryterainc.com"])
def test_company_email_accepted(monkeypatch: pytest.MonkeyPatch, email: str) -> None:
    monkeypatch.delenv("REGISTRATION_EMAIL_DOMAINS", raising=False)
    assert validate_company_email(email).valid is True
