"""Tests for LangSmith cloud eval tracker (offline / mocked)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from evaluations.cloud_tracker import CloudEvalTracker, track_report


def test_tracker_status_disabled_without_key(monkeypatch, tmp_path):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("EVAL_CLOUD_CACHE_DIR", str(tmp_path))
    tracker = CloudEvalTracker(api_key="")
    assert tracker.is_enabled() is False
    status = tracker.status()
    assert status["provider"] == "langsmith"
    assert status["enabled"] is False
    assert status["dashboard"] == "https://smith.langchain.com"


def test_log_metrics_caches_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("EVAL_CLOUD_CACHE_DIR", str(tmp_path))
    tracker = CloudEvalTracker(api_key="")
    result = tracker.log_metrics(
        run_name="unit-test-metrics",
        metrics={"precision": 0.91, "recall": 0.94},
        metadata={"suite": "unit"},
    )
    assert result.enabled is False
    assert result.local_path is not None
    payload = json.loads(open(result.local_path, encoding="utf-8").read())
    assert payload["metrics"]["precision"] == 0.91
    assert payload["run_name"] == "unit-test-metrics"


def test_log_metrics_uploads_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("EVAL_CLOUD_CACHE_DIR", str(tmp_path))
    fake_run = MagicMock()
    fake_run.id = "run-abc-123"
    fake_client = MagicMock()
    fake_client.create_run.return_value = fake_run

    tracker = CloudEvalTracker(api_key="lsv2_test_key", project="insureflow-evals")
    with patch.object(tracker, "_client", return_value=fake_client):
        result = tracker.log_metrics(
            run_name="unit-upload",
            metrics={"precision": 0.88, "recall": 0.92, "skip_me": None},
        )

    assert result.enabled is True
    assert result.run_id == "run-abc-123"
    assert result.scores_logged == 2
    fake_client.create_run.assert_called_once()
    assert fake_client.create_feedback.call_count == 2


def test_track_report_maps_summary_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("EVAL_CLOUD_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    report = {
        "report_title": "test",
        "generated_at": "2026-07-14T00:00:00Z",
        "summary": {
            "overall_verdict": "DEPLOYMENT-READY",
            "precision": 0.9,
            "recall": 0.95,
            "hallucination_rate": 0.02,
            "ragas_quality_score": 0.87,
            "giskard_issues_found": 0,
        },
        "sections": {
            "rag_quality": {
                "metrics": {
                    "faithfulness": 0.9,
                    "answer_relevancy": 0.85,
                    "context_precision": 0.8,
                    "context_recall": 0.88,
                }
            }
        },
        "recommendations": [],
    }
    cloud = track_report(report)
    assert cloud["enabled"] is False
    assert cloud["provider"] == "langsmith"
    assert cloud["local_path"]
    cached = json.loads(open(cloud["local_path"], encoding="utf-8").read())
    assert cached["metrics"]["precision"] == 0.9
    assert cached["metrics"]["faithfulness"] == 0.9


def test_enable_runtime_tracing_sets_env(monkeypatch):
    tracker = CloudEvalTracker(api_key="lsv2_key", project="insureflow-evals", tracing_enabled=True)
    assert tracker.enable_runtime_tracing() is True
    assert monkeypatch is not None
    import os

    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_PROJECT"] == "insureflow-evals"
