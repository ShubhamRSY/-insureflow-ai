"""ZTA data models — task types, route decisions and context."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ZtaTask(str, Enum):
    """Pipeline tasks the router can classify."""

    EXTRACT_STRUCTURED = "extract_structured"
    EXTRACT_UNSTRUCTURED = "extract_unstructured"
    RECONCILE = "reconcile"
    SCORE = "score"
    PRICE = "price"
    DECIDE = "decide"
    MEMO = "memo"
    VISION = "vision"


class RouteDecision(str, Enum):
    """Where a task gets resolved."""

    DETERMINISTIC = "deterministic"  # zero tokens — solved with code/rules/ML models
    LLM = "llm"  # genuinely needs an LLM
    ESCALATE_HUMAN = "escalate_human"  # can't be solved deterministically, don't burn tokens
    SKIP = "skip"  # not applicable in this mode


@dataclass
class RouteContext:
    """Signals the router uses to decide a single task.

    Only the fields relevant to a task need to be filled in.
    """

    text: str | None = None
    regex_field_count: int = 0
    expected_fields: int = 0
    doc_type: str = ""
    conflict_count: int = 0
    critical_conflict_count: int = 0
    required_features_present: bool = True
    missing_required: list[str] = field(default_factory=list)
    photo_count: int = 0


@dataclass
class RouteResult:
    """A single routing decision with token accounting."""

    task: ZtaTask
    decision: RouteDecision
    reason: str
    tokens_saved_est: int = 0
    tokens_used_est: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "task": self.task.value,
            "decision": self.decision.value,
            "reason": self.reason,
            "tokens_saved_est": self.tokens_saved_est,
            "tokens_used_est": self.tokens_used_est,
        }
