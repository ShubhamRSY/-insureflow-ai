"""Tests for agent release checklist and experiment store."""

from __future__ import annotations

from pathlib import Path

from evaluations.release_process import (
    ExperimentClass,
    ExperimentStage,
    ExperimentStore,
    checklist_payload,
    release_walkthrough,
    seed_demo_experiments,
)


def test_checklist_has_eleven_steps() -> None:
    payload = checklist_payload()
    assert len(payload["steps"]) == 11
    assert payload["steps"][0]["id"] == "classify"
    assert payload["steps"][-1]["id"] == "post_release_monitor"
    assert "prompt" in payload["experiment_classes"]
    assert "canary" in payload["stages"]


def test_experiment_lifecycle(tmp_path: Path) -> None:
    store = ExperimentStore(tmp_path)
    row = store.start_run(
        name="prompt-v2",
        experiment_class=ExperimentClass.PROMPT,
        hypothesis="Lower hallucination",
        params={"prompt_hash": "abc"},
    )
    assert row["run_id"].startswith("exp-")
    assert row["stage"] == "draft"
    updated = store.log_metrics(row["run_id"], {"precision": 0.9, "recall": 0.93})
    assert updated is not None
    assert updated["metrics"]["precision"] == 0.9
    promoted = store.promote(row["run_id"], ExperimentStage.CANARY)
    assert promoted is not None
    assert promoted["stage"] == "canary"
    got = store.get(row["run_id"])
    assert got is not None
    assert got["stage"] == "canary"


def test_seed_and_walkthrough(tmp_path: Path) -> None:
    store = ExperimentStore(tmp_path)
    assert seed_demo_experiments(store) == 4
    assert seed_demo_experiments(store) == 0
    summary = store.by_class_summary()
    assert summary["total_runs"] == 4
    assert "prompt" in summary["by_class"]
    walk = release_walkthrough()
    assert "classify → MLflow" in walk["summary"] or "MLflow" in walk["summary"]
