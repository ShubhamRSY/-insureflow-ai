"""Tests for agent log performance analysis."""

from __future__ import annotations

import json
from pathlib import Path

from insureflow.analytics.agent_perf import (
    LOG_EXPLORER_QUERIES,
    analyze_audit_directory,
    analyze_jsonl_logs,
    seed_demo_agent_perf,
)


def test_analyze_jsonl_logs(tmp_path: Path) -> None:
    log = tmp_path / "agents.jsonl"
    rows = [
        {"agent": "risk_analyst", "level": "INFO", "duration_ms": 100, "findings_count": 3},
        {"agent": "risk_analyst", "level": "ERROR", "duration_ms": 200, "error": "timeout"},
        {"agent": "rag_agent", "level": "WARNING", "duration_ms": 50},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    result = analyze_jsonl_logs(log)
    assert result["ok"] is True
    assert result["total_lines"] == 3
    assert result["agents"]["risk_analyst"]["events"] == 2
    assert result["agents"]["risk_analyst"]["errors"] == 1
    assert result["agents"]["risk_analyst"]["error_rate"] == 0.5
    assert result["agents"]["risk_analyst"]["avg_duration_ms"] == 150.0
    assert result["agents"]["rag_agent"]["warnings"] == 1
    assert "cloudwatch_logs_insights" in result["log_explorers"]


def test_analyze_missing_path(tmp_path: Path) -> None:
    result = analyze_jsonl_logs(tmp_path / "missing.jsonl")
    assert result["ok"] is False
    assert result["agents"] == {}


def test_analyze_audit_directory(tmp_path: Path) -> None:
    (tmp_path / "run.jsonl").write_text(
        json.dumps({"agent": "triage_agent", "level": "INFO", "duration_ms": 80}) + "\n",
        encoding="utf-8",
    )
    result = analyze_audit_directory(tmp_path)
    assert result["ok"] is True
    assert result["files_scanned"] == 1
    assert "triage_agent" in result["agents"]
    assert "cloudwatch_agent_latency" in LOG_EXPLORER_QUERIES


def test_seed_demo_agent_perf() -> None:
    demo = seed_demo_agent_perf()
    assert demo["demo"] is True
    assert "risk_analyst" in demo["agents"]
    assert demo["agents"]["risk_analyst"]["avg_duration_ms"] > 0
