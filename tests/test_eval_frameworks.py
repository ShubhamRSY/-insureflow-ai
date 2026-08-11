"""CI-safe smoke tests for the four-framework eval matrix.

These run fully offline (no LLM API keys, no optional eval SDKs) and are cheap:
they verify the matrix registry, the deterministic offline scorers, the fast
suite run over sampled tasks, the SLA gate, and promptfoo config generation.
"""

from __future__ import annotations

import json

from evaluations.frameworks._common import cases_for_task, execute_case, offline_metric_score, run_task_cases
from evaluations.frameworks.promptfoo_suite import build_config
from evaluations.matrix import (
    FRAMEWORKS,
    TASKS,
    apply_sla_gate,
    matrix_inventory,
    task_index,
)

OFFLINE_TASKS = [t.task_id for t in TASKS if t.offline]


def test_matrix_registry() -> None:
    assert set(FRAMEWORKS) == {"ragas", "deepeval", "promptfoo", "phoenix"}
    assert len(TASKS) >= 11
    assert len({t.task_id for t in TASKS}) == len(TASKS)
    assert len(OFFLINE_TASKS) >= 6


def test_matrix_inventory_shape() -> None:
    inv = matrix_inventory()
    assert inv["task_count"] == len(TASKS)
    assert inv["frameworks"] == list(FRAMEWORKS)
    assert len(inv["sections"]) >= 8
    by_task = {t["task_id"]: t for t in inv["tasks"]}
    metrics = by_task["rag_guideline_qa"]["metrics"]
    assert any(m[1] == "context_recall" for m in metrics)
    assert any(m[1] == "answer_relevancy" and m[4] == 0.60 for m in metrics)


def test_offline_execute_and_score_sampled_tasks() -> None:
    for task_id in ("rating_accuracy", "reconciliation", "redaction_safety", "mcp_contract"):
        cases = cases_for_task(task_id)
        assert cases, f"no cases for {task_id}"
        io = execute_case(task_id, cases[0])
        assert io.task_id == task_id
        assert isinstance(offline_metric_score("phoenix", "numeric_ratio", io), float)


def test_sla_gate_passes_offline_fast_mode() -> None:
    from evaluations.frameworks.suite_runner import run_all

    payload = run_all(
        task_ids=["rating_accuracy", "reconciliation", "redaction_safety", "mcp_contract"],
        fast=True,
        output_path=None,
    )
    gate = payload["sla_gate"]
    assert gate["overall_pass"] is True
    assert gate["frameworks"]  # all frameworks produce a verdict


def test_apply_sla_gate_reports_mode() -> None:
    results = {"deepeval": {"rating_accuracy": {"numeric_tolerance": 0.99}}}
    gate = apply_sla_gate(results, offline=True)
    assert gate["overall_pass"] is True
    assert gate["frameworks"]["deepeval"]["pass"] is True


def test_promptfoo_config_generation_idempotent(tmp_path) -> None:
    cases = run_task_cases("redaction_safety")[:2]
    first = build_config("redaction_safety", cases)
    assert first.exists()
    content_a = first.read_text()
    second = build_config("redaction_safety", cases)
    assert second.read_text() == content_a


def test_fast_suite_writes_report(tmp_path) -> None:
    from evaluations.frameworks.suite_runner import run_all

    out = tmp_path / "eval.json"
    run_all(
        task_ids=["mcp_contract", "agent_tool_selection"],
        fast=True,
        output_path=str(out),
    )
    assert out.exists()
    data = json.loads(out.read_text())
    assert "scores" in data
    assert "sla_gate" in data
    assert data["mode"] == "fast"


def test_task_index_covers_all_frameworks() -> None:
    idx = task_index()
    for t in TASKS:
        assert idx[t.task_id] is t
        assert all(fw in FRAMEWORKS for fw in t.frameworks)
