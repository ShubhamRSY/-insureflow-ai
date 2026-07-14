"""Tests for quality gate thresholds and flagging."""

from __future__ import annotations

from evaluations.quality_gates import QUALITY_GATES, apply_quality_gates, gates_from_report_summary


def test_gates_catalog_has_core_metrics():
    names = {g.metric for g in QUALITY_GATES}
    assert {"precision", "recall", "hallucination_rate", "ragas_quality_score", "hitl_case_pass_rate"} <= names


def test_pass_when_above_thresholds():
    result = apply_quality_gates(
        {
            "precision": 0.91,
            "recall": 0.94,
            "hallucination_rate": 0.03,
            "ragas_quality_score": 0.85,
            "hitl_case_pass_rate": 0.9,
            "hitl_agree_rate": 0.88,
        }
    )
    assert result["verdict"] in {"PASS", "FLAGGED"}  # may flag optional Ragas component skips
    assert result["blocks"] == 0


def test_block_when_precision_low():
    result = apply_quality_gates({"precision": 0.70, "recall": 0.95, "hallucination_rate": 0.02})
    assert result["verdict"] == "BLOCKED"
    assert result["blocks"] >= 1
    failed = [g for g in result["gates"] if g["status"] == "fail"]
    assert any(g["metric"] == "precision" for g in failed)


def test_flag_when_faithfulness_low_but_core_ok():
    result = apply_quality_gates(
        {
            "precision": 0.90,
            "recall": 0.92,
            "hallucination_rate": 0.04,
            "faithfulness": 0.50,
            "hitl_case_pass_rate": 0.85,
        }
    )
    assert result["verdict"] == "FLAGGED"
    assert result["flags"] >= 1


def test_gates_from_report_summary():
    out = gates_from_report_summary(
        {"precision": 0.9, "recall": 0.91, "hallucination_rate": 0.04, "ragas_quality_score": 0.83},
        ragas_metrics={"faithfulness": {"avg": 0.81}},
    )
    assert "verdict" in out
    assert out["automation"]["unit_tests"].startswith("automated")
