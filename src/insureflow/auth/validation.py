from __future__ import annotations

import os
import re
from dataclasses import dataclass

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 ._-]{2,49}$")
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
        errors.append("Username may only contain letters, digits, spaces, dots, hyphens, and underscores")
    elif "  " in username:
        errors.append("Username cannot contain multiple consecutive spaces")
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


# Personal and throwaway mailbox providers. Any TLD of the first group counts
# (yahoo.co.in, hotmail.fr, outlook.de, ...).
# ponytail: fixed list covers the big providers; swap for a maintained list if small ones slip through.
_PERSONAL_EMAIL_BRANDS = frozenset({"gmail", "googlemail", "yahoo", "ymail", "rocketmail", "hotmail", "outlook", "live", "msn", "aol"})
_PERSONAL_EMAIL_DOMAINS = frozenset(
    {
        "icloud.com", "me.com", "mac.com", "proton.me", "protonmail.com", "pm.me", "gmx.com", "gmx.net", "gmx.de",
        "mail.com", "yandex.com", "yandex.ru", "zoho.com", "zohomail.com", "qq.com", "163.com", "126.com",
        "rediffmail.com", "tutanota.com", "tuta.io", "fastmail.com", "hey.com", "web.de", "mail.ru", "inbox.com",
        "hushmail.com", "mailinator.com", "guerrillamail.com", "10minutemail.com", "temp-mail.org", "yopmail.com",
    }
)  # fmt: skip


def is_personal_email_domain(domain: str) -> bool:
    domain = domain.strip().lower()
    return domain in _PERSONAL_EMAIL_DOMAINS or domain.split(".", 1)[0] in _PERSONAL_EMAIL_BRANDS


def validate_company_email(email: str) -> ValidationResult:
    """Self-registration must use a company email: never a personal mailbox, and
    one of REGISTRATION_EMAIL_DOMAINS when that is set."""
    base = validate_email(email)
    if not base.valid:
        return base
    domain = email.strip().rsplit("@", 1)[-1].lower()
    if is_personal_email_domain(domain):
        return ValidationResult(
            valid=False,
            errors=[f"Please use your company email. Personal addresses like @{domain} can't be used to sign up."],
        )
    allowed = registration_email_domains()
    if not allowed:
        return ValidationResult(valid=True, errors=[])
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
    seen: set[str] = set()
    # validate_company_email runs validate_email first, so a bad email would
    # otherwise be reported twice. Dedupe while keeping the first occurrence.
    for result in [
        validate_username(username),
        validate_email(email),
        validate_company_email(email),
        validate_password(password, min_length=min_password_length),
        validate_company_name(company_name),
    ]:
        for error in result.errors:
            if error not in seen:
                seen.add(error)
                all_errors.append(error)
    return ValidationResult(valid=len(all_errors) == 0, errors=all_errors)
