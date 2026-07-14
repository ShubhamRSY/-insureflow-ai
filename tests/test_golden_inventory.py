"""Ground-truth / golden dataset inventory tests."""

from __future__ import annotations

from evaluations.golden_dataset import golden_dataset
from evaluations.qa_ground_truth import (
    all_ground_truth_questions,
    field_questions_from_case,
    ground_truth_inventory,
)


def test_golden_dataset_has_thirteen_cases():
    cases = golden_dataset()
    assert len(cases) == 13
    assert all(c.name and c.acord_xml for c in cases)


def test_field_questions_generated_per_case():
    case = golden_dataset()[0]
    qs = field_questions_from_case(case)
    assert len(qs) >= 8
    assert all(q.expected_answer for q in qs)


def test_inventory_totals():
    inv = ground_truth_inventory()
    assert inv["maintained"] is True
    assert inv["insurance"]["golden_cases"] == 13
    assert inv["mortgage"]["golden_borrower_packages"] == 6
    assert inv["guideline_rag"]["ground_truth_questions"] == 8
    assert inv["totals"]["ground_truth_questions"] >= 13 * 8
    assert "interview_summary" in inv


def test_all_questions_unique_ids():
    qs = all_ground_truth_questions()
    ids = [q.question_id for q in qs]
    assert len(ids) == len(set(ids))
    assert len(qs) == ground_truth_inventory()["totals"]["ground_truth_questions"]
