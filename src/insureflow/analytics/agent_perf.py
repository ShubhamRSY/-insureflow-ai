"""Agent performance extraction from structured logs / audit trails.

Automation: run after pipelines or on cadence; feeds eval trend store + APIs.
Log explorers: CloudWatch Logs Insights (infra) + LangSmith (LLM/agent traces).
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LOG_DIR = Path(os.getenv("AGENT_PERF_LOG_DIR", "./audit_logs"))


# CloudWatch Logs Insights templates (copy into AWS Console → Logs Insights)
LOG_EXPLORER_QUERIES: dict[str, str] = {
    "cloudwatch_agent_errors": """
fields @timestamp, agent, message, bundle_id, level
| filter logger like /insureflow.audit/ or logger like /insureflow.agents/
| filter level = "ERROR" or level = "WARNING"
| sort @timestamp desc
| limit 100
""".strip(),
    "cloudwatch_agent_latency": """
fields @timestamp, agent, duration_ms, bundle_id, message
| filter ispresent(duration_ms)
| stats avg(duration_ms) as avg_ms, pct(duration_ms, 95) as p95_ms, count() as n by agent
| sort avg_ms desc
""".strip(),
    "cloudwatch_pipeline_throughput": """
fields @timestamp, message, bundle_id
| filter message like /SYNTHESIS/ or message like /completed/ or message like /Bundle/
| stats count() as events by bin(5m)
""".strip(),
    "langsmith": "Use LangSmith project 'insureflow-evals' — Runs explorer + dashboards for LLM latency, token usage, feedback scores.",
}


def analyze_jsonl_logs(path: Path | str) -> dict[str, Any]:
    """Parse JSONL agent/pipeline logs into performance metrics."""
    p = Path(path)
    if not p.exists():
        return {"ok": False, "error": f"log path not found: {p}", "agents": {}}

    by_agent: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "events": 0,
        "errors": 0,
        "warnings": 0,
        "durations_ms": [],
        "findings": 0,
    })
    total_lines = 0
    parse_errors = 0

    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        total_lines += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            # fallback: plain text with agent= name
            m = re.search(r"agent[=:](\w+)", line, re.I)
            if m:
                by_agent[m.group(1)]["events"] += 1
                if re.search(r"error|fail", line, re.I):
                    by_agent[m.group(1)]["errors"] += 1
            else:
                parse_errors += 1
            continue

        agent = str(row.get("agent") or row.get("agent_name") or row.get("logger", "unknown"))
        if "." in agent:
            agent = agent.split(".")[-1]
        stats = by_agent[agent]
        stats["events"] += 1
        level = str(row.get("level", "")).upper()
        if level == "ERROR" or row.get("error"):
            stats["errors"] += 1
        if level == "WARNING":
            stats["warnings"] += 1
        dur = row.get("duration_ms") or row.get("latency_ms")
        if dur is not None:
            try:
                stats["durations_ms"].append(float(dur))
            except (TypeError, ValueError):
                pass
        findings = row.get("findings_count")
        if findings is not None:
            try:
                stats["findings"] += int(findings)
            except (TypeError, ValueError):
                pass

    agents_out: dict[str, Any] = {}
    for name, s in by_agent.items():
        durs = s["durations_ms"]
        agents_out[name] = {
            "events": s["events"],
            "errors": s["errors"],
            "warnings": s["warnings"],
            "error_rate": round(s["errors"] / s["events"], 4) if s["events"] else 0.0,
            "findings": s["findings"],
            "avg_duration_ms": round(sum(durs) / len(durs), 2) if durs else None,
            "p95_duration_ms": round(sorted(durs)[int(0.95 * (len(durs) - 1))], 2) if len(durs) >= 2 else (durs[0] if durs else None),
        }

    return {
        "ok": True,
        "source": str(p),
        "total_lines": total_lines,
        "parse_errors": parse_errors,
        "agents": agents_out,
        "analyzed_at": datetime.now(tz=timezone.utc).isoformat(),
        "log_explorers": {
            "cloudwatch_logs_insights": "AWS Console → CloudWatch → Logs Insights (queries in LOG_EXPLORER_QUERIES)",
            "langsmith": "https://smith.langchain.com — agent/LLM trace explorer",
        },
    }


def analyze_audit_directory(base: Path | str | None = None) -> dict[str, Any]:
    """Scan audit_logs for JSON artifacts and summarize agent-ish performance signals."""
    root = Path(base or DEFAULT_LOG_DIR)
    if not root.exists():
        return {"ok": False, "error": f"audit dir missing: {root}", "files_scanned": 0, "agents": {}}

    jsonl_files = list(root.rglob("*.jsonl")) + list(root.rglob("*.log"))
    merged: dict[str, Any] = {"ok": True, "files_scanned": 0, "agents": {}, "sources": []}
    for f in jsonl_files[:50]:
        part = analyze_jsonl_logs(f)
        merged["files_scanned"] += 1
        merged["sources"].append(str(f))
        for agent, stats in (part.get("agents") or {}).items():
            cur = merged["agents"].setdefault(
                agent,
                {"events": 0, "errors": 0, "warnings": 0, "findings": 0, "durations_ms": []},
            )
            cur["events"] += stats["events"]
            cur["errors"] += stats["errors"]
            cur["warnings"] += stats["warnings"]
            cur["findings"] += stats["findings"]
            if stats.get("avg_duration_ms") is not None:
                cur["durations_ms"].append(stats["avg_duration_ms"])

    # finalize
    out_agents = {}
    for name, s in merged["agents"].items():
        durs = s.get("durations_ms") or []
        out_agents[name] = {
            "events": s["events"],
            "errors": s["errors"],
            "warnings": s["warnings"],
            "error_rate": round(s["errors"] / s["events"], 4) if s["events"] else 0.0,
            "findings": s["findings"],
            "avg_duration_ms": round(sum(durs) / len(durs), 2) if durs else None,
        }
    merged["agents"] = out_agents
    merged["log_explorers"] = {
        "primary": "Amazon CloudWatch Logs Insights",
        "llm_traces": "LangSmith Runs explorer",
        "queries": LOG_EXPLORER_QUERIES,
    }
    merged["automation"] = (
        "Automated: JSON logs → analyze_audit_directory on nightly eval job; "
        "metrics appended to eval trend store; CloudWatch metric emit optional."
    )
    return merged


def seed_demo_agent_perf() -> dict[str, Any]:
    """Demo agent performance metrics so the dashboard has data out of the box."""
    return {
        "ok": True,
        "demo": True,
        "agents": {
            "triage_agent": {"events": 42, "errors": 0, "warnings": 1, "error_rate": 0.0, "findings": 12, "avg_duration_ms": 180.0},
            "risk_analyst": {"events": 40, "errors": 1, "warnings": 2, "error_rate": 0.025, "findings": 86, "avg_duration_ms": 920.0},
            "loss_run_analyst": {"events": 38, "errors": 0, "warnings": 0, "error_rate": 0.0, "findings": 54, "avg_duration_ms": 640.0},
            "compliance_agent": {"events": 38, "errors": 0, "warnings": 1, "error_rate": 0.0, "findings": 21, "avg_duration_ms": 410.0},
            "uw_decision_agent": {"events": 36, "errors": 0, "warnings": 0, "error_rate": 0.0, "findings": 36, "avg_duration_ms": 1100.0},
            "rag_agent": {"events": 36, "errors": 2, "warnings": 0, "error_rate": 0.0556, "findings": 0, "avg_duration_ms": 350.0},
        },
        "log_explorers": {
            "primary": "Amazon CloudWatch Logs Insights",
            "llm_traces": "LangSmith Runs explorer",
            "queries": LOG_EXPLORER_QUERIES,
        },
        "automation": "Nightly scheduled job + optional CloudWatch metrics; demo seed when no live logs.",
    }
