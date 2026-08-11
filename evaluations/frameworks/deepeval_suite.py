"""DeepEval harness — LLM-as-judge metrics parameterized by the eval matrix.

Online mode (OPENAI_API_KEY set + deepeval installed) runs real deepeval
metrics (AnswerCorrectness, Faithfulness, GEval with task-specific criteria,
BiasMetric). Offline mode falls back to the deterministic scorers in
`_common.offline_metric_score` so every task still yields numbers.
"""

from __future__ import annotations

import logging
import sys
import traceback
from typing import Any

from evaluations.frameworks._common import CaseIO, offline_metric_score, offline_mode, run_task_cases, save_payload

logger = logging.getLogger(__name__)

METRIC_LABELS: dict[str, str] = {
    "answer_correctness": "Whether the extracted answer matches the golden value.",
    "faithfulness": "Whether every claim in the answer is supported by the retrieved context.",
    "g_eval_decision": "Decision is clear, correct, and grounded in the submission facts.",
    "g_eval_accuracy": "Reconciliation summary is accurate and complete.",
    "g_eval_triage": "Triage output correctly identifies missing documents for the LOB.",
    "g_eval_report": "Memo is complete, accurate vs profile, and free of hallucinations.",
    "bias": "Decision shows no protected-class or demographic bias.",
    "numeric_tolerance": "Numeric output is within tolerance of the reference.",
    "precision": "Precision of the binary classifier.",
    "recall": "Recall of the binary classifier.",
    "redaction_recall": "No PII tokens leak from the redacted output.",
    "json_schema_fidelity": "Tool output matches the expected JSON contract.",
}

_DEEPEVAL_METRIC_FACTORIES: dict[str, Any] = {}


def _build_metric(metric: str, task_id: str) -> Any:
    try:
        from deepeval.metrics import BiasMetric, GEval
        from deepeval.metrics.answer_correctness import AnswerCorrectness
        from deepeval.metrics.faithfulness import Faithfulness  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover - depends on installed deepeval layout
        from deepeval.metrics.answer_correctness import AnswerCorrectness
        from deepeval.metrics.bias import BiasMetric
        from deepeval.metrics.faithfulness import Faithfulness  # type: ignore[attr-defined]
        from deepeval.metrics.geval import GEval  # type: ignore[no-redef]

    if metric == "answer_correctness":
        return AnswerCorrectness(model="gpt-4o-mini")
    if metric == "faithfulness":
        return Faithfulness(model="gpt-4o-mini")
    if metric == "bias":
        return BiasMetric(model="gpt-4o-mini")
    if metric in _DEEPEVAL_METRIC_FACTORIES:
        return _DEEPEVAL_METRIC_FACTORIES[metric](task_id)
    criteria = METRIC_LABELS.get(metric, f"Quality of the output for task {task_id}.")
    return GEval(name=metric, criteria=criteria, model="gpt-4o-mini", evaluation_steps=[criteria])


def _build_test_case(case: CaseIO) -> Any:
    from deepeval.test_case import LLMTestCase

    return LLMTestCase(
        input=case.input_text,
        actual_output=case.output_text,
        expected_output=case.expected_text or None,
        retrieval_context=case.retrieved_contexts or None,  # type: ignore[arg-type]
    )


def evaluate_task(task_id: str, metrics: list[str], cases: list[CaseIO], *, use_llm: bool) -> dict[str, float]:
    """Score one task. Returns {metric: avg} (0..1)."""
    scores: dict[str, list[float]] = {m: [] for m in metrics}

    for case in cases:
        if case.metadata.get("error"):
            continue
        if not use_llm:
            for m in metrics:
                scores[m].append(offline_metric_score("deepeval", m, case))
            continue

        try:
            test_case = _build_test_case(case)
            for m in metrics:
                metric = _build_metric(m, task_id)
                metric.measure(test_case)
                score = float(getattr(metric, "score", 0.0) or 0.0)
                scores[m].append(max(0.0, min(1.0, score)))
        except Exception:  # noqa: BLE001 — deepeval LLM judging failed; fall back offline
            logger.warning("deepeval LLM judging failed for %s (%s); using offline scores", task_id, case.case_id)
            for m in metrics:
                scores[m].append(offline_metric_score("deepeval", m, case))

    return {m: round(sum(v) / max(len(v), 1), 4) for m, v in scores.items()}


def run_framework(task_ids: list[str], *, output_path: str | None = None) -> dict[str, Any]:
    """Run deepeval across the given tasks. Returns {task_id: {metric: avg}}."""
    use_llm = not offline_mode()
    from evaluations.matrix import task_index

    index = task_index()
    results: dict[str, Any] = {}
    for task_id in task_ids:
        task = index.get(task_id)
        if task is None:
            continue
        metrics = [m.metric for m in task.metrics if m.framework == "deepeval"]
        cases = run_task_cases(task_id)
        results[task_id] = evaluate_task(task_id, metrics, cases, use_llm=use_llm)
    if output_path:
        save_payload(output_path, results)
    return results


def cli_main(argv: list[str] | None = None) -> None:
    import argparse

    from evaluations.matrix import tasks_for_framework

    parser = argparse.ArgumentParser(description="deepeval harness across eval tasks")
    parser.add_argument("--tasks", nargs="*", default=[t.task_id for t in tasks_for_framework("deepeval") if t.offline])
    parser.add_argument("--output", default="evaluation_deepeval.json")
    args = parser.parse_args(argv)
    results = run_framework(args.tasks, output_path=args.output)
    print(results)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        cli_main()
    except Exception:  # noqa: BLE001
        print(traceback.format_exc())
        sys.exit(1)
