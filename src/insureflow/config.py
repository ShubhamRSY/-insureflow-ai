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

    max_retries: int = 3
    extraction_chunk_size: int = 4000
    extraction_overlap: int = 200


settings = Settings()
