"""Tests for HITL evaluation rubrics."""

from __future__ import annotations

from evaluations.hitl_rubrics import (
    AgreeLabel,
    HITLEvalStore,
    HumanEvalReview,
    RUBRIC_DEFINITIONS,
    export_rubric_card,
    seed_demo_reviews,
)


def test_rubric_definitions_complete():
    assert len(RUBRIC_DEFINITIONS) >= 8
    for meta in RUBRIC_DEFINITIONS.values():
        assert "pass_threshold" in meta
        assert "description" in meta


def test_submit_and_summary(tmp_path):
    store = HITLEvalStore(path=tmp_path / "hitl")
    review = HumanEvalReview(
        case_id="case-a",
        reviewer="uw.test",
        scores={
            "field_extraction_accuracy": 5,
            "decision_appropriateness": 5,
            "reasoning_quality": 4,
            "hallucination_absence": 5,
            "coverage_completeness": 4,
            "compliance_safety": 5,
            "provenance_trust": 5,
            "overall_production_ready": 4,
        },
        ai_decision="REFER",
        human_preferred_decision="REFER",
        decision_agree=AgreeLabel.AGREE,
        feedback_tags=["good_provenance"],
    )
    stored = store.submit(review)
    assert stored.case_pass is True
    summary = store.summary()
    assert summary.total_reviews == 1
    assert summary.agree_rate == 1.0
    assert summary.case_pass_rate == 1.0


def test_disagree_fails_case(tmp_path):
    store = HITLEvalStore(path=tmp_path / "hitl")
    review = HumanEvalReview(
        case_id="case-b",
        reviewer="uw.test",
        scores={"overall_production_ready": 5, "field_extraction_accuracy": 5},
        ai_decision="ACCEPT",
        human_preferred_decision="DECLINE",
        decision_agree=AgreeLabel.DISAGREE,
        decision_change_reason="material undisclosed loss",
        feedback_tags=["over_aggressive_accept"],
    )
    stored = store.submit(review)
    assert stored.case_pass is False
    assert "human_disagrees_with_ai_decision" in stored.blocking_issues


def test_seed_demo_and_rubric_card(tmp_path, monkeypatch):
    monkeypatch.setenv("HITL_EVAL_PATH", str(tmp_path / "hitl"))
    store = HITLEvalStore(path=tmp_path / "hitl")
    seeded = seed_demo_reviews(store)
    assert len(seeded) >= 3
    # idempotent
    assert len(seed_demo_reviews(store)) >= 3
    card = export_rubric_card(tmp_path / "RUBRIC_CARD.md")
    text = open(card, encoding="utf-8").read()
    assert "Field extraction accuracy" in text
    assert "Feedback we track from humans" in text
