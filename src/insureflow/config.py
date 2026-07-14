from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Pull bank secrets from AWS before Settings snapshots env (no-op without ARN).
try:
    from insureflow.security.secrets_loader import load_secrets_from_aws

    load_secrets_from_aws()
except Exception:
    pass


@dataclass(frozen=True)
class Settings:
    # Runtime posture
    environment: str = os.getenv("ENVIRONMENT", "development")
    bank_mode: bool = os.getenv("BANK_MODE", "").lower() in {"1", "true", "yes"} or (os.getenv("ENVIRONMENT", "development").lower() == "production")

    # Legacy single-model config (backward compat)
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # Dual-model config: cheap for specialist agents, expensive for final decision
    llm_cheap_provider: str = os.getenv("LLM_CHEAP_PROVIDER", "")
    llm_cheap_model: str = os.getenv("LLM_CHEAP_MODEL", "gpt-4o-mini")
    llm_cheap_api_key: str = os.getenv("LLM_CHEAP_API_KEY", "")
    llm_cheap_base_url: str = os.getenv("LLM_CHEAP_BASE_URL", "")

    llm_expensive_provider: str = os.getenv("LLM_EXPENSIVE_PROVIDER", "")
    llm_expensive_model: str = os.getenv("LLM_EXPENSIVE_MODEL", "gpt-4o")
    llm_expensive_api_key: str = os.getenv("LLM_EXPENSIVE_API_KEY", "")
    llm_expensive_base_url: str = os.getenv("LLM_EXPENSIVE_BASE_URL", "")

    # Claude-specific
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    provenance_hierarchy: list[str] = field(
        default_factory=lambda: [
            "signed_legal_submission",
            "broker_acord_xml",
            "underwriter_notes",
            "inspection_report",
            "supplemental_document",
        ]
    )

    confidence_thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "critical": 0.95,
            "high": 0.90,
            "medium": 0.80,
            "low": 0.70,
        }
    )

    field_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "construction_type": "risk_profile.construction_type",
            "year_built": "location.0.year_built",
            "square_footage": "location.0.square_footage",
            "number_of_stories": "risk_profile.number_of_stories",
            "occupancy_type": "risk_profile.occupancy_type",
            "sprinklered": "risk_profile.sprinklered",
            "protection_class": "risk_profile.protection_class",
            "prior_claims": "financial.prior_losses",
        }
    )

    audit_log_path: Path = Path(os.getenv("AUDIT_LOG_PATH", "./audit_logs"))
    storage_backend: str = os.getenv("STORAGE_BACKEND", "memory")

    # Auth
    secret_key: str = os.getenv("SECRET_KEY", "CHANGE_ME_TO_A_LONG_SECRET_KEY_IN_PRODUCTION")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Job store (memory | redis | auto)
    job_store_backend: str = os.getenv("JOB_STORE_BACKEND", "auto")
    redis_url: str = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", ""))

    # Encryption at rest for audit bundles
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "")

    max_retries: int = 3
    extraction_chunk_size: int = 4000
    extraction_overlap: int = 200

    # Oracle clients: simulated | live | auto
    oracle_mode: str = os.getenv("ORACLE_MODE", "auto")
    clue_api_key: str = os.getenv("CLUE_API_KEY", "")
    clue_api_url: str = os.getenv("CLUE_API_URL", "https://integrations.rytera.ai/oracles/clue/v2")
    clue_query_path: str = os.getenv("CLUE_QUERY_PATH", "/queries")

    verisk_api_key: str = os.getenv("VERISK_API_KEY", "")
    ncci_api_key: str = os.getenv("NCCI_API_KEY", "")
    ncci_api_url: str = os.getenv("NCCI_API_URL", "https://integrations.rytera.ai/oracles/ncci/v2")
    ncci_query_path: str = os.getenv("NCCI_QUERY_PATH", "/experience")

    aplus_api_key: str = os.getenv("APLUS_API_KEY", "")
    aplus_api_url: str = os.getenv("APLUS_API_URL", "https://integrations.rytera.ai/oracles/aplus/v2")
    aplus_query_path: str = os.getenv("APLUS_QUERY_PATH", "/queries")

    cat_api_key: str = os.getenv("CAT_API_KEY", "")
    cat_api_url: str = os.getenv("CAT_API_URL", "https://integrations.rytera.ai/oracles/cat/v1")
    cat_query_path: str = os.getenv("CAT_QUERY_PATH", "/model")

    iso_rating_api_key: str = os.getenv("ISO_RATING_API_KEY", "")
    iso_rating_api_url: str = os.getenv("ISO_RATING_API_URL", "https://integrations.rytera.ai/oracles/iso/v1")
    iso_rating_mode: str = os.getenv("ISO_RATING_MODE", "auto")

    # Policy admin / core systems
    guidewire_api_key: str = os.getenv("GUIDEWIRE_API_KEY", "")
    guidewire_api_url: str = os.getenv("GUIDEWIRE_API_URL", "https://integrations.rytera.ai/policy/guidewire/v1")
    guidewire_username: str = os.getenv("GUIDEWIRE_USERNAME", "")
    guidewire_password: str = os.getenv("GUIDEWIRE_PASSWORD", "")
    guidewire_mode: str = os.getenv("GUIDEWIRE_MODE", "auto")

    britecore_api_key: str = os.getenv("BRITECORE_API_KEY", "")
    britecore_api_url: str = os.getenv("BRITECORE_API_URL", "https://integrations.rytera.ai/policy/britecore/v2")
    britecore_mode: str = os.getenv("BRITECORE_MODE", "auto")

    # Enterprise ecosystem
    loss_control_api_key: str = os.getenv("LOSS_CONTROL_API_KEY", "")
    loss_control_api_url: str = os.getenv("LOSS_CONTROL_API_URL", "https://integrations.rytera.ai/enterprise/loss-control/v1")
    loss_control_mode: str = os.getenv("LOSS_CONTROL_MODE", "auto")

    claims_api_key: str = os.getenv("CLAIMS_API_KEY", "")
    claims_api_url: str = os.getenv("CLAIMS_API_URL", "https://integrations.rytera.ai/enterprise/claims/v1")
    claims_mode: str = os.getenv("CLAIMS_MODE", "auto")

    broker_portal_api_key: str = os.getenv("BROKER_PORTAL_API_KEY", "")
    broker_portal_api_url: str = os.getenv("BROKER_PORTAL_API_URL", "https://integrations.rytera.ai/enterprise/broker-portal/v1")
    broker_portal_mode: str = os.getenv("BROKER_PORTAL_MODE", "auto")

    actuarial_api_key: str = os.getenv("ACTUARIAL_API_KEY", "")
    actuarial_api_url: str = os.getenv("ACTUARIAL_API_URL", "https://integrations.rytera.ai/enterprise/actuarial/v1")
    actuarial_mode: str = os.getenv("ACTUARIAL_MODE", "auto")

    hubspot_api_key: str = os.getenv("HUBSPOT_API_KEY", "")
    hubspot_api_url: str = os.getenv("HUBSPOT_API_URL", "https://api.hubapi.com/crm/v3")
    hubspot_mode: str = os.getenv("HUBSPOT_MODE", "auto")

    integration_timeout_seconds: float = float(os.getenv("INTEGRATION_TIMEOUT_SECONDS", "30"))
    integration_max_retries: int = int(os.getenv("INTEGRATION_MAX_RETRIES", "3"))

    # Rytera integration gateway (bundled in API at /integrations for local + self-hosted prod)
    integration_gateway_api_key: str = os.getenv("INTEGRATION_GATEWAY_API_KEY", "rytera-dev-gateway-key-change-in-production")
    api_port: int = int(os.getenv("API_PORT", "8002"))

    # LangSmith cloud eval / pipeline tracing (https://smith.langchain.com)
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", "insureflow-evals"))
    langsmith_endpoint: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    langsmith_tracing: bool = os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "true")).lower() in {
        "1",
        "true",
        "yes",
    }

    # AWS / bank landing zone
    aws_region: str = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    aws_secrets_arn: str = os.getenv("AWS_SECRETS_ARN", os.getenv("AWS_SECRET_ID", ""))
    cloudwatch_logs: bool = os.getenv("CLOUDWATCH_LOGS", "").lower() in {"1", "true", "yes"}
    worm_audit_path: Path = Path(os.getenv("WORM_AUDIT_PATH", "./audit_logs/worm"))
    audit_retention_days: int = int(os.getenv("AUDIT_RETENTION_DAYS", "2555"))
    retention_s3_bucket: str = os.getenv("RETENTION_S3_BUCKET", "")


settings = Settings()


def maybe_enable_langsmith_tracing() -> bool:
    """Enable LangSmith tracing when LANGSMITH_API_KEY is configured."""
    if not settings.langsmith_api_key:
        return False
    os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langsmith_tracing else "false"
    os.environ["LANGSMITH_TRACING"] = "true" if settings.langsmith_tracing else "false"
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ.setdefault("LANGSMITH_ENDPOINT", settings.langsmith_endpoint)
        os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.langsmith_endpoint)
    return True


def bootstrap_security() -> list[str]:
    """Validate bank/prod posture; return error messages (empty = ok)."""
    from insureflow.security.posture import resolve_security_posture, validate_startup_secrets

    posture = resolve_security_posture(environment=settings.environment, bank_mode=settings.bank_mode)
    return validate_startup_secrets(
        secret_key=settings.secret_key,
        encryption_key=settings.encryption_key,
        posture=posture,
    )
