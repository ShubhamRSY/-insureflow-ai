"""InsureFlow evaluations package.

Heavy deps (Ragas/Giskard) are imported lazily by their modules — keep this
init light so unit tests don't pull the full ML stack.
"""

from evaluations.golden_dataset import GoldenCase, golden_dataset
from evaluations.hitl_rubrics import (
    HITLEvalStore,
    HumanEvalReview,
    RUBRIC_DEFINITIONS,
    export_rubric_card,
    seed_demo_reviews,
    track_hitl_to_langsmith,
)
from evaluations.runner import run_all, run_case
from evaluations.scorer import score_all, score_case

__all__ = [
    "GoldenCase",
    "golden_dataset",
    "run_case",
    "run_all",
    "score_case",
    "score_all",
    "HITLEvalStore",
    "HumanEvalReview",
    "RUBRIC_DEFINITIONS",
    "export_rubric_card",
    "seed_demo_reviews",
    "track_hitl_to_langsmith",
]
