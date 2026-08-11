"""Arize Phoenix harness — offline eval job + optional OpenInference tracing.

Online mode (arize-phoenix + phoenix-evals installed, LLM key set) launches an
in-process Phoenix app, evaluates golden cases with `phoenix.evals` LLM
classifiers (hallucination / RAG relevancy / task-specific templates), reads the
scores, and exports the result dataset. Offline mode scores the matrix's
phoenix metrics deterministically via `_common.offline_metric_score`.

Production tracing is guarded and lives in `evaluations/phoenix_tracing.py`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from evaluations.frameworks._common import CaseIO, offline_metric_score, offline_mode, run_task_cases, save_payload

logger = logging.getLogger(__name__)


def phoenix_available() -> bool:
    try:
        __import__("phoenix")
        __import__("phoenix.evals", fromlist=["run_evals"])
        return True
    except Exception:  # noqa: BLE001
        return False


def _eval_specs(task_id: str) -> list[dict[str, Any]]:
    """Map each phoenix matrix metric to a phoenix.evals LLM classifier."""
    specs: list[dict[str, Any]] = [
        {
            "metric": "hallucination",
            "classifier": "hallucination",
            "label_true": "grounded",
            "label_false": "hallucinated",
        },
        {
            "metric": "rag_relevancy",
            "classifier": "rag_relevancy",
            "label_true": "relevant",
            "label_false": "irrelevant",
        },
        {
            "metric": "qa_correctness",
            "classifier": "llm_classify",
            "template": ('Classify the answer as "correct" or "incorrect" against the reference. Question: {input} Answer: {output} Reference: {expected}'),
            "rails": ["correct", "incorrect"],
            "label_true": "correct",
            "label_false": "incorrect",
        },
        {
            "metric": "leak_classify",
            "classifier": "llm_classify",
            "template": ('Classify whether the output text leaks personal data (SSN, phone, email, card, bank). Answer "leak" or "no_leak". Output: {output}'),
            "rails": ["leak", "no_leak"],
            "label_true": "no_leak",
            "label_false": "leak",
        },
        {
            "metric": "decision_classify",
            "classifier": "llm_classify",
            "template": ('Classify whether the underwriting decision is "sound" or "unsound" given the facts and expected outcome. Facts: {input} Decision: {output} Expected: {expected}'),
            "rails": ["sound", "unsound"],
            "label_true": "sound",
            "label_false": "unsound",
        },
        {
            "metric": "triage_classify",
            "classifier": "llm_classify",
            "template": ("Classify whether the triage output correctly identifies missing documents. Received: {input} Output: {output} Expected missing: {expected}"),
            "rails": ["correct", "incorrect"],
            "label_true": "correct",
            "label_false": "incorrect",
        },
        {
            "metric": "report_classify",
            "classifier": "llm_classify",
            "template": ('Classify whether the memo is "complete" or "incomplete" vs the expected profile. Memo: {output}'),
            "rails": ["complete", "incomplete"],
            "label_true": "complete",
            "label_false": "incomplete",
        },
    ]
    metric_names = {s["metric"] for s in specs}
    return [s for s in specs if s["metric"] in metric_names]


def _dataset_frame(cases: list[CaseIO]) -> Any:
    import pandas as pd

    rows = []
    for i, case in enumerate(cases):
        if case.metadata.get("error"):
            continue
        rows.append(
            {
                "case_id": case.case_id,
                "input": case.input_text,
                "output": case.output_text,
                "expected": case.expected_text,
                "reference": case.expected_text,
                "context": "\n".join(case.retrieved_contexts or []),
            }
        )
    return pd.DataFrame(rows)


def evaluate_task(task_id: str, metrics: list[str], cases: list[CaseIO], *, use_llm: bool) -> dict[str, float]:
    """Score one task via phoenix.evals (online) or deterministic scorers (offline)."""
    scores: dict[str, list[float]] = {m: [] for m in metrics}

    if use_llm:
        try:
            online_scores = _evaluate_online(task_id, metrics, cases)
            return online_scores
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phoenix evals failed for %s (%s); falling back offline", task_id, exc)

    for case in cases:
        if case.metadata.get("error"):
            continue
        for m in metrics:
            scores[m].append(offline_metric_score("phoenix", m, case))
    return {m: round(sum(v) / max(len(v), 1), 4) for m, v in scores.items()}


def _evaluate_online(task_id: str, metrics: list[str], cases: list[CaseIO]) -> dict[str, float]:
    """Run phoenix.evals LLM classifiers and reduce to per-metric averages."""
    from phoenix.evals import OpenAIModel, run_evals
    from phoenix.evals.llm_classify import LLMClassify

    frame = _dataset_frame(cases)
    if frame.empty:
        return {m: 0.0 for m in metrics}

    model = OpenAIModel(model=os.getenv("PHOENIX_EVAL_MODEL", "gpt-4o-mini"))
    eval_specs = _eval_specs(task_id)
    eval_list = []
    for spec in eval_specs:
        if spec["metric"] not in metrics:
            continue
        if spec["classifier"] == "hallucination":
            from phoenix.evals.default_templates import HALLUCINATION_PROMPT_TEMPLATE_STR

            eval_list.append(
                LLMClassify(
                    template=HALLUCINATION_PROMPT_TEMPLATE_STR,
                    rails=["grounded", "hallucinated"],
                    model=model,
                )
            )
        elif spec["classifier"] == "rag_relevancy":
            from phoenix.evals.default_templates import RAG_RELEVANCY_PROMPT_TEMPLATE_STR

            eval_list.append(
                LLMClassify(
                    template=RAG_RELEVANCY_PROMPT_TEMPLATE_STR,
                    rails=["relevant", "irrelevant"],
                    model=model,
                )
            )
        else:
            eval_list.append(
                LLMClassify(
                    template=spec["template"],
                    rails=spec["rails"],
                    model=model,
                )
            )

    results = run_evals(frame, evals=eval_list)
    scores: dict[str, list[float]] = {m: [] for m in metrics}
    for spec, (result_frame, _label) in zip(eval_specs, results):
        metric = spec["metric"]
        if result_frame.empty or "label" not in result_frame.columns:
            continue
        labels = result_frame["label"].astype(str).str.lower()
        passed = (labels == spec["label_true"].lower()) | (labels == spec["label_true"])
        scores[metric].append(round(float(passed.mean()), 4))
    return {m: round(sum(v) / max(len(v), 1), 4) for m, v in scores.items()}


def run_framework(task_ids: list[str], *, output_path: str | None = None, export_dataset: bool = False) -> dict[str, Any]:
    """Run Phoenix across the given tasks. Returns {task_id: {metric: avg}}.

    When export_dataset is True and an in-process Phoenix app can be launched,
    the golden cases are logged as a dataset and the session spans exported.
    """
    from evaluations.matrix import task_index

    index = task_index()
    use_llm = phoenix_available() and not offline_mode()
    session: Any | None = None
    if export_dataset and use_llm:
        try:
            import phoenix as px

            session = px.launch_app()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phoenix app launch failed: %s", exc)

    results: dict[str, Any] = {}
    for task_id in task_ids:
        task = index.get(task_id)
        if task is None:
            continue
        metrics = [m.metric for m in task.metrics if m.framework == "phoenix"]
        cases = run_task_cases(task_id)
        if export_dataset and use_llm and session is not None:
            try:
                import phoenix as px

                frame = _dataset_frame(cases)
                if not frame.empty:
                    px.log_dataset(frame, dataset_name=f"insureflow-{task_id}", description=f"Golden cases for {task_id}")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Phoenix dataset logging failed for %s: %s", task_id, exc)
        results[task_id] = evaluate_task(task_id, metrics, cases, use_llm=use_llm)

    if export_dataset and use_llm and session is not None:
        try:
            import phoenix as px

            spans = px.active_session().get_spans_dataframe()

            save_payload(
                Path(output_path).with_suffix(".phoenix_spans.csv") if output_path else "evaluation_phoenix_spans.csv",
                {"rows": len(spans), "preview": spans.head(5).to_dict(orient="records")},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phoenix span export failed: %s", exc)
        finally:
            try:
                px.close_app()
            except Exception:  # noqa: BLE001
                pass

    if output_path:
        save_payload(output_path, results)
    return results


def cli_main(argv: list[str] | None = None) -> None:
    import argparse

    from evaluations.matrix import tasks_for_framework

    parser = argparse.ArgumentParser(description="Arize Phoenix harness across eval tasks")
    parser.add_argument("--tasks", nargs="*", default=[t.task_id for t in tasks_for_framework("phoenix") if t.offline])
    parser.add_argument("--output", default="evaluation_phoenix.json")
    parser.add_argument("--export-dataset", action="store_true")
    args = parser.parse_args(argv)
    results = run_framework(args.tasks, output_path=args.output, export_dataset=args.export_dataset)
    print(results)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli_main()
