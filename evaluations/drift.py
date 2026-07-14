"""Agent / model drift detection against a champion baseline.

We do **not** use a secondary SQL retrieval path for RAG — vector search is primary
(keyword + knowledge-graph are non-SQL fallbacks only when vector is weak/empty).

Drift is addressed operationally:
1. Detect vs champion baseline (metric + behavioral + decision)
2. Severity → quality-gate BLOCK / FLAGGED
3. Open ``regression`` experiment in MLflow / experiment store
4. Rollback challenger → last champion registry snapshot when critical
5. Fix (prompt / LLM config / RAG knobs) → re-run golden eval → re-promote
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_BASELINE_PATH = Path(os.getenv("EVAL_BASELINE_PATH", "./evaluation_baselines/champion.json"))
DEFAULT_DRIFT_LOG = Path(os.getenv("EVAL_DRIFT_LOG", "./evaluation_baselines/drift_events.jsonl"))


class DriftKind(str, Enum):
    METRIC = "metric"  # precision/recall/hallucination/RAG/HITL vs baseline
    BEHAVIORAL = "behavioral"  # latency, agent error rate from logs
    DECISION = "decision"  # UW override rate / decision mix shift
    OUTPUT = "output"  # distribution of findings volume / severity tags


class DriftSeverity(str, Enum):
    NONE = "none"
    WATCH = "watch"  # soft drift — monitor
    ACTION = "action"  # open regression experiment
    CRITICAL = "critical"  # block release / rollback champion


# Absolute delta thresholds from champion baseline
DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "precision": {"watch": 0.03, "action": 0.05, "critical": 0.08},  # drop
    "recall": {"watch": 0.03, "action": 0.05, "critical": 0.08},
    "hallucination_rate": {"watch": 0.02, "action": 0.03, "critical": 0.05},  # rise
    "ragas_quality_score": {"watch": 0.03, "action": 0.05, "critical": 0.08},
    "hitl_case_pass_rate": {"watch": 0.05, "action": 0.08, "critical": 0.12},
    "hitl_agree_rate": {"watch": 0.05, "action": 0.08, "critical": 0.12},
    "avg_agent_error_rate": {"watch": 0.01, "action": 0.02, "critical": 0.04},
    "avg_agent_latency_ms": {"watch": 150, "action": 300, "critical": 600},
    "uw_override_rate": {"watch": 0.05, "action": 0.10, "critical": 0.15},
}

# Metrics where higher is worse
HIGHER_IS_WORSE = {
    "hallucination_rate",
    "avg_agent_error_rate",
    "avg_agent_latency_ms",
    "uw_override_rate",
}


@dataclass
class DriftSignal:
    metric: str
    kind: DriftKind
    baseline: float
    current: float
    delta: float
    severity: DriftSeverity
    direction: str  # "worse" | "better" | "flat"


@dataclass
class DriftReport:
    status: DriftSeverity
    signals: list[DriftSignal] = field(default_factory=list)
    champion_version: str = ""
    compared_at: str = ""
    remediation: list[dict[str, Any]] = field(default_factory=list)
    interview_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "champion_version": self.champion_version,
            "compared_at": self.compared_at,
            "signals": [
                {
                    "metric": s.metric,
                    "kind": s.kind.value,
                    "baseline": s.baseline,
                    "current": s.current,
                    "delta": s.delta,
                    "severity": s.severity.value,
                    "direction": s.direction,
                }
                for s in self.signals
            ],
            "actionable_signals": [s.metric for s in self.signals if s.severity != DriftSeverity.NONE],
            "remediation": self.remediation,
            "interview_summary": self.interview_summary,
            "rag_note": ("Primary retrieval is vector-only (no secondary SQL retrieval). Keyword/KG are non-SQL fallbacks when vector similarity is weak/empty."),
        }


def _severity_for(metric: str, delta_worse: float, thresholds: dict[str, dict[str, float]]) -> DriftSeverity:
    t = thresholds.get(metric) or {"watch": 0.03, "action": 0.05, "critical": 0.08}
    if delta_worse >= t["critical"]:
        return DriftSeverity.CRITICAL
    if delta_worse >= t["action"]:
        return DriftSeverity.ACTION
    if delta_worse >= t["watch"]:
        return DriftSeverity.WATCH
    return DriftSeverity.NONE


def _kind_for(metric: str) -> DriftKind:
    if metric in {"avg_agent_error_rate", "avg_agent_latency_ms"}:
        return DriftKind.BEHAVIORAL
    if metric in {"uw_override_rate"}:
        return DriftKind.DECISION
    return DriftKind.METRIC


def default_champion_baseline() -> dict[str, Any]:
    """Seed champion metrics (from quality-gate green / demo production)."""
    return {
        "version": "champion-v1",
        "promoted_at": "2026-06-01T00:00:00+00:00",
        "registry_snapshot_id": "snap-champion-seed",
        "metrics": {
            "precision": 0.91,
            "recall": 0.94,
            "hallucination_rate": 0.03,
            "ragas_quality_score": 0.86,
            "hitl_case_pass_rate": 0.88,
            "hitl_agree_rate": 0.85,
            "avg_agent_error_rate": 0.018,
            "avg_agent_latency_ms": 650.0,
            "uw_override_rate": 0.12,
        },
        "source": "seed",
    }


class ChampionBaselineStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or DEFAULT_BASELINE_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            base = default_champion_baseline()
            self.save(base)
            return base
        return cast(dict[str, Any], json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, baseline: dict[str, Any]) -> dict[str, Any]:
        baseline = {**baseline, "updated_at": datetime.now(tz=timezone.utc).isoformat()}
        self.path.write_text(json.dumps(baseline, indent=2, default=str), encoding="utf-8")
        return baseline

    def promote_from_metrics(
        self,
        metrics: dict[str, float],
        version: str | None = None,
        registry_snapshot_id: str = "",
    ) -> dict[str, Any]:
        current = self.load()
        merged = {**(current.get("metrics") or {}), **{k: float(v) for k, v in metrics.items() if v is not None}}
        baseline = {
            "version": version or f"champion-{uuid4().hex[:8]}",
            "promoted_at": datetime.now(tz=timezone.utc).isoformat(),
            "registry_snapshot_id": registry_snapshot_id or current.get("registry_snapshot_id", ""),
            "metrics": merged,
            "source": "promoted",
        }
        return self.save(baseline)


def remediation_playbook(status: DriftSeverity, signals: list[DriftSignal]) -> list[dict[str, Any]]:
    """Concrete steps we take when drift is found during tests / nightly."""
    steps: list[dict[str, Any]] = [
        {
            "step": 1,
            "action": "confirm",
            "detail": "Re-run golden scorer + Ragas on the same commit; exclude flaky LLM variance (temp=0).",
        },
        {
            "step": 2,
            "action": "classify_drift",
            "detail": (f"Tag DriftKind from signals: {sorted({s.kind.value for s in signals}) or ['none']} — metric vs behavioral vs decision."),
        },
    ]
    if status in {DriftSeverity.ACTION, DriftSeverity.CRITICAL}:
        steps.append(
            {
                "step": 3,
                "action": "open_regression_experiment",
                "detail": ("Start ExperimentClass.REGRESSION in MLflow /experiments store; freeze challenger; do not promote while gates BLOCKED."),
            }
        )
    if status == DriftSeverity.CRITICAL:
        steps.append(
            {
                "step": 4,
                "action": "rollback_champion",
                "detail": ("Restore last approved registry snapshot + MLflow Production alias; canary traffic back to previous champion prompts/LLM config."),
            }
        )
        steps.append(
            {
                "step": 5,
                "action": "root_cause",
                "detail": ("Diff prompt hash / LLM model / RAG top-k / provider change / guideline pack; check LangSmith traces + CloudWatch agent error spikes."),
            }
        )
    else:
        steps.append(
            {
                "step": 3,
                "action": "root_cause",
                "detail": "Compare trend charts + LangSmith traces vs last champion run; check provider model updates.",
            }
        )
    steps.append(
        {
            "step": 6 if status == DriftSeverity.CRITICAL else 4,
            "action": "fix_and_revalidate",
            "detail": ("Patch (prompt tighten / model pin / RAG knobs) → full release checklist → quality gates PASS → HITL sample → re-promote champion baseline."),
        }
    )
    steps.append(
        {
            "step": 7 if status == DriftSeverity.CRITICAL else 5,
            "action": "raise_monitoring",
            "detail": "7-day heightened watch on Eval Trends + override rate; weekly HITL spot-check.",
        }
    )
    return steps


def detect_drift(
    current_metrics: dict[str, Any],
    baseline: dict[str, Any] | None = None,
    thresholds: dict[str, dict[str, float]] | None = None,
) -> DriftReport:
    store = ChampionBaselineStore()
    base = baseline or store.load()
    base_metrics = base.get("metrics") or {}
    thr = thresholds or DEFAULT_THRESHOLDS
    signals: list[DriftSignal] = []

    for metric, base_val in base_metrics.items():
        if metric not in current_metrics or current_metrics[metric] is None:
            continue
        try:
            cur = float(current_metrics[metric])
            b = float(base_val)
        except (TypeError, ValueError):
            continue
        raw_delta = cur - b
        worse_delta = raw_delta if metric in HIGHER_IS_WORSE else (b - cur)
        if worse_delta < 0:
            direction = "better"
            sev = DriftSeverity.NONE
        elif worse_delta == 0:
            direction = "flat"
            sev = DriftSeverity.NONE
        else:
            direction = "worse"
            sev = _severity_for(metric, worse_delta, thr)
        if sev == DriftSeverity.NONE and direction == "worse":
            # still record tiny drifts? skip noise
            continue
        if sev == DriftSeverity.NONE and direction != "worse":
            continue
        signals.append(
            DriftSignal(
                metric=metric,
                kind=_kind_for(metric),
                baseline=round(b, 4),
                current=round(cur, 4),
                delta=round(raw_delta, 4),
                severity=sev,
                direction=direction,
            )
        )

    # also flag better large moves? skip — drift playbook is about degradation

    order = {DriftSeverity.CRITICAL: 3, DriftSeverity.ACTION: 2, DriftSeverity.WATCH: 1, DriftSeverity.NONE: 0}
    status = DriftSeverity.NONE
    for s in signals:
        if order[s.severity] > order[status]:
            status = s.severity

    rem = remediation_playbook(status, signals)
    summary = (
        f"Drift status={status.value}. Compare nightly/current metrics to champion baseline "
        f"({base.get('version')}). On ACTION/CRITICAL: open regression experiment, "
        f"{'rollback champion, ' if status == DriftSeverity.CRITICAL else ''}"
        f"root-cause (prompt/LLM/RAG), re-validate through quality gates, re-promote."
    )
    return DriftReport(
        status=status,
        signals=signals,
        champion_version=str(base.get("version", "")),
        compared_at=datetime.now(tz=timezone.utc).isoformat(),
        remediation=rem,
        interview_summary=summary,
    )


def log_drift_event(report: DriftReport, path: Path | str | None = None) -> None:
    p = Path(path or DEFAULT_DRIFT_LOG)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(report.to_dict(), default=str) + "\n")


def detect_from_trends(lookback: int = 5) -> DriftReport:
    """Compare latest trend point(s) average to champion baseline."""
    from evaluations.trend_store import EvalTrendStore, seed_demo_trends

    store = EvalTrendStore()
    seed_demo_trends(store)
    rows = store.list_rows(limit=lookback)
    if not rows:
        return detect_drift({})
    # average last N metric dicts
    keys: set[str] = set()
    for r in rows:
        keys |= set((r.get("metrics") or {}).keys())
    avg: dict[str, float] = {}
    for k in keys:
        vals = []
        for r in rows:
            v = (r.get("metrics") or {}).get(k)
            if v is not None:
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
        if vals:
            avg[k] = sum(vals) / len(vals)
    report = detect_drift(avg)
    if report.status != DriftSeverity.NONE:
        log_drift_event(report)
    return report


def maybe_open_regression_experiment(report: DriftReport) -> dict[str, Any] | None:
    """Auto-open a REGRESSION experiment when drift is ACTION/CRITICAL."""
    if report.status not in {DriftSeverity.ACTION, DriftSeverity.CRITICAL}:
        return None
    try:
        from evaluations.release_process import ExperimentClass, ExperimentStage, ExperimentStore

        store = ExperimentStore()
        row = store.start_run(
            name=f"drift-{report.status.value}-{report.champion_version}",
            experiment_class=ExperimentClass.REGRESSION,
            hypothesis=f"Investigate agent drift vs {report.champion_version}: {[s.metric for s in report.signals]}",
            params={"champion_version": report.champion_version, "status": report.status.value},
            tags={"drift": "true", "severity": report.status.value},
            stage=ExperimentStage.OFFLINE_EVAL,
        )
        store.log_metrics(
            row["run_id"],
            {s.metric: s.current for s in report.signals},
        )
        return row
    except Exception as exc:
        logger.warning("Could not open regression experiment: %s", exc)
        return None


def drift_policy_payload() -> dict[str, Any]:
    return {
        "champion_baseline": ChampionBaselineStore().load(),
        "thresholds": DEFAULT_THRESHOLDS,
        "kinds": [k.value for k in DriftKind],
        "severities": [s.value for s in DriftSeverity],
        "detection": [
            "Nightly golden metrics vs champion baseline",
            "Eval Trends lookback (detect_from_trends)",
            "Behavioral: agent error/latency from log analyzer",
            "Decision: UW override-rate shift",
        ],
        "response": [
            "Confirm with temp=0 re-run",
            "Open REGRESSION experiment (MLflow)",
            "CRITICAL → rollback to champion registry snapshot",
            "Root-cause prompt/LLM/RAG/provider",
            "Fix → quality gates → HITL → re-promote baseline",
        ],
        "rag_clarification": ("No secondary SQL retrieval for guidelines — vector DB is primary; keyword + knowledge graph are fallbacks only."),
    }
