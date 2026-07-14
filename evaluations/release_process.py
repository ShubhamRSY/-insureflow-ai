"""Agent release checklist + experiment taxonomy (MLflow-compatible).

Walkthrough for a new agent/prompt/LLM/RAG release:

1. Classify the change (experiment class)
2. Log an MLflow (or local) experiment run with params + metrics
3. Run offline evals → quality gates
4. HITL sample review
5. Registry draft → review → approve
6. Shadow/canary → champion promotion
7. Post-release trend + log monitoring

``MLFLOW_TRACKING_URI`` enables real MLflow; without it we persist under
``evaluation_experiments/`` so CI and demos stay offline-friendly.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_EXPERIMENT_DIR = Path(os.getenv("EVAL_EXPERIMENT_DIR", "./evaluation_experiments"))
DEFAULT_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "insureflow-agent-releases")


class ExperimentClass(str, Enum):
    """How we classify release experiments."""

    PROMPT = "prompt"  # system/user prompt variants
    LLM_CONFIG = "llm_config"  # model, temp, max_tokens, provider
    RAG = "rag"  # retrieval k, hybrid vs vector, KG weights
    AGENT_LOGIC = "agent_logic"  # routing, specialist rules, tools
    TOOLING = "tooling"  # tool schemas / MCP bindings
    EVAL_BASELINE = "eval_baseline"  # establish or refresh golden baselines
    REGRESSION = "regression"  # fix after incident / gate failure
    CANARY = "canary"  # production shadow / % traffic comparison
    COMPLIANCE = "compliance"  # guideline / rule pack change


class ExperimentStage(str, Enum):
    """Promotion path — MLflow-style stages + our UW registry."""

    DRAFT = "draft"
    OFFLINE_EVAL = "offline_eval"
    HITL_REVIEW = "hitl_review"
    REGISTRY_REVIEW = "registry_review"
    SHADOW = "shadow"
    CANARY = "canary"
    CHAMPION = "champion"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    REJECTED = "rejected"


# Ordered checklist for a full agent release
RELEASE_CHECKLIST: list[dict[str, Any]] = [
    {
        "step": 1,
        "id": "classify",
        "title": "Classify the change",
        "owner": "engineer",
        "required": True,
        "detail": ("Pick ExperimentClass (prompt / llm_config / rag / agent_logic / tooling / eval_baseline / regression / canary / compliance) and name the hypothesis."),
        "artifacts": ["experiment class", "hypothesis string", "linked registry draft id"],
    },
    {
        "step": 2,
        "id": "log_experiment",
        "title": "Open MLflow experiment run",
        "owner": "engineer",
        "required": True,
        "detail": ("Start a run under experiment 'insureflow-agent-releases'. Log params (model, temp, prompt hash, RAG k, hybrid flag) and tags (class, git sha)."),
        "artifacts": ["mlflow_run_id", "params", "tags"],
    },
    {
        "step": 3,
        "id": "unit_regression",
        "title": "Unit + pipeline regression (pytest)",
        "owner": "ci",
        "required": True,
        "detail": "PR CI: agents, pipeline, parsers, bank security posture.",
        "artifacts": ["pytest pass rate"],
    },
    {
        "step": 4,
        "id": "golden_offline",
        "title": "Golden offline eval (precision / recall / hallucination)",
        "owner": "ci",
        "required": True,
        "detail": "Run evaluations.scorer on 13 insurance golden cases (+ mortgage gold).",
        "artifacts": ["evaluation_scores.json", "trend_store append"],
    },
    {
        "step": 5,
        "id": "ragas_giskard",
        "title": "RAG quality (Ragas) + adversarial scan (Giskard)",
        "owner": "ci",
        "required": True,
        "detail": "Weekly or pre-release: Ragas faithfulness/relevancy/context; Giskard high-sev count.",
        "artifacts": ["ragas_scores.json", "giskard_scan.json"],
    },
    {
        "step": 6,
        "id": "quality_gates",
        "title": "Quality gates (BLOCK / FLAG / PASS)",
        "owner": "ci",
        "required": True,
        "detail": ("BLOCK if precision <85%, recall <90%, hallucination >5%, RAG <80%, HITL pass <80%. No champion promotion on BLOCKED."),
        "artifacts": ["gate_verdict"],
    },
    {
        "step": 7,
        "id": "hitl_sample",
        "title": "HITL rubric sample (≥5 cases)",
        "owner": "licensed_uw",
        "required": True,
        "detail": "Human scores on 8 rubric dimensions + agree/disagree vs agent decision.",
        "artifacts": ["hitl summary", "LangSmith feedback"],
    },
    {
        "step": 8,
        "id": "registry_approve",
        "title": "Model registry: submit → compliance approve",
        "owner": "compliance",
        "required": True,
        "detail": "draft → review → approved for prompt/llm_config/agent_logic/compliance_rule.",
        "artifacts": ["registry entry_id", "checksum", "diff"],
    },
    {
        "step": 9,
        "id": "shadow_canary",
        "title": "Shadow / canary deployment",
        "owner": "platform",
        "required": True,
        "detail": ("Run challenger alongside champion on duplicate traffic or % canary. Compare agent latency/error from CloudWatch + LangSmith; append trends."),
        "artifacts": ["canary experiment run", "agent_perf delta"],
    },
    {
        "step": 10,
        "id": "promote_champion",
        "title": "Promote champion + registry snapshot",
        "owner": "admin",
        "required": True,
        "detail": "MLflow stage → Production; registry snapshot for audit; roll forward version labels.",
        "artifacts": ["snapshot_id", "mlflow production alias"],
    },
    {
        "step": 11,
        "id": "post_release_monitor",
        "title": "Post-release monitoring",
        "owner": "uw_ops",
        "required": True,
        "detail": ("Watch Eval Trends + override analytics for 7 days; weekly HITL spot-checks; monthly loss/bind calibration."),
        "artifacts": ["eval trends", "override patterns", "loss calibration"],
    },
]


def checklist_payload() -> dict[str, Any]:
    return {
        "name": "InsureFlow / Rytera agent release checklist",
        "experiment_classes": [c.value for c in ExperimentClass],
        "stages": [s.value for s in ExperimentStage],
        "promotion_path": [s.value for s in ExperimentStage if s not in {ExperimentStage.ARCHIVED, ExperimentStage.REJECTED}],
        "steps": RELEASE_CHECKLIST,
        "tracking": {
            "primary": "MLflow (params, metrics, stages) when MLFLOW_TRACKING_URI is set",
            "fallback": "local evaluation_experiments/*.jsonl",
            "eval_cloud": "LangSmith insureflow-evals",
            "log_explorers": ["CloudWatch Logs Insights", "LangSmith Runs"],
            "registry": "insureflow.registry (draft → review → approved)",
        },
        "quality_gates_ref": "GET /evaluations/quality-gates",
    }


class ExperimentStore:
    """Local experiment log + optional MLflow client."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or DEFAULT_EXPERIMENT_DIR) / "runs.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.experiment_name = DEFAULT_EXPERIMENT_NAME

    def _mlflow_client(self) -> Any:
        uri = os.getenv("MLFLOW_TRACKING_URI", "").strip()
        if not uri:
            return None
        try:
            import mlflow

            mlflow.set_tracking_uri(uri)
            mlflow.set_experiment(self.experiment_name)
            return mlflow
        except Exception as exc:
            logger.warning("MLflow unavailable (%s) — using local experiment store", exc)
            return None

    def start_run(
        self,
        *,
        name: str,
        experiment_class: ExperimentClass | str,
        hypothesis: str = "",
        params: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
        stage: ExperimentStage | str = ExperimentStage.DRAFT,
        registry_entry_id: str = "",
    ) -> dict[str, Any]:
        cls = ExperimentClass(experiment_class) if not isinstance(experiment_class, ExperimentClass) else experiment_class
        st = ExperimentStage(stage) if not isinstance(stage, ExperimentStage) else stage
        run_id = f"exp-{uuid4().hex[:12]}"
        params = params or {}
        tags = {
            "experiment_class": cls.value,
            "stage": st.value,
            **(tags or {}),
        }
        row: dict[str, Any] = {
            "run_id": run_id,
            "name": name,
            "experiment_class": cls.value,
            "hypothesis": hypothesis,
            "stage": st.value,
            "params": params,
            "metrics": {},
            "tags": tags,
            "registry_entry_id": registry_entry_id,
            "mlflow_run_id": None,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            "status": "running",
        }

        mlflow = self._mlflow_client()
        if mlflow is not None:
            try:
                with mlflow.start_run(run_name=name) as active:
                    row["mlflow_run_id"] = active.info.run_id
                    mlflow.log_params({k: str(v)[:250] for k, v in params.items()})
                    mlflow.set_tags(tags)
                    if hypothesis:
                        mlflow.set_tag("hypothesis", hypothesis[:250])
            except Exception as exc:
                logger.warning("MLflow start_run failed: %s", exc)

        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
        return row

    def _rewrite(self, rows: list[dict[str, Any]]) -> None:
        with self.path.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, default=str) + "\n")

    def list_runs(self, experiment_class: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if experiment_class and row.get("experiment_class") != experiment_class:
                continue
            rows.append(row)
        return rows[-limit:]

    def get(self, run_id: str) -> dict[str, Any] | None:
        for row in self.list_runs(limit=500):
            if row.get("run_id") == run_id:
                return row
        return None

    def log_metrics(self, run_id: str, metrics: dict[str, float]) -> dict[str, Any] | None:
        rows = self.list_runs(limit=500)
        target = None
        for row in rows:
            if row.get("run_id") == run_id:
                row["metrics"] = {**(row.get("metrics") or {}), **metrics}
                row["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
                target = row
                break
        if not target:
            return None
        self._rewrite(rows)

        mlflow = self._mlflow_client()
        if mlflow is not None and target.get("mlflow_run_id"):
            try:
                with mlflow.start_run(run_id=target["mlflow_run_id"]):
                    for k, v in metrics.items():
                        try:
                            mlflow.log_metric(k, float(v))
                        except (TypeError, ValueError):
                            continue
            except Exception as exc:
                logger.warning("MLflow log_metrics failed: %s", exc)
        return target

    def promote(self, run_id: str, stage: ExperimentStage | str) -> dict[str, Any] | None:
        st = ExperimentStage(stage) if not isinstance(stage, ExperimentStage) else stage
        rows = self.list_runs(limit=500)
        target = None
        for row in rows:
            if row.get("run_id") == run_id:
                row["stage"] = st.value
                row["tags"] = {**(row.get("tags") or {}), "stage": st.value}
                row["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
                if st == ExperimentStage.PRODUCTION:
                    row["status"] = "completed"
                if st == ExperimentStage.REJECTED:
                    row["status"] = "rejected"
                target = row
                break
        if not target:
            return None
        self._rewrite(rows)

        # Optional MLflow Model Registry stage naming
        mlflow = self._mlflow_client()
        if mlflow is not None and target.get("mlflow_run_id"):
            try:
                with mlflow.start_run(run_id=target["mlflow_run_id"]):
                    mlflow.set_tag("stage", st.value)
            except Exception as exc:
                logger.warning("MLflow promote tag failed: %s", exc)
        return target

    def by_class_summary(self) -> dict[str, Any]:
        rows = self.list_runs(limit=200)
        counts: dict[str, int] = {}
        stages: dict[str, int] = {}
        for r in rows:
            counts[r.get("experiment_class", "?")] = counts.get(r.get("experiment_class", "?"), 0) + 1
            stages[r.get("stage", "?")] = stages.get(r.get("stage", "?"), 0) + 1
        return {"total_runs": len(rows), "by_class": counts, "by_stage": stages}


def seed_demo_experiments(store: ExperimentStore | None = None) -> int:
    store = store or ExperimentStore()
    if store.list_runs():
        return 0
    demos: list[dict[str, Any]] = [
        {
            "name": "prompt-uw-decision-v3",
            "experiment_class": ExperimentClass.PROMPT,
            "hypothesis": "Tighter citation instructions reduce hallucination without hurting recall",
            "params": {"prompt_key": "uw_decision", "version": "v3", "prompt_hash": "a1b2c3"},
            "metrics": {"precision": 0.91, "recall": 0.94, "hallucination_rate": 0.03},
            "stage": ExperimentStage.PRODUCTION,
        },
        {
            "name": "rag-hybrid-kg-k8",
            "experiment_class": ExperimentClass.RAG,
            "hypothesis": "Hybrid vector+KG at k=8 improves context precision",
            "params": {"retrieval_k": 8, "hybrid": True, "kg_enabled": True},
            "metrics": {"ragas_quality_score": 0.86, "context_precision": 0.78},
            "stage": ExperimentStage.CHAMPION,
        },
        {
            "name": "llm-claude-sonnet-temp0",
            "experiment_class": ExperimentClass.LLM_CONFIG,
            "hypothesis": "Sonnet @ temp=0 is more stable for field extraction than Haiku",
            "params": {"provider": "anthropic", "model": "claude-sonnet", "temperature": 0.0},
            "metrics": {"precision": 0.89, "avg_agent_latency_ms": 720},
            "stage": ExperimentStage.CANARY,
        },
        {
            "name": "regression-naics-lookup",
            "experiment_class": ExperimentClass.REGRESSION,
            "hypothesis": "Fix NAICS mis-map that dropped construction hazard findings",
            "params": {"agent": "risk_analyst", "bug": "NAICS-441"},
            "metrics": {"recall": 0.95, "precision": 0.90},
            "stage": ExperimentStage.OFFLINE_EVAL,
        },
    ]
    n = 0
    for d in demos:
        row = store.start_run(
            name=str(d["name"]),
            experiment_class=d["experiment_class"],
            hypothesis=str(d["hypothesis"]),
            params=dict(d["params"]),
            stage=ExperimentStage.DRAFT,
            tags={"seed": "true"},
        )
        store.log_metrics(row["run_id"], dict(d["metrics"]))
        store.promote(row["run_id"], d["stage"])
        n += 1
    return n


def release_walkthrough() -> dict[str, Any]:
    """Interview-friendly narrative of the release process."""
    return {
        "summary": ("Every agent release is an experiment: classify → MLflow run → offline evals + gates → HITL → registry approval → shadow/canary → champion/production → monitor."),
        "checklist": checklist_payload(),
        "experiment_classes_explained": {
            ExperimentClass.PROMPT.value: "Prompt text / citation / rubric instruction changes",
            ExperimentClass.LLM_CONFIG.value: "Model tier, provider, temperature, max tokens",
            ExperimentClass.RAG.value: "Retriever k, hybrid vs vector, knowledge-graph weights",
            ExperimentClass.AGENT_LOGIC.value: "Specialist routing, decision rules, synthesis logic",
            ExperimentClass.TOOLING.value: "Tool / MCP schema or binding changes",
            ExperimentClass.EVAL_BASELINE.value: "Refresh golden set or gate thresholds",
            ExperimentClass.REGRESSION.value: "Targeted fix after production or gate failure",
            ExperimentClass.CANARY.value: "Live traffic comparison vs current champion",
            ExperimentClass.COMPLIANCE.value: "Guideline pack / compliance rule snapshot",
        },
        "stages_explained": {
            ExperimentStage.DRAFT.value: "Hypothesis filed; params fixed",
            ExperimentStage.OFFLINE_EVAL.value: "Golden + Ragas/Giskard running",
            ExperimentStage.HITL_REVIEW.value: "Licensed UW rubric sample",
            ExperimentStage.REGISTRY_REVIEW.value: "Compliance reviewing registry entry",
            ExperimentStage.SHADOW.value: "Challenger scores duplicate traffic, no client impact",
            ExperimentStage.CANARY.value: "Small % of live traffic",
            ExperimentStage.CHAMPION.value: "Beats baseline on gates + HITL; ready to cut over",
            ExperimentStage.PRODUCTION.value: "Active; registry snapshot taken",
        },
    }
