"""Framework suite runner — executes the eval matrix across all four frameworks.

Runs ragas / deepeval / promptfoo / Arize Phoenix over the task registry in
`evaluations/matrix.py` and merges the per-metric averages into one payload,
then applies the matrix SLA gate. Use `python -m evaluations.frameworks.suite_runner`.

Modes:
  --fast         offline-only, skip heavy tasks (default for CI smoke)
  --medium       + ML fraud + mortgage per-borrower
  --pipeline     + full underwriting/mortgage pipeline tasks (needs EVAL deps + LLM)
"""

from __future__ import annotations

import argparse
import logging
from typing import Any

from evaluations.frameworks._common import offline_metric_score, run_task_cases, save_payload

logger = logging.getLogger(__name__)

_HEAVY = {"ml_fraud_detection", "mortgage_decision"}
_PIPELINE = {"field_extraction", "underwriting_decision", "synthesis_quality"}


def _framework_harness(name: str) -> Any:
    from evaluations.frameworks import deepeval_suite, phoenix_suite, promptfoo_suite

    return {
        "deepeval": deepeval_suite,
        "promptfoo": promptfoo_suite,
        "phoenix": phoenix_suite,
    }[name]


def _ragas_scores(task_ids: list[str], *, use_pipeline: bool) -> dict[str, Any]:
    """ragas support: offline matrix metrics by default; full ragas_eval when pipeline mode is on."""
    from evaluations.matrix import task_index

    results: dict[str, Any] = {}
    index = task_index()
    if use_pipeline:
        try:
            from evaluations.ragas_eval import evaluate_ragas

            summary = evaluate_ragas("evaluation_ragas.json")
            metrics = summary.get("metrics", {})
            for name, payload in metrics.items():
                if isinstance(payload, dict) and "avg" in payload:
                    for task_id in ("field_extraction", "underwriting_decision"):
                        results.setdefault(task_id, {})[name] = payload["avg"]
            return results
        except Exception as exc:  # noqa: BLE001
            logger.warning("Full ragas run skipped: %s", exc)

    for task_id in task_ids:
        task = index.get(task_id)
        if task is None or "ragas" not in task.frameworks:
            continue
        ragas_metrics = [m.metric for m in task.metrics if m.framework == "ragas"]
        cases = run_task_cases(task_id)
        scores: dict[str, list[float]] = {m: [] for m in ragas_metrics}
        for case in cases:
            if case.metadata.get("error"):
                continue
            for m in ragas_metrics:
                scores[m].append(offline_metric_score("ragas", m, case))
        results[task_id] = {m: round(sum(v) / max(len(v), 1), 4) for m, v in scores.items()}
    return results


def _select_tasks(task_ids: list[str] | None, *, fast: bool, pipeline: bool) -> list[str]:
    from evaluations.matrix import TASKS

    all_tasks = [t.task_id for t in TASKS]
    selected = task_ids if task_ids else list(all_tasks)
    if fast:
        selected = [t for t in selected if t not in _HEAVY and t not in _PIPELINE]
    elif not pipeline:
        selected = [t for t in selected if t not in _PIPELINE]
    return selected


def run_all(
    *,
    frameworks: list[str] | None = None,
    task_ids: list[str] | None = None,
    fast: bool = False,
    pipeline: bool = False,
    output_path: str | None = "evaluation_frameworks.json",
    export_dataset: bool = False,
) -> dict[str, Any]:
    from evaluations.matrix import FRAMEWORKS, apply_sla_gate

    selected = _select_tasks(task_ids, fast=fast, pipeline=pipeline)
    frameworks = frameworks or list(FRAMEWORKS)
    merged: dict[str, Any] = {}
    for fw in frameworks:
        if fw == "ragas":
            merged["ragas"] = _ragas_scores(selected, use_pipeline=pipeline)
            continue
        harness = _framework_harness(fw)
        kwargs: dict[str, Any] = {}
        if fw == "phoenix":
            kwargs["export_dataset"] = export_dataset
        merged[fw] = harness.run_framework(selected, **kwargs)

    gate = apply_sla_gate(merged, offline=not pipeline)
    payload: dict[str, Any] = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "mode": "pipeline" if pipeline else ("fast" if fast else "standard"),
        "frameworks": {fw: {"enabled": True} for fw in frameworks},
        "tasks": selected,
        "scores": merged,
        "sla_gate": gate,
        "coverage": {
            "framework": _coverage_fraction(merged),
            "sections": _section_coverage(),
        },
    }
    if output_path:
        save_payload(output_path, payload)
    return payload


def _coverage_fraction(merged: dict[str, Any]) -> dict[str, float]:
    from evaluations.matrix import tasks_for_framework

    frac: dict[str, float] = {}
    for fw, tasks in merged.items():
        if not isinstance(tasks, dict):
            continue
        expected = [t.task_id for t in tasks_for_framework(fw)]
        scored = [t for t in expected if t in tasks and isinstance(tasks[t], dict) and tasks[t]]
        frac[fw] = round(len(scored) / max(len(expected), 1), 3)
    return frac


def _section_coverage() -> list[dict[str, Any]]:
    from evaluations.matrix import sections

    return [{"section": s} for s in sections()]


def cli_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the four-framework eval matrix")
    parser.add_argument("--frameworks", nargs="*", default=None)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--output", default="evaluation_frameworks.json")
    parser.add_argument("--fast", action="store_true", help="offline-only, skip heavy tasks")
    parser.add_argument("--pipeline", action="store_true", help="include full pipeline tasks (needs EVAL deps + LLM)")
    parser.add_argument("--export-dataset", action="store_true", help="log Phoenix dataset + export spans")
    args = parser.parse_args(argv)
    payload = run_all(
        frameworks=args.frameworks,
        task_ids=args.tasks,
        fast=args.fast,
        pipeline=args.pipeline,
        output_path=args.output,
        export_dataset=args.export_dataset,
    )
    import json

    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli_main()
