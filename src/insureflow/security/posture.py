"""Banking / production security posture helpers."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_INSECURE_SECRET = "CHANGE_ME_TO_A_LONG_SECRET_KEY_IN_PRODUCTION"
_DEV_GATEWAY_KEY = "rytera-dev-gateway-key-change-in-production"


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
    env_raw = environment if environment is not None else os.getenv("ENVIRONMENT", "development")
    env = str(env_raw or "development").strip().lower()
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


def allow_simulated_bind(posture: SecurityPosture | None = None) -> bool:
    """Whether fake/local policy binds are permitted (dev only unless explicitly opted in)."""
    posture = posture or resolve_security_posture()
    explicit = os.getenv("ALLOW_SIMULATED_BIND", "").lower() in {"1", "true", "yes"}
    if posture.is_hardened:
        return explicit
    return True


def load_demo_assets(posture: SecurityPosture | None = None) -> bool:
    """Whether demo portfolio seeds / sample connectors should load."""
    posture = posture or resolve_security_posture()
    if os.getenv("LOAD_DEMO_PORTFOLIO", "").lower() in {"1", "true", "yes"}:
        return True
    if os.getenv("LOAD_DEMO_PORTFOLIO", "").lower() in {"0", "false", "no"}:
        return False
    return not posture.is_hardened


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
            errors.append("BANK_MODE/production requires SECRET_KEY to be set to a unique value ≥ 32 characters (not the default CHANGE_ME placeholder).")

    if posture.require_encryption and not encryption_key:
        errors.append(
            "BANK_MODE/production requires ENCRYPTION_KEY for audit encryption at rest. "
            'Generate with: python -c "from insureflow.storage.encryption import EnvelopeEncryption; print(EnvelopeEncryption.generate_key())"'
        )

    if posture.is_hardened:
        gateway_key = os.getenv("INTEGRATION_GATEWAY_API_KEY", "")
        if not gateway_key or gateway_key == _DEV_GATEWAY_KEY:
            errors.append("BANK_MODE/production requires INTEGRATION_GATEWAY_API_KEY to be a unique production secret (not the rytera-dev-gateway-key placeholder).")

        job_backend = (os.getenv("JOB_STORE_BACKEND") or "auto").strip().lower()
        if job_backend == "memory":
            errors.append("BANK_MODE/production forbids JOB_STORE_BACKEND=memory. Use redis or auto with a reachable REDIS_URL.")

        if posture.allow_open_registration:
            errors.append("BANK_MODE/production forbids ALLOW_OPEN_REGISTRATION=true. Disable open registration for hardened deployments.")

        if posture.allow_auth_reset:
            errors.append("BANK_MODE/production forbids ALLOW_AUTH_RESET=true. Disable auth reset for hardened deployments.")

        for key_name in (
            "CLUE_API_KEY",
            "APLUS_API_KEY",
            "NCCI_API_KEY",
            "CAT_API_KEY",
            "GUIDEWIRE_API_KEY",
            "BRITECORE_API_KEY",
            "ISO_RATING_API_KEY",
        ):
            val = os.getenv(key_name, "")
            if val == _DEV_GATEWAY_KEY:
                errors.append(
                    f"BANK_MODE/production: {key_name} still uses the development gateway placeholder. Replace with a production secret or clear it and set ORACLE_MODE/policy modes appropriately."
                )

        if os.getenv("REQUIRE_LIVE_ORACLES", "").lower() in {"1", "true", "yes"}:
            oracle_mode = (os.getenv("ORACLE_MODE") or "auto").strip().lower()
            if oracle_mode in {"simulated", ""}:
                errors.append("REQUIRE_LIVE_ORACLES=true but ORACLE_MODE is simulated. Set ORACLE_MODE=live or auto with live credentials.")

    return errors
