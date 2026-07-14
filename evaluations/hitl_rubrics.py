"""Human-in-the-loop evaluation rubrics for InsureFlow.

Two HITL feedback loops exist in the platform:

1. **Production HITL** (already shipped)
   Licensed UW sign-off + override analytics + bind/loss feedback.
   Tracks: decision agree/disagree, override category, UW confidence,
   premium delta, post-bind verdict, loss ratio calibration.

2. **Eval HITL** (this module)
   Human reviewers score golden-dataset / sample pipeline outputs with
   explicit rubrics before declaring deployment readiness.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_STORE = Path(os.getenv("HITL_EVAL_PATH", "./evaluation_hitl"))


class RubricDimension(str, Enum):
    """Dimensions a human reviewer scores on each eval case."""

    FIELD_EXTRACTION_ACCURACY = "field_extraction_accuracy"
    DECISION_APPROPRIATENESS = "decision_appropriateness"
    REASONING_QUALITY = "reasoning_quality"
    HALLUCINATION_ABSENCE = "hallucination_absence"
    COVERAGE_COMPLETENESS = "coverage_completeness"
    COMPLIANCE_SAFETY = "compliance_safety"
    PROVENANCE_TRUST = "provenance_trust"
    OVERALL_PRODUCTION_READY = "overall_production_ready"


RUBRIC_DEFINITIONS: dict[str, dict[str, Any]] = {
    RubricDimension.FIELD_EXTRACTION_ACCURACY.value: {
        "label": "Field extraction accuracy",
        "scale": "1-5",
        "description": "Named insured, construction, occupancy, PC, sqft, NAICS, revenue/payroll match source docs.",
        "pass_threshold": 4,
    },
    RubricDimension.DECISION_APPROPRIATENESS.value: {
        "label": "Decision appropriateness",
        "scale": "1-5",
        "description": "ACCEPT/REFER/DECLINE aligns with appetite, loss history, and risk facts.",
        "pass_threshold": 4,
    },
    RubricDimension.REASONING_QUALITY.value: {
        "label": "Reasoning quality",
        "scale": "1-5",
        "description": "Memo rationale is coherent, cites material risks, and is UW-usable.",
        "pass_threshold": 3,
    },
    RubricDimension.HALLUCINATION_ABSENCE.value: {
        "label": "Hallucination absence",
        "scale": "1-5",
        "description": "No unsupported limits, claimants, or facts invented beyond sources.",
        "pass_threshold": 4,
    },
    RubricDimension.COVERAGE_COMPLETENESS.value: {
        "label": "Coverage completeness",
        "scale": "1-5",
        "description": "Required coverages/limits/deductibles captured; material gaps flagged.",
        "pass_threshold": 3,
    },
    RubricDimension.COMPLIANCE_SAFETY.value: {
        "label": "Compliance & safety",
        "scale": "1-5",
        "description": "No unsafe bind recommendation when red flags present; guidelines respected.",
        "pass_threshold": 4,
    },
    RubricDimension.PROVENANCE_TRUST.value: {
        "label": "Provenance trust",
        "scale": "1-5",
        "description": "Structured ACORD wins over free-text when conflicts arise; mismatches called out.",
        "pass_threshold": 4,
    },
    RubricDimension.OVERALL_PRODUCTION_READY.value: {
        "label": "Overall production ready",
        "scale": "1-5",
        "description": "Would you trust this case output in a live bank/carrier workflow?",
        "pass_threshold": 4,
    },
}


class AgreeLabel(str, Enum):
    AGREE = "agree"
    PARTIAL = "partial"
    DISAGREE = "disagree"


class HumanEvalReview(BaseModel):
    """One human review of a single eval / golden case output."""

    review_id: str = Field(default_factory=lambda: f"hitl-{uuid4().hex[:10]}")
    case_id: str
    bundle_id: str = ""
    reviewer: str
    reviewer_role: str = "licensed_uw"  # licensed_uw | cuo | ml_eval | compliance
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # Rubric scores 1–5
    scores: dict[str, int] = Field(default_factory=dict)

    # Decision-level feedback (what we track from humans)
    ai_decision: str = ""
    human_preferred_decision: str = ""
    decision_agree: AgreeLabel = AgreeLabel.AGREE
    decision_change_reason: str = ""

    # Freeform + structured feedback tags
    notes: str = ""
    feedback_tags: list[str] = Field(default_factory=list)
    # Examples: missing_sprinkler_flag, over_aggressive_accept, under_extracted_payroll

    # Pass/fail for this case under human rubric
    case_pass: bool = False
    blocking_issues: list[str] = Field(default_factory=list)


class HITLEvalSummary(BaseModel):
    total_reviews: int = 0
    unique_cases: int = 0
    unique_reviewers: int = 0
    agree_rate: float = 0.0
    partial_rate: float = 0.0
    disagree_rate: float = 0.0
    case_pass_rate: float = 0.0
    avg_scores: dict[str, float] = Field(default_factory=dict)
    below_threshold: dict[str, int] = Field(default_factory=dict)
    top_feedback_tags: list[dict[str, Any]] = Field(default_factory=list)
    rubrics: dict[str, Any] = Field(default_factory=lambda: RUBRIC_DEFINITIONS)


class HITLEvalStore:
    """File-backed store for human eval reviews."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or DEFAULT_STORE)
        self.path.mkdir(parents=True, exist_ok=True)
        self._index = self.path / "reviews.jsonl"

    def submit(self, review: HumanEvalReview) -> HumanEvalReview:
        review.case_pass = self._compute_pass(review)
        if not review.blocking_issues:
            review.blocking_issues = self._blocking(review)
        with self._index.open("a", encoding="utf-8") as fh:
            fh.write(review.model_dump_json() + "\n")
        logger.info(
            "HITL eval review saved case=%s reviewer=%s pass=%s",
            review.case_id,
            review.reviewer,
            review.case_pass,
        )
        return review

    def list_reviews(self, case_id: str | None = None) -> list[HumanEvalReview]:
        if not self._index.exists():
            return []
        out: list[HumanEvalReview] = []
        for line in self._index.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = HumanEvalReview.model_validate_json(line)
            if case_id is None or r.case_id == case_id:
                out.append(r)
        return out

    def summary(self) -> HITLEvalSummary:
        reviews = self.list_reviews()
        if not reviews:
            return HITLEvalSummary(rubrics=RUBRIC_DEFINITIONS)

        n = len(reviews)
        agree = sum(1 for r in reviews if r.decision_agree == AgreeLabel.AGREE)
        partial = sum(1 for r in reviews if r.decision_agree == AgreeLabel.PARTIAL)
        disagree = sum(1 for r in reviews if r.decision_agree == AgreeLabel.DISAGREE)
        passed = sum(1 for r in reviews if r.case_pass)

        avg_scores: dict[str, float] = {}
        below: dict[str, int] = {}
        for dim, meta in RUBRIC_DEFINITIONS.items():
            vals = [r.scores[dim] for r in reviews if dim in r.scores]
            if vals:
                avg_scores[dim] = round(sum(vals) / len(vals), 3)
                thr = int(meta["pass_threshold"])
                below[dim] = sum(1 for v in vals if v < thr)

        tag_counts: dict[str, int] = {}
        for r in reviews:
            for t in r.feedback_tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1
        top_tags = [{"tag": k, "count": v} for k, v in sorted(tag_counts.items(), key=lambda x: -x[1])[:15]]

        return HITLEvalSummary(
            total_reviews=n,
            unique_cases=len({r.case_id for r in reviews}),
            unique_reviewers=len({r.reviewer for r in reviews}),
            agree_rate=round(agree / n, 4),
            partial_rate=round(partial / n, 4),
            disagree_rate=round(disagree / n, 4),
            case_pass_rate=round(passed / n, 4),
            avg_scores=avg_scores,
            below_threshold=below,
            top_feedback_tags=top_tags,
            rubrics=RUBRIC_DEFINITIONS,
        )

    @staticmethod
    def _compute_pass(review: HumanEvalReview) -> bool:
        if review.decision_agree == AgreeLabel.DISAGREE:
            return False
        for dim, meta in RUBRIC_DEFINITIONS.items():
            score = review.scores.get(dim)
            if score is None:
                continue
            if score < int(meta["pass_threshold"]):
                return False
        return bool(review.scores)

    @staticmethod
    def _blocking(review: HumanEvalReview) -> list[str]:
        issues: list[str] = []
        if review.decision_agree == AgreeLabel.DISAGREE:
            issues.append("human_disagrees_with_ai_decision")
        for dim, meta in RUBRIC_DEFINITIONS.items():
            score = review.scores.get(dim)
            if score is not None and score < int(meta["pass_threshold"]):
                issues.append(f"below_threshold:{dim}")
        return issues


