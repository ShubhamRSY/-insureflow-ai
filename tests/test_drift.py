"""Tests for agent/model drift detection and remediation playbook."""

from __future__ import annotations

from pathlib import Path

from evaluations.drift import (
    ChampionBaselineStore,
    DriftSeverity,
    default_champion_baseline,
    detect_drift,
    drift_policy_payload,
    remediation_playbook,
)


def test_no_drift_near_baseline(tmp_path: Path):
    store = ChampionBaselineStore(tmp_path / "champion.json")
    store.save(default_champion_baseline())
    report = detect_drift(
        {
            "precision": 0.91,
            "recall": 0.94,
            "hallucination_rate": 0.03,
        },
        baseline=store.load(),
    )
    assert report.status == DriftSeverity.NONE
    assert report.signals == []


def test_critical_precision_drop(tmp_path: Path):
    store = ChampionBaselineStore(tmp_path / "champion.json")
    base = default_champion_baseline()
    store.save(base)
    report = detect_drift(
        {
            "precision": 0.80,  # -0.11 from 0.91 → critical
            "recall": 0.94,
            "hallucination_rate": 0.03,
        },
        baseline=store.load(),
    )
    assert report.status == DriftSeverity.CRITICAL
    assert any(s.metric == "precision" for s in report.signals)
    assert any(s["action"] == "rollback_champion" for s in report.remediation)


def test_hallucination_rise_action(tmp_path: Path):
    base = default_champion_baseline()
    report = detect_drift(
        {"hallucination_rate": 0.07},  # +0.04 from 0.03 → action
        baseline=base,
    )
    assert report.status in {DriftSeverity.ACTION, DriftSeverity.CRITICAL}
    assert any(s.metric == "hallucination_rate" and s.direction == "worse" for s in report.signals)


def test_policy_mentions_vector_only_rag():
    p = drift_policy_payload()
    assert "SQL" in p["rag_clarification"] or "vector" in p["rag_clarification"].lower()
    assert "rollback" in " ".join(p["response"]).lower()


def test_remediation_watch_has_no_rollback():
    steps = remediation_playbook(DriftSeverity.WATCH, [])
    assert not any(s["action"] == "rollback_champion" for s in steps)
