"""Canonical decision vocabulary across insurance / mortgage / lending."""

from __future__ import annotations

import pytest

from insureflow.decisions import DecisionOutcome, decision_rank, is_accept_family, is_bind_eligible, is_decline, ml_binary_target, normalize_decision, skips_core_push, to_vertical
from insureflow.lending.models import LoanDecision
from insureflow.models.agents import UWDecision
from insureflow.models.mortgage import MortgageDecision


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("accept", DecisionOutcome.ACCEPT),
        ("approve", DecisionOutcome.ACCEPT),
        ("approved", DecisionOutcome.ACCEPT),
        ("conditional_accept", DecisionOutcome.CONDITIONAL_ACCEPT),
        ("approve_with_conditions", DecisionOutcome.CONDITIONAL_ACCEPT),
        ("approved_with_conditions", DecisionOutcome.CONDITIONAL_ACCEPT),
        ("refer", DecisionOutcome.REFER),
        ("referred", DecisionOutcome.REFER),
        ("request_info", DecisionOutcome.REFER),
        ("suspend", DecisionOutcome.SUSPEND),
        ("decline", DecisionOutcome.DECLINE),
        ("deny", DecisionOutcome.DECLINE),
        ("denied", DecisionOutcome.DECLINE),
        ("declined", DecisionOutcome.DECLINE),
        (UWDecision.ACCEPT, DecisionOutcome.ACCEPT),
        (MortgageDecision.APPROVE, DecisionOutcome.ACCEPT),
        (MortgageDecision.APPROVE_WITH_CONDITIONS, DecisionOutcome.CONDITIONAL_ACCEPT),
        (MortgageDecision.DENY, DecisionOutcome.DECLINE),
        (LoanDecision.APPROVED, DecisionOutcome.ACCEPT),
        (LoanDecision.APPROVED_WITH_CONDITIONS, DecisionOutcome.CONDITIONAL_ACCEPT),
        (LoanDecision.DECLINED, DecisionOutcome.DECLINE),
        (LoanDecision.REFERRED, DecisionOutcome.REFER),
        (LoanDecision.SUSPENDED, DecisionOutcome.SUSPEND),
    ],
)
def test_normalize_across_verticals(raw, expected) -> None:
    assert normalize_decision(raw) == expected


def test_ranks_and_gates() -> None:
    assert decision_rank("accept") > decision_rank("refer") > decision_rank("decline")
    assert is_bind_eligible("approve") is True
    assert is_bind_eligible("approve_with_conditions") is False
    assert is_accept_family("approved_with_conditions") is True
    assert is_decline("deny") is True
    assert skips_core_push("refer") is True
    assert skips_core_push("accept") is False


def test_to_vertical_roundtrip() -> None:
    assert to_vertical(DecisionOutcome.ACCEPT, "insurance") == "accept"
    assert to_vertical(DecisionOutcome.CONDITIONAL_ACCEPT, "insurance") == "conditional_accept"
    assert to_vertical(DecisionOutcome.ACCEPT, "mortgage") == "approve"
    assert to_vertical(DecisionOutcome.CONDITIONAL_ACCEPT, "mortgage") == "approve_with_conditions"
    assert to_vertical(DecisionOutcome.DECLINE, "mortgage") == "deny"
    assert to_vertical(DecisionOutcome.ACCEPT, "lending") == "approved"
    assert to_vertical(DecisionOutcome.CONDITIONAL_ACCEPT, "lending") == "approved_with_conditions"
    assert to_vertical(DecisionOutcome.DECLINE, "lending") == "declined"


def test_ml_binary_target() -> None:
    assert ml_binary_target("decline") == 1.0
    assert ml_binary_target("accept") == 0.0
    assert ml_binary_target("refer") == 0.5
