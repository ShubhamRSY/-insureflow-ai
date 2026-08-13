"""Canonical underwriting decision vocabulary shared across verticals.

Vertical-specific enums (UWDecision, MortgageDecision, LoanDecision, SignOffAction)
remain for domain APIs. Normalize at boundaries with ``normalize_decision``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class DecisionOutcome(str, Enum):
    """Unified decision outcome for analytics, ML labels, and cross-vertical gates."""

    ACCEPT = "accept"
    CONDITIONAL_ACCEPT = "conditional_accept"
    REFER = "refer"
    SUSPEND = "suspend"
    DECLINE = "decline"


# Higher = more favorable to the applicant / bind path
DECISION_RANK: dict[DecisionOutcome, int] = {
    DecisionOutcome.DECLINE: 0,
    DecisionOutcome.SUSPEND: 1,
    DecisionOutcome.REFER: 2,
    DecisionOutcome.CONDITIONAL_ACCEPT: 3,
    DecisionOutcome.ACCEPT: 4,
}

_ALIASES: dict[str, DecisionOutcome] = {
    # accept family
    "accept": DecisionOutcome.ACCEPT,
    "accepted": DecisionOutcome.ACCEPT,
    "approve": DecisionOutcome.ACCEPT,
    "approved": DecisionOutcome.ACCEPT,
    "quote": DecisionOutcome.ACCEPT,
    "quoted": DecisionOutcome.ACCEPT,
    "will_quote": DecisionOutcome.ACCEPT,
    "bind": DecisionOutcome.ACCEPT,
    "bound": DecisionOutcome.ACCEPT,
    # conditional
    "conditional_accept": DecisionOutcome.CONDITIONAL_ACCEPT,
    "conditional-accept": DecisionOutcome.CONDITIONAL_ACCEPT,
    "approved_with_conditions": DecisionOutcome.CONDITIONAL_ACCEPT,
    "approve_with_conditions": DecisionOutcome.CONDITIONAL_ACCEPT,
    "conditional_approval": DecisionOutcome.CONDITIONAL_ACCEPT,
    # refer
    "refer": DecisionOutcome.REFER,
    "referral": DecisionOutcome.REFER,
    "referred": DecisionOutcome.REFER,
    "request_info": DecisionOutcome.REFER,
    # suspend / hold
    "suspend": DecisionOutcome.SUSPEND,
    "suspended": DecisionOutcome.SUSPEND,
    # decline family
    "decline": DecisionOutcome.DECLINE,
    "declined": DecisionOutcome.DECLINE,
    "deny": DecisionOutcome.DECLINE,
    "denied": DecisionOutcome.DECLINE,
    "reject": DecisionOutcome.DECLINE,
    "rejected": DecisionOutcome.DECLINE,
    "no_quote": DecisionOutcome.DECLINE,
    "no-quote": DecisionOutcome.DECLINE,
    "will_not_quote": DecisionOutcome.DECLINE,
}


def normalize_decision(value: Any, default: DecisionOutcome = DecisionOutcome.REFER) -> DecisionOutcome:
    """Map any vertical decision string/enum to ``DecisionOutcome``."""
    if isinstance(value, DecisionOutcome):
        return value
    if value is None:
        return default
    raw = getattr(value, "value", value)
    key = str(raw or "").strip().lower().replace(" ", "_")
    return _ALIASES.get(key, default)


def decision_rank(value: Any) -> int:
    return DECISION_RANK[normalize_decision(value)]


def is_decline(value: Any) -> bool:
    return normalize_decision(value) == DecisionOutcome.DECLINE


def is_accept_family(value: Any) -> bool:
    return normalize_decision(value) in {DecisionOutcome.ACCEPT, DecisionOutcome.CONDITIONAL_ACCEPT}


def is_bind_eligible(value: Any) -> bool:
    """Only clean accepts are bind/quote-eligible without further conditions."""
    return normalize_decision(value) == DecisionOutcome.ACCEPT


def skips_core_push(value: Any) -> bool:
    """Decisions that should not push to core policy admin yet."""
    return normalize_decision(value) in {
        DecisionOutcome.DECLINE,
        DecisionOutcome.REFER,
        DecisionOutcome.SUSPEND,
    }


def to_vertical(outcome: DecisionOutcome, vertical: str) -> str:
    """Emit the preferred string for a vertical's native vocabulary."""
    v = (vertical or "").lower()
    if v in {"mortgage", "mort"}:
        return {
            DecisionOutcome.ACCEPT: "approve",
            DecisionOutcome.CONDITIONAL_ACCEPT: "approve_with_conditions",
            DecisionOutcome.REFER: "refer",
            DecisionOutcome.SUSPEND: "suspend",
            DecisionOutcome.DECLINE: "deny",
        }[outcome]
    if v in {"lending", "lend", "credit"}:
        return {
            DecisionOutcome.ACCEPT: "approved",
            DecisionOutcome.CONDITIONAL_ACCEPT: "approved_with_conditions",
            DecisionOutcome.REFER: "referred",
            DecisionOutcome.SUSPEND: "suspended",
            DecisionOutcome.DECLINE: "declined",
        }[outcome]
    # insurance / default
    return {
        DecisionOutcome.ACCEPT: "accept",
        DecisionOutcome.CONDITIONAL_ACCEPT: "conditional_accept",
        DecisionOutcome.REFER: "refer",
        DecisionOutcome.SUSPEND: "refer",
        DecisionOutcome.DECLINE: "decline",
    }[outcome]


def ml_binary_target(value: Any) -> float:
    """Classification target: 1 = adverse (decline/suspend), 0 = accept family, 0.5 = refer."""
    outcome = normalize_decision(value)
    if outcome == DecisionOutcome.DECLINE:
        return 1.0
    if outcome == DecisionOutcome.SUSPEND:
        return 1.0
    if outcome == DecisionOutcome.REFER:
        return 0.5
    return 0.0