def seed_demo_reviews(store: HITLEvalStore | None = None) -> list[HumanEvalReview]:
    """Seed representative human reviews so HITL analytics work out of the box."""
    store = store or HITLEvalStore()
    if store.list_reviews():
        return store.list_reviews()

    seeds = [
        HumanEvalReview(
            case_id="acme_manufacturing",
            reviewer="uw.patel",
            reviewer_role="licensed_uw",
            scores={
                RubricDimension.FIELD_EXTRACTION_ACCURACY.value: 5,
                RubricDimension.DECISION_APPROPRIATENESS.value: 4,
                RubricDimension.REASONING_QUALITY.value: 4,
                RubricDimension.HALLUCINATION_ABSENCE.value: 5,
                RubricDimension.COVERAGE_COMPLETENESS.value: 4,
                RubricDimension.COMPLIANCE_SAFETY.value: 5,
                RubricDimension.PROVENANCE_TRUST.value: 5,
                RubricDimension.OVERALL_PRODUCTION_READY.value: 4,
            },
            ai_decision="REFER",
            human_preferred_decision="REFER",
            decision_agree=AgreeLabel.AGREE,
            notes="Extraction solid; refer for ammonia / sprinkler items matches my review.",
            feedback_tags=["good_provenance", "correct_refer"],
        ),
        HumanEvalReview(
            case_id="pacific_coast",
            reviewer="uw.chen",
            reviewer_role="licensed_uw",
            scores={
                RubricDimension.FIELD_EXTRACTION_ACCURACY.value: 4,
                RubricDimension.DECISION_APPROPRIATENESS.value: 3,
                RubricDimension.REASONING_QUALITY.value: 3,
                RubricDimension.HALLUCINATION_ABSENCE.value: 4,
                RubricDimension.COVERAGE_COMPLETENESS.value: 3,
                RubricDimension.COMPLIANCE_SAFETY.value: 4,
                RubricDimension.PROVENANCE_TRUST.value: 4,
                RubricDimension.OVERALL_PRODUCTION_READY.value: 3,
            },
            ai_decision="ACCEPT",
            human_preferred_decision="REFER",
            decision_agree=AgreeLabel.DISAGREE,
            decision_change_reason="Unsprinklered dock + ammonia leak history warrant REFER, not ACCEPT.",
            notes="Model under-weighted inspection findings vs ACORD sprinklered claim.",
            feedback_tags=["over_aggressive_accept", "missed_sprinkler_gap", "loss_run_weighting"],
        ),
        HumanEvalReview(
            case_id="northwind_cold",
            reviewer="cuo.rivera",
            reviewer_role="cuo",
            scores={
                RubricDimension.FIELD_EXTRACTION_ACCURACY.value: 5,
                RubricDimension.DECISION_APPROPRIATENESS.value: 5,
                RubricDimension.REASONING_QUALITY.value: 4,
                RubricDimension.HALLUCINATION_ABSENCE.value: 5,
                RubricDimension.COVERAGE_COMPLETENESS.value: 4,
                RubricDimension.COMPLIANCE_SAFETY.value: 5,
                RubricDimension.PROVENANCE_TRUST.value: 5,
                RubricDimension.OVERALL_PRODUCTION_READY.value: 5,
            },
            ai_decision="REFER",
            human_preferred_decision="REFER",
            decision_agree=AgreeLabel.AGREE,
            notes="Strong provenance hierarchy on TIV mismatch.",
            feedback_tags=["good_provenance", "tiv_reconciliation"],
        ),
    ]
    return [store.submit(s) for s in seeds]


