from __future__ import annotations

import os
import re
from dataclasses import dataclass

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,50}$")
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_PASSWORD_SPECIAL_RE = re.compile(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\;'/`~]")


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]


def validate_username(username: str) -> ValidationResult:
    errors: list[str] = []
    username = username.strip()
    if not username:
        errors.append("Username is required")
    elif len(username) < 3:
        errors.append("Username must be at least 3 characters")
    elif len(username) > 50:
        errors.append("Username must be at most 50 characters")
    elif not _USERNAME_RE.match(username):
        errors.append("Username may only contain letters, digits, dots, hyphens, and underscores")
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_email(email: str) -> ValidationResult:
    errors: list[str] = []
    email = email.strip()
    if not email:
        errors.append("Email is required")
    elif not _EMAIL_RE.match(email):
        errors.append("Invalid email format")
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def registration_email_domains() -> list[str]:
    raw = os.getenv("REGISTRATION_EMAIL_DOMAINS", "")
    return [part.strip().lower().lstrip("@") for part in raw.split(",") if part.strip()]


def validate_company_email(email: str) -> ValidationResult:
    """Self-registration must use an approved company email domain."""
    base = validate_email(email)
    if not base.valid:
        return base
    allowed = registration_email_domains()
    if not allowed:
        return ValidationResult(valid=True, errors=[])
    domain = email.strip().rsplit("@", 1)[-1].lower()
    if domain not in allowed:
        allowed_label = ", ".join(f"@{d}" for d in allowed)
        errors = [f"Registration requires a company email ({allowed_label})"]
        return ValidationResult(valid=False, errors=errors)
    return ValidationResult(valid=True, errors=[])


def validate_password(password: str, min_length: int = 8) -> ValidationResult:
    errors: list[str] = []
    if not password:
        errors.append("Password is required")
    else:
        if len(password) < min_length:
            errors.append(f"Password must be at least {min_length} characters")
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", password):
            errors.append("Password must contain at least one digit")
        if not _PASSWORD_SPECIAL_RE.search(password):
            errors.append("Password must contain at least one special character (!@#$%^&* etc.)")
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_company_name(name: str) -> ValidationResult:
    errors: list[str] = []
    name = name.strip()
    if not name:
        errors.append("Company name is required")
    elif len(name) < 2:
        errors.append("Company name must be at least 2 characters")
    elif len(name) > 255:
        errors.append("Company name must be at most 255 characters")
    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_registration(
    username: str,
    email: str,
    password: str,
    company_name: str,
    min_password_length: int = 8,
) -> ValidationResult:
    all_errors: list[str] = []
    for result in [
        validate_username(username),
        validate_email(email),
        validate_company_email(email),
        validate_password(password, min_length=min_password_length),
        validate_company_name(company_name),
    ]:
        all_errors.extend(result.errors)
    return ValidationResult(valid=len(all_errors) == 0, errors=all_errors)
