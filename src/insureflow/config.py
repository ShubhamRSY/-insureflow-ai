from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
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


settings = Settings()