def track_hitl_to_langsmith(summary: HITLEvalSummary | None = None) -> dict[str, Any]:
    """Push HITL aggregate metrics to LangSmith when configured."""
    summary = summary or HITLEvalStore().summary()
    try:
        from evaluations.cloud_tracker import get_tracker

        metrics: dict[str, float | int | None] = {
            "hitl_agree_rate": summary.agree_rate,
            "hitl_disagree_rate": summary.disagree_rate,
            "hitl_case_pass_rate": summary.case_pass_rate,
            "hitl_total_reviews": summary.total_reviews,
        }
        for dim, val in summary.avg_scores.items():
            metrics[f"hitl_avg_{dim}"] = val
        result = get_tracker().log_metrics(
            run_name="hitl-eval-rubrics",
            metrics=metrics,
            outputs={
                "top_feedback_tags": summary.top_feedback_tags,
                "below_threshold": summary.below_threshold,
            },
            metadata={"suite": "hitl_rubrics"},
            tags=["evaluation", "hitl", "human-feedback"],
        )
        return {
            "enabled": result.enabled,
            "run_id": result.run_id,
            "local_path": result.local_path,
            "error": result.error,
        }
    except Exception as exc:
        logger.warning("HITL LangSmith tracking failed: %s", exc)
        return {"enabled": False, "error": str(exc)}


