"""LangSmith cloud tracking for InsureFlow evaluation metrics and pipeline runs.

Cloud environment: LangSmith (https://smith.langchain.com)

Set LANGSMITH_API_KEY to enable. Without a key the tracker is a no-op so local
pytest / eval runs stay offline-friendly.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PROJECT = "insureflow-evals"
LOCAL_CACHE_DIR = Path(os.getenv("EVAL_CLOUD_CACHE_DIR", "./evaluation_cloud_cache"))


@dataclass
class CloudTrackResult:
    enabled: bool
    provider: str = "langsmith"
    project: str = DEFAULT_PROJECT
    run_id: str | None = None
    url: str | None = None
    local_path: str | None = None
    error: str | None = None
    scores_logged: int = 0


@dataclass
class CloudEvalTracker:
    """Push precision/recall/Ragas/Giskard metrics to LangSmith."""

    api_key: str = field(default_factory=lambda: os.getenv("LANGSMITH_API_KEY", "").strip())
    project: str = field(default_factory=lambda: os.getenv("LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", DEFAULT_PROJECT)))
    endpoint: str = field(default_factory=lambda: os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com").rstrip("/"))
    tracing_enabled: bool = field(default_factory=lambda: os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "true")).lower() in {"1", "true", "yes"})

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict[str, Any]:
        return {
            "provider": "langsmith",
            "enabled": self.is_enabled(),
            "project": self.project,
            "endpoint": self.endpoint,
            "tracing": self.tracing_enabled and self.is_enabled(),
            "dashboard": "https://smith.langchain.com",
        }

    def enable_runtime_tracing(self) -> bool:
        """Enable LangChain/LangGraph cloud tracing for live pipeline runs."""
        if not self.is_enabled():
            return False
        os.environ.setdefault("LANGSMITH_API_KEY", self.api_key)
        os.environ.setdefault("LANGCHAIN_API_KEY", self.api_key)
        os.environ["LANGCHAIN_TRACING_V2"] = "true" if self.tracing_enabled else "false"
        os.environ["LANGSMITH_TRACING"] = "true" if self.tracing_enabled else "false"
        os.environ["LANGCHAIN_PROJECT"] = self.project
        os.environ["LANGSMITH_PROJECT"] = self.project
        if self.endpoint:
            os.environ.setdefault("LANGSMITH_ENDPOINT", self.endpoint)
            os.environ.setdefault("LANGCHAIN_ENDPOINT", self.endpoint)
        logger.info("LangSmith runtime tracing enabled → project=%s", self.project)
        return True

    def _client(self) -> Any:
        from langsmith import Client

        return Client(api_key=self.api_key, api_url=self.endpoint)

    def _cache_locally(self, payload: dict[str, Any], prefix: str) -> str:
        LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = LOCAL_CACHE_DIR / f"{prefix}_{stamp}_{uuid.uuid4().hex[:8]}.json"
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return str(path)

    def log_metrics(
        self,
        *,
        run_name: str,
        metrics: dict[str, float | int | None],
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> CloudTrackResult:
        """Log an evaluation run + numeric feedback scores to LangSmith."""
        payload: dict[str, Any] = {
            "run_name": run_name,
            "metrics": metrics,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "metadata": {
                "source": "insureflow-evaluations",
                "logged_at": datetime.now(tz=timezone.utc).isoformat(),
                **(metadata or {}),
            },
            "tags": tags or ["evaluation"],
            "project": self.project,
        }

        if not self.is_enabled():
            local_path = self._cache_locally(payload, "metrics_offline")
            logger.info("LangSmith disabled (no LANGSMITH_API_KEY) — cached to %s", local_path)
            return CloudTrackResult(
                enabled=False,
                project=self.project,
                local_path=local_path,
                error="LANGSMITH_API_KEY not set",
            )

        try:
            client = self._client()
            outs: dict[str, Any] = dict(payload["outputs"] or {})
            outs["metrics"] = metrics
            run = client.create_run(
                name=run_name,
                run_type="chain",
                inputs=payload["inputs"] or {"metrics_keys": list(metrics.keys())},
                outputs=outs,
                project_name=self.project,
                extra={"metadata": payload["metadata"]},
                tags=payload["tags"],
            )
            run_id = getattr(run, "id", None) or getattr(run, "run_id", None)
            scores_logged = 0
            for key, value in metrics.items():
                if value is None:
                    continue
                try:
                    score = float(value)
                except (TypeError, ValueError):
                    continue
                client.create_feedback(
                    run_id=run_id,
                    key=key,
                    score=score,
                    comment=f"InsureFlow eval metric: {key}",
                )
                scores_logged += 1

            url = f"https://smith.langchain.com/o/default/projects/p/{self.project}"
            if run_id:
                url = f"https://smith.langchain.com/public/{run_id}/r"
            local_path = self._cache_locally({**payload, "run_id": str(run_id)}, "metrics_uploaded")
            logger.info(
                "LangSmith run logged: project=%s run_id=%s scores=%s",
                self.project,
                run_id,
                scores_logged,
            )
            return CloudTrackResult(
                enabled=True,
                project=self.project,
                run_id=str(run_id) if run_id else None,
                url=url,
                local_path=local_path,
                scores_logged=scores_logged,
            )
        except ImportError:
            local_path = self._cache_locally(payload, "metrics_no_sdk")
            return CloudTrackResult(
                enabled=False,
                project=self.project,
                local_path=local_path,
                error="langsmith package not installed — pip install -e '.[eval]'",
            )
        except Exception as exc:
            local_path = self._cache_locally({**payload, "error": str(exc)}, "metrics_error")
            logger.warning("LangSmith upload failed: %s (cached to %s)", exc, local_path)
            return CloudTrackResult(
                enabled=False,
                project=self.project,
                local_path=local_path,
                error=str(exc),
            )

    def log_evaluation_report(self, report: dict[str, Any]) -> CloudTrackResult:
        """Push a full generate_report() payload to LangSmith."""
        summary = report.get("summary", {})
        metrics: dict[str, float | int | None] = {
            "precision": summary.get("precision"),
            "recall": summary.get("recall"),
            "hallucination_rate": summary.get("hallucination_rate"),
        }
        ragas = summary.get("ragas_quality_score")
        if isinstance(ragas, (int, float)):
            metrics["ragas_quality_score"] = float(ragas)
        giskard = summary.get("giskard_issues_found")
        if isinstance(giskard, (int, float)):
            metrics["giskard_issues"] = float(giskard)

        sections = report.get("sections", {})
        rag = sections.get("rag_quality", {}).get("metrics", {})
        for key in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
            if key in rag and isinstance(rag[key], (int, float)):
                metrics[key] = float(rag[key])

        return self.log_metrics(
            run_name="underwriting-eval-report",
            metrics=metrics,
            inputs={"report_title": report.get("report_title")},
            outputs={
                "verdict": summary.get("overall_verdict"),
                "recommendations": report.get("recommendations", []),
                "sections": {k: v.get("metrics") if isinstance(v, dict) else v for k, v in sections.items()},
            },
            metadata={
                "generated_at": report.get("generated_at"),
                "verdict": summary.get("overall_verdict"),
            },
            tags=["evaluation", "report", "insureflow"],
        )

    def log_case_scores(self, scored_cases: list[dict[str, Any]]) -> CloudTrackResult:
        """Log aggregate + per-case field extraction scores."""
        if not scored_cases:
            return CloudTrackResult(enabled=self.is_enabled(), project=self.project, error="no cases")

        avg_precision = sum(s.get("precision", 0) for s in scored_cases) / len(scored_cases)
        avg_recall = sum(s.get("recall", 0) for s in scored_cases) / len(scored_cases)
        avg_hallucination = sum(s.get("hallucination_rate", 0) for s in scored_cases) / len(scored_cases)

        return self.log_metrics(
            run_name="field-extraction-scorer",
            metrics={
                "avg_precision": avg_precision,
                "avg_recall": avg_recall,
                "avg_hallucination_rate": avg_hallucination,
                "total_cases": len(scored_cases),
            },
            outputs={"per_case": scored_cases},
            metadata={"suite": "custom_scorer"},
            tags=["evaluation", "field-extraction"],
        )


def get_tracker() -> CloudEvalTracker:
    return CloudEvalTracker()


def track_report(report: dict[str, Any]) -> dict[str, Any]:
    """Convenience wrapper used by evaluations.report."""
    result = get_tracker().log_evaluation_report(report)
    return {
        "enabled": result.enabled,
        "provider": result.provider,
        "project": result.project,
        "run_id": result.run_id,
        "url": result.url,
        "local_path": result.local_path,
        "error": result.error,
        "scores_logged": result.scores_logged,
    }
