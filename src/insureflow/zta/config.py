"""Zero Token Architecture (ZTA) configuration.

ZTA is the design principle: *use AI only when you must — everything else,
solve deterministically.*  The best token is the one you never had to generate.

All settings are environment-driven so deployments can tune behaviour without
code changes:

- ``ZTA_ENABLED`` (0/1): enable the router. When disabled the pipelines keep
  their legacy all-or-nothing ``use_llm`` behaviour and the router only records
  what *would* have been decided.
- ``ZTA_STRICT`` (0/1): hard mode — never call the LLM. Tasks that can't be
  solved deterministically are escalated to a human or skipped.
- ``ZTA_EXPECTED_FIELDS_RATIO`` (0.0–1.0): regex/rule extraction coverage ratio
  that counts as "good enough" for deterministic handling.
- ``ZTA_MAX_LLM_TASKS_PER_JOB`` (int): budget of LLM tasks allowed per job.
- ``ZTA_MEMO_LLM`` (0/1): whether memo generation may use the LLM.
"""

from __future__ import annotations

import os

DEFAULT_EXPECTED_FIELDS_RATIO = 0.6
DEFAULT_MAX_LLM_TASKS_PER_JOB = 5


def _env_flag(name: str) -> bool:
    return os.getenv(name, "0").lower() in {"1", "true", "yes", "on"}


class ZtaConfig:
    """Environment-driven ZTA settings."""

    def __init__(self) -> None:
        self.enabled = _env_flag("ZTA_ENABLED")
        self.strict = _env_flag("ZTA_STRICT")
        self.memo_llm = _env_flag("ZTA_MEMO_LLM")
        self.expected_fields_ratio = float(os.getenv("ZTA_EXPECTED_FIELDS_RATIO", str(DEFAULT_EXPECTED_FIELDS_RATIO)))
        self.max_llm_tasks_per_job = int(os.getenv("ZTA_MAX_LLM_TASKS_PER_JOB", str(DEFAULT_MAX_LLM_TASKS_PER_JOB)))

    @property
    def mode(self) -> str:
        if self.strict:
            return "strict"
        if self.enabled:
            return "zta"
        return "legacy"

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "strict": self.strict,
            "memo_llm": self.memo_llm,
            "mode": self.mode,
            "expected_fields_ratio": self.expected_fields_ratio,
            "max_llm_tasks_per_job": self.max_llm_tasks_per_job,
        }