def export_rubric_card(path: str | Path | None = None) -> str:
    """Write a human-readable rubric card for reviewers."""
    dest = Path(path or DEFAULT_STORE / "RUBRIC_CARD.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# InsureFlow HITL Evaluation Rubric Card",
        "",
        "Score each dimension **1–5**. Case passes only if all scored dimensions meet threshold",
        "and decision_agree is not `disagree`.",
        "",
        "| Dimension | Threshold | What to check |",
        "|-----------|-----------|---------------|",
    ]
    for dim, meta in RUBRIC_DEFINITIONS.items():
        lines.append(f"| {meta['label']} (`{dim}`) | ≥ {meta['pass_threshold']} | {meta['description']} |")
    lines += [
        "",
        "## Feedback we track from humans",
        "",
        "1. **Rubric scores** (1–5) per dimension above",
        "2. **Decision agree** — agree / partial / disagree vs AI ACCEPT|REFER|DECLINE",
        "3. **Preferred decision** + change reason when disagree",
        "4. **Feedback tags** — recurring failure modes (e.g. `over_aggressive_accept`)",
        "5. **Freeform notes** — examiner-usable commentary",
        "6. **Blocking issues** — auto-derived from below-threshold scores",
        "",
        "## Production HITL (separate loop)",
        "",
        "Licensed UW sign-off also tracks override category, UW confidence, premium delta,",
        "and post-bind / loss-ratio calibration (`outcomes/override.py`, `outcomes/feedback.py`).",
        "",
    ]
    dest.write_text("\n".join(lines), encoding="utf-8")
    return str(dest)


if __name__ == "__main__":
    store = HITLEvalStore()
    seed_demo_reviews(store)
    export_rubric_card()
    summary = store.summary()
    print(json.dumps(summary.model_dump(), indent=2, default=str))
    print("LangSmith:", track_hitl_to_langsmith(summary))
