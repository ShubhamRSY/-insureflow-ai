from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    PROMPT = "prompt"
    LLM_CONFIG = "llm_config"
    COMPLIANCE_RULE = "compliance_rule"
    AGENT_LOGIC = "agent_logic"


class RegistryEntryStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ReviewComment(BaseModel):
    comment_id: str = Field(default_factory=lambda: f"cmt-{uuid4().hex[:8]}")
    reviewer: str
    comment: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class RegistryEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: f"reg-{uuid4().hex[:12]}")
    component_type: ComponentType
    version_label: str
    status: RegistryEntryStatus = RegistryEntryStatus.DRAFT
    created_by: str = ""
    description: str = ""
    change_notes: str = ""
    checksum: str = ""
    review_comments: list[ReviewComment] = Field(default_factory=list)
    superseded_by: Optional[str] = None
    active_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class PromptVersion(RegistryEntry):
    prompt_key: str = ""
    prompt_text: str = ""
    prompt_hash: str = ""

    def compute_diff(self, other: PromptVersion) -> dict[str, Any]:
        return {
            "component_type": "prompt",
            "prompt_key": self.prompt_key,
            "from_version": other.version_label,
            "to_version": self.version_label,
            "from_hash": other.prompt_hash,
            "to_hash": self.prompt_hash,
            "hash_changed": self.prompt_hash != other.prompt_hash,
            "text_changed": self.prompt_text != other.prompt_text,
        }


class LLMConfigVersion(RegistryEntry):
    model_tier: str = ""  # cheap, expensive, default
    provider: str = ""
    model_name: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096

    def compute_diff(self, other: LLMConfigVersion) -> dict[str, Any]:
        changes = {}
        for field in ("provider", "model_name", "temperature", "max_tokens"):
            a = getattr(self, field)
            b = getattr(other, field)
            if a != b:
                changes[field] = {"from": b, "to": a}
        return {
            "component_type": "llm_config",
            "model_tier": self.model_tier,
            "from_version": other.version_label,
            "to_version": self.version_label,
            "changes": changes,
        }


class AgentLogicVersion(RegistryEntry):
    agent_type: str = ""
    source_file: str = ""
    source_hash: str = ""

    def compute_diff(self, other: AgentLogicVersion) -> dict[str, Any]:
        return {
            "component_type": "agent_logic",
            "agent_type": self.agent_type,
            "from_version": other.version_label,
            "to_version": self.version_label,
            "from_hash": other.source_hash,
            "to_hash": self.source_hash,
            "hash_changed": self.source_hash != other.source_hash,
        }


class ComplianceRuleVersion(RegistryEntry):
    rules_snapshot: dict[str, Any] = Field(default_factory=dict)

    def compute_diff(self, other: ComplianceRuleVersion) -> dict[str, Any]:
        old_rules = set(other.rules_snapshot.keys())
        new_rules = set(self.rules_snapshot.keys())
        return {
            "component_type": "compliance_rule",
            "from_version": other.version_label,
            "to_version": self.version_label,
            "added": list(new_rules - old_rules),
            "removed": list(old_rules - new_rules),
            "changed": [
                r
                for r in old_rules & new_rules
                if other.rules_snapshot[r] != self.rules_snapshot[r]
            ],
        }


class ChangeRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"cr-{uuid4().hex[:8]}")
    title: str
    description: str = ""
    entries: list[str] = Field(default_factory=list)
    status: RegistryEntryStatus = RegistryEntryStatus.DRAFT
    requested_by: str = ""
    reviewed_by: str = ""
    review_decision: str = ""
    review_comments: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class RegistrySnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: f"snap-{uuid4().hex[:8]}")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    prompts: dict[str, str] = Field(default_factory=dict)
    llm_configs: dict[str, str] = Field(default_factory=dict)
    compliance_rules: list[str] = Field(default_factory=list)
    agent_logic: dict[str, str] = Field(default_factory=dict)
    bundle_id: str = ""
