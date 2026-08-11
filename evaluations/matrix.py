"""Eval matrix — task -> framework -> metric parameter registry.

This is the single source of truth that answers: for every subsystem we have
built, which evaluation frameworks (ragas / deepeval / promptfoo / Arize
Phoenix) apply, which metrics each framework reports, and the SLA target each
metric must meet. The harnesses under `evaluations/frameworks/` read this
registry so that "parameters as evaluations" stay declarative and reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FRAMEWORKS: tuple[str, ...] = ("ragas", "deepeval", "promptfoo", "phoenix")

FRAMEWORK_DESCRIPTIONS: dict[str, str] = {
    "ragas": "RAG evaluation (faithfulness, relevancy, context precision/recall) on golden pipelines",
    "deepeval": "LLM-as-judge metrics (answer correctness, faithfulness, G-Eval, safety) via DeepEval",
    "promptfoo": "Declarative prompt/output regression tests via promptfoo YAML configs + assertions",
    "phoenix": "Arize Phoenix evals (LLM classifiers + numeric) and OpenInference tracing",
}

# Coverage targets per framework: minimum fraction of (offline-runnable) tasks
# that must produce a score before the matrix is considered covered.
FRAMEWORK_MIN_COVERAGE: dict[str, float] = {
    "ragas": 0.80,
    "deepeval": 0.80,
    "promptfoo": 0.80,
    "phoenix": 0.80,
}


@dataclass(frozen=True)
class MetricSpec:
    framework: str
    metric: str
    target: float  # 0..1 SLA threshold the metric must meet (LLM-judged mode)
    category: str = "quality"  # quality | correctness | safety | performance
    offline_target: float | None = None  # relaxed SLA for the deterministic offline proxy

    def sla_target(self, *, offline: bool) -> float:
        if offline and self.offline_target is not None:
            return self.offline_target
        return self.target


@dataclass(frozen=True)
class EvalTask:
    task_id: str
    section: str
    subsystem: str
    description: str
    frameworks: tuple[str, ...]
    metrics: tuple[MetricSpec, ...]
    offline: bool  # deterministically runnable without an LLM API key
    sample_limit: int = 8


TASKS: list[EvalTask] = [
    EvalTask(
        task_id="field_extraction",
        section="Commercial Underwriting — Ingestion & Extraction",
        subsystem="src/insureflow/ingestion + pipeline",
        description="Extract named insured, construction, occupancy, PC, square footage, stories, NAICS, revenue, payroll from golden ACORD submissions.",
        frameworks=("ragas", "deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("ragas", "faithfulness", 0.75),
            MetricSpec("ragas", "answer_relevancy", 0.70),
            MetricSpec("ragas", "context_precision", 0.70),
            MetricSpec("ragas", "context_recall", 0.80),
            MetricSpec("deepeval", "answer_correctness", 0.70),
            MetricSpec("promptfoo", "field_contains", 0.85, "correctness"),
            MetricSpec("phoenix", "qa_correctness", 0.70),
        ),
        offline=False,
        sample_limit=3,
    ),
    EvalTask(
        task_id="reconciliation",
        section="Commercial Underwriting — Reconciliation & Provenance",
        subsystem="src/insureflow/reconciliation",
        description="Detect cross-source field discrepancies (coverage, financials, party) and reconcile to a consensus value.",
        frameworks=("deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("deepeval", "g_eval_accuracy", 0.75),
            MetricSpec("promptfoo", "python_assert", 1.0, "correctness"),
            MetricSpec("phoenix", "discrepancy_classify", 0.80),
        ),
        offline=True,
        sample_limit=4,
    ),
    EvalTask(
        task_id="underwriting_decision",
        section="Commercial Underwriting — Decision",
        subsystem="src/insureflow/agents/uw_decision_agent + pipeline",
        description="Produce a clear underwriting decision with a rationale grounded in the submission facts.",
        frameworks=("ragas", "deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("ragas", "faithfulness", 0.70),
            MetricSpec("ragas", "answer_relevancy", 0.65),
            MetricSpec("deepeval", "g_eval_decision", 0.70),
            MetricSpec("deepeval", "bias", 0.60, "safety"),
            MetricSpec("promptfoo", "llm_rubric", 0.70),
            MetricSpec("phoenix", "decision_classify", 0.70),
        ),
        offline=False,
        sample_limit=3,
    ),
    EvalTask(
        task_id="rating_accuracy",
        section="Rating & Pricing",
        subsystem="src/insureflow/rating",
        description="InsuranceRatingEngine quote premium vs an independent pure-premium ratemaking reference.",
        frameworks=("deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("deepeval", "numeric_tolerance", 0.90, "correctness"),
            MetricSpec("promptfoo", "python_assert", 0.90, "correctness"),
            MetricSpec("phoenix", "numeric_ratio", 0.90),
        ),
        offline=True,
        sample_limit=3,
    ),
    EvalTask(
        task_id="rag_guideline_qa",
        section="RAG & Knowledge",
        subsystem="src/insureflow/rag (rag_agent + knowledge_graph)",
        description="Answer underwriting-guideline questions from hybrid vector RAG + knowledge-graph retrieval.",
        frameworks=("ragas", "deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("ragas", "faithfulness", 0.80),
            MetricSpec("ragas", "answer_relevancy", 0.75, offline_target=0.60),
            MetricSpec("ragas", "context_precision", 0.75),
            MetricSpec("ragas", "context_recall", 0.80),
            MetricSpec("deepeval", "faithfulness", 0.80),
            MetricSpec("promptfoo", "contains_phrases", 0.80),
            MetricSpec("phoenix", "hallucination", 0.85, "safety"),
            MetricSpec("phoenix", "rag_relevancy", 0.75),
        ),
        offline=True,
        sample_limit=8,
    ),
    EvalTask(
        task_id="mortgage_decision",
        section="Mortgage",
        subsystem="src/insureflow/mortgage + agents/mortgage",
        description="Mortgage pipeline decision (approve/refer/suspend/deny), DTI/LTV ranges, compliance violations per golden borrower package.",
        frameworks=("ragas", "deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("ragas", "faithfulness", 0.70),
            MetricSpec("deepeval", "g_eval_decision", 0.70),
            MetricSpec("promptfoo", "llm_rubric", 0.70),
            MetricSpec("phoenix", "decision_classify", 0.70),
        ),
        offline=True,
        sample_limit=4,
    ),
    EvalTask(
        task_id="ml_fraud_detection",
        section="ML Predictive",
        subsystem="src/insureflow/ml/fraud_detection",
        description="Fraud anomaly detection precision / recall / F1 on a synthetic claims corpus.",
        frameworks=("deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("deepeval", "precision", 0.70, "correctness"),
            MetricSpec("deepeval", "recall", 0.70, "correctness"),
            MetricSpec("promptfoo", "python_assert", 0.70, "correctness"),
            MetricSpec("phoenix", "numeric_precision", 0.70),
        ),
        offline=True,
        sample_limit=1,
    ),
    EvalTask(
        task_id="agent_tool_selection",
        section="Agents",
        subsystem="src/insureflow/agents/triage_agent + tools",
        description="Triage agent completeness scoring and tool-call correctness for a submission document checklist.",
        frameworks=("deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("deepeval", "g_eval_triage", 0.70),
            MetricSpec("promptfoo", "llm_rubric", 0.70),
            MetricSpec("phoenix", "triage_classify", 0.70),
        ),
        offline=True,
        sample_limit=3,
    ),
    EvalTask(
        task_id="mcp_contract",
        section="MCP Server",
        subsystem="src/insureflow/mcp/server (UnderwritingTools)",
        description="MCP tool outputs satisfy the numeric JSON contract (loss ratio, frequency, severity, large-loss, litigation ratios).",
        frameworks=("deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("deepeval", "json_schema_fidelity", 0.90, "correctness"),
            MetricSpec("promptfoo", "json_assert", 0.90, "correctness"),
            MetricSpec("phoenix", "schema_classify", 0.90),
        ),
        offline=True,
        sample_limit=5,
    ),
    EvalTask(
        task_id="redaction_safety",
        section="Security & Privacy",
        subsystem="src/insureflow/redaction",
        description="PII redaction recall — SSN, phone, email, credit card tokens must never leak from outputs.",
        frameworks=("deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("deepeval", "redaction_recall", 0.95, "safety"),
            MetricSpec("promptfoo", "regex_assert", 1.0, "safety"),
            MetricSpec("phoenix", "leak_classify", 0.95, "safety"),
        ),
        offline=True,
        sample_limit=6,
    ),
    EvalTask(
        task_id="synthesis_quality",
        section="Reporting & Synthesis",
        subsystem="src/insureflow/agents/synthesis_agent + rating/report_document",
        description="Synthesis memo quality — completeness, accuracy vs profile, clarity, no hallucinated facts.",
        frameworks=("deepeval", "promptfoo", "phoenix"),
        metrics=(
            MetricSpec("deepeval", "g_eval_report", 0.70),
            MetricSpec("promptfoo", "llm_rubric", 0.70),
            MetricSpec("phoenix", "report_classify", 0.70),
        ),
        offline=False,
        sample_limit=3,
    ),
]


def task_index() -> dict[str, EvalTask]:
    return {t.task_id: t for t in TASKS}


def tasks_for_framework(framework: str) -> list[EvalTask]:
    return [t for t in TASKS if framework in t.frameworks]


def sections() -> list[str]:
    return list(dict.fromkeys(t.section for t in TASKS))


def coverage_matrix() -> list[dict[str, Any]]:
    """Section x framework coverage: which frameworks evaluate each section."""
    rows: list[dict[str, Any]] = []
    for section in sections():
        row: dict[str, Any] = {"section": section, "tasks": []}
        for t in TASKS:
            if t.section != section:
                continue
            row["tasks"].append(
                {
                    "task_id": t.task_id,
                    "frameworks": list(t.frameworks),
                    "offline": t.offline,
                    "metrics": [(m.framework, m.metric, m.target) for m in t.metrics],
                }
            )
            for fw in FRAMEWORKS:
                row[fw] = row.get(fw, False) or fw in t.frameworks
        rows.append(row)
    return rows


def matrix_inventory() -> dict[str, Any]:
    """Machine-readable inventory for interviews / dashboards / scheduled evals."""
    by_section: dict[str, list[str]] = {}
    for t in TASKS:
        by_section.setdefault(t.section, []).append(t.task_id)

    per_framework: dict[str, dict[str, Any]] = {}
    for fw in FRAMEWORKS:
        tasks = tasks_for_framework(fw)
        metrics = [f"{m.framework}:{m.metric}" for t in tasks for m in t.metrics if m.framework == fw]
        per_framework[fw] = {
            "description": FRAMEWORK_DESCRIPTIONS[fw],
            "tasks": len(tasks),
            "task_ids": [t.task_id for t in tasks],
            "metrics": sorted(set(metrics)),
        }

    return {
        "frameworks": list(FRAMEWORKS),
        "sections": sections(),
        "task_count": len(TASKS),
        "tasks": [
            {
                "task_id": t.task_id,
                "section": t.section,
                "subsystem": t.subsystem,
                "description": t.description,
                "frameworks": list(t.frameworks),
                "offline": t.offline,
                "metrics": [(m.framework, m.metric, m.target, m.category, m.offline_target) for m in t.metrics],
            }
            for t in TASKS
        ],
        "coverage": coverage_matrix(),
        "per_framework": per_framework,
        "sla": {f"{m.framework}:{m.metric}": m.target for t in TASKS for m in t.metrics},
    }


def apply_sla_gate(results: dict[str, Any], *, offline: bool = True) -> dict[str, Any]:
    """Check per-metric averages against the SLA targets from this matrix.

    `results` is the combined output of suite_runner.run_all() — a dict of
    framework -> {task_id -> {metric: avg}}. Returns a gate dict with pass/fail
    per framework and overall. When ``offline`` is True (deterministic proxy
    mode), metrics that declare an ``offline_target`` are compared against that
    relaxed threshold instead of the LLM-judged target.
    """
    spec_index = {f"{m.framework}:{m.metric}": m for t in TASKS for m in t.metrics}
    checked: dict[str, list[float]] = {fw: [] for fw in FRAMEWORKS}
    violations: list[dict[str, Any]] = []

    for framework, tasks in results.items():
        if framework not in FRAMEWORKS:
            continue
        for task_id, task_result in tasks.items():
            if not isinstance(task_result, dict):
                continue
            for metric, avg in task_result.items():
                if isinstance(avg, (int, float)):
                    spec = spec_index.get(f"{framework}:{metric}")
                    if spec is None:
                        continue
                    target = spec.sla_target(offline=offline)
                    checked[framework].append(float(avg))
                    if float(avg) < target:
                        violations.append(
                            {
                                "framework": framework,
                                "task": task_id,
                                "metric": metric,
                                "avg": float(avg),
                                "target": target,
                                "mode": "offline" if offline else "pipeline",
                            }
                        )

    gate: dict[str, Any] = {"violations": violations, "frameworks": {}}
    evaluated: list[bool] = []
    for fw in FRAMEWORKS:
        vals = checked[fw]
        fw_violations = [v for v in violations if v["framework"] == fw]
        gate["frameworks"][fw] = {
            "metrics_checked": len(vals),
            "avg_score": round(sum(vals) / max(len(vals), 1), 4) if vals else None,
            "pass": not fw_violations and bool(vals),
        }
        if vals:
            evaluated.append(not fw_violations)
    gate["overall_pass"] = all(evaluated) if evaluated else False
    return gate


def _metrics_for(framework: str) -> set[str]:
    return {m.metric for t in TASKS for m in t.metrics if m.framework == framework}


if __name__ == "__main__":
    import json

    print(json.dumps(matrix_inventory(), indent=2))
