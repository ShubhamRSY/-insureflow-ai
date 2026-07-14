"""Banking / production security posture helpers."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_INSECURE_SECRET = "CHANGE_ME_TO_A_LONG_SECRET_KEY_IN_PRODUCTION"


@dataclass(frozen=True)
class SecurityPosture:
    """Resolved runtime security mode for bank simulation vs local demo."""

    environment: str  # development | staging | production
    bank_mode: bool
    allow_open_registration: bool
    allow_auth_reset: bool
    require_encryption: bool
    require_strong_secret: bool
    min_password_length: int

    @property
    def is_hardened(self) -> bool:
        return self.bank_mode or self.environment == "production"


def resolve_security_posture(
    *,
    environment: str | None = None,
    bank_mode: bool | None = None,
) -> SecurityPosture:
    env = (environment or os.getenv("ENVIRONMENT", "development")).strip().lower()
    if bank_mode is None:
        bank_mode = os.getenv("BANK_MODE", "").lower() in {"1", "true", "yes"} or env == "production"

    if bank_mode or env == "production":
        return SecurityPosture(
            environment=env,
            bank_mode=True,
            allow_open_registration=os.getenv("ALLOW_OPEN_REGISTRATION", "false").lower() in {"1", "true", "yes"},
            allow_auth_reset=os.getenv("ALLOW_AUTH_RESET", "false").lower() in {"1", "true", "yes"},
            require_encryption=True,
            require_strong_secret=True,
            min_password_length=int(os.getenv("MIN_PASSWORD_LENGTH", "12")),
        )

    return SecurityPosture(
        environment=env,
        bank_mode=False,
        allow_open_registration=os.getenv("ALLOW_OPEN_REGISTRATION", "true").lower() in {"1", "true", "yes"},
        allow_auth_reset=os.getenv("ALLOW_AUTH_RESET", "true").lower() in {"1", "true", "yes"},
        require_encryption=os.getenv("REQUIRE_ENCRYPTION", "false").lower() in {"1", "true", "yes"},
        require_strong_secret=False,
        min_password_length=int(os.getenv("MIN_PASSWORD_LENGTH", "4")),
    )


def validate_startup_secrets(
    *,
    secret_key: str,
    encryption_key: str,
    posture: SecurityPosture | None = None,
) -> list[str]:
    """Return blocking error messages when bank/prod posture is violated."""
    posture = posture or resolve_security_posture()
    errors: list[str] = []

    if posture.require_strong_secret:
        if not secret_key or secret_key == _INSECURE_SECRET or len(secret_key) < 32:
            errors.append(
                "BANK_MODE/production requires SECRET_KEY to be set to a unique value ≥ 32 characters "
                "(not the default CHANGE_ME placeholder)."
            )

    if posture.require_encryption and not encryption_key:
        errors.append(
            "BANK_MODE/production requires ENCRYPTION_KEY for audit encryption at rest. "
            "Generate with: python -c \"from insureflow.storage.encryption import EnvelopeEncryption; print(EnvelopeEncryption.generate_key())\""
        )

    return errors
