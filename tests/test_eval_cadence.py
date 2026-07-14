"""Tests for eval / HITL cadence policy."""

from __future__ import annotations

from evaluations.cadence import EVAL_CADENCE, HITL_CADENCE, cadence_inventory


def test_cadence_has_eval_and_hitl_tracks() -> None:
    inv = cadence_inventory()
    assert "automated_eval" in inv
    assert "human_in_the_loop" in inv
    assert len(EVAL_CADENCE) >= 4
    assert len(HITL_CADENCE) >= 3


def test_summary_frequencies() -> None:
    s = cadence_inventory()["summary"]
    assert "every PR" in s["unit_tests"]
    assert "nightly" in s["golden_and_ragas"]
    assert "weekly" in s["giskard_and_full_report"]
    assert "every submission" in s["production_hitl"]
    assert "weekly" in s["eval_hitl_rubrics"]


def test_interview_summary_mentions_both() -> None:
    text = cadence_inventory()["interview_summary"].lower()
    assert "nightly" in text
    assert "weekly" in text
    assert "sign-off" in text or "submission" in text
