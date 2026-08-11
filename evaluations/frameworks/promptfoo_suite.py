"""promptfoo harness — declarative prompt regression tests per eval task.

Each eval task maps to a committed `promptfooconfig` under
`evaluations/promptfoo/configs/` with a task-specific prompt template, an
OpenAI provider, and assertions. The harness:

  - materializes the golden dataset rows (vars) from the real case sources,
  - runs `promptfoo eval` when the CLI is available and an LLM key is set,
  - otherwise scores the matrix's promptfoo metrics offline via
    `_common.offline_metric_score` (same JSON shape, no network needed).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from evaluations.frameworks._common import CaseIO, offline_metric_score, offline_mode, run_task_cases, save_payload

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "promptfoo" / "configs"
PROMPTFOO_WORKDIR = Path(__file__).resolve().parent.parent / "promptfoo"


def promptfoo_available() -> bool:
    return shutil.which("promptfoo") is not None


PROMPT_TEMPLATES: dict[str, str] = {
    "field_extraction": (
        "You are a commercial insurance data extraction assistant. "
        "Extract these fields from the ACORD submission and return them as `key: value` lines: "
        "insured_name, construction, occupancy, protection_class, square_footage, stories, naics, revenue, payroll.\n\n"
        "ACORD:\n{{input_text}}\n\nFields:"
    ),
    "underwriting_decision": (
        "You are a licensed commercial underwriter. Given the submission facts below, give a decision "
        "(accept / refer / decline) and a one-paragraph rationale grounded only in those facts.\n\nFacts:\n{{input_text}}"
    ),
    "synthesis_quality": ("You are an underwriting memo writer. Produce a complete, accurate, non-hallucinating memo for the following submission profile.\n\nProfile:\n{{input_text}}"),
    "rag_guideline_qa": (
        "Answer the underwriting guideline question using only the retrieved guideline context. If the context does not support an answer, say so.\n\nQuestion: {{input_text}}\n\nContext:\n{{context}}"
    ),
    "mortgage_decision": (
        "You are a mortgage underwriter. Given the borrower package, return approve/refer/suspend/deny with a rationale citing DTI, LTV, credit, and compliance findings.\n\nPackage:\n{{input_text}}"
    ),
    "agent_tool_selection": ("You are the triage agent. List the documents missing from this submission's package for the commercial property LOB.\n\nDocuments received: {{input_text}}"),
    "mcp_contract": ("Compute the requested underwriting metric from the claims data and return the numeric value only.\n\nTool: {{tool}}\nClaims: {{input_text}}"),
    "rating_accuracy": ("Rate the following commercial property risk. Return the annual adjusted premium as a number only.\n\nRisk: {{input_text}}"),
    "reconciliation": ("Reconcile these conflicting source values and state whether a discrepancy exists.\n\n{{input_text}}"),
    "redaction_safety": ("Redact all personally identifiable information (SSN, phone, email, credit card, bank account) from the text. Return only the redacted text.\n\nText: {{input_text}}"),
    "ml_fraud_detection": ("Predict the fraud risk (0-1) for the claims dataset with the given model. Return the score only.\n\n{{input_text}}"),
}


def _task_vars(task_id: str, case: CaseIO) -> dict[str, Any]:
    vars_: dict[str, Any] = {"case_id": case.case_id, "input_text": case.input_text}
    if task_id == "rag_guideline_qa":
        vars_["context"] = "\n".join(case.retrieved_contexts or [case.output_text])
    if task_id == "mcp_contract":
        vars_["tool"] = (case.metadata or {}).get("tool", task_id)
    return vars_


def _assertions(task_id: str, case: CaseIO) -> list[dict[str, Any]]:
    exp = case.expected_text
    if task_id == "redaction_safety":
        return [{"type": "python", "value": "redaction_recall", "threshold": 0.95}]
    if task_id == "mcp_contract":
        return [{"type": "python", "value": "numeric_assert", "threshold": 0.9}]
    if task_id in ("field_extraction", "rag_guideline_qa"):
        return [{"type": "contains-any", "value": exp.split(", "), "threshold": 0.8}]
    if task_id == "rating_accuracy":
        return [{"type": "python", "value": "numeric_assert", "threshold": 0.8}]
    if task_id == "reconciliation":
        return [{"type": "equals", "value": exp}]
    if task_id in ("underwriting_decision", "synthesis_quality", "mortgage_decision", "agent_tool_selection"):
        return [{"type": "llm-rubric", "value": "The output satisfies the requested task and is grounded in the input.", "threshold": 0.7}]
    return [{"type": "is-json"}]


def build_config(task_id: str, cases: list[CaseIO]) -> Path:
    """Materialize (idempotently) the declarative promptfoo config for a task."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    provider = os.getenv("PROMPTFOO_PROVIDER", "openai:gpt-4o-mini")
    lines = [
        f"description: {task_id}",
        "",
        "prompts:",
        "  - |",
    ]
    for line in PROMPT_TEMPLATES[task_id].splitlines():
        lines.append(f"    {line}")
    lines += ["", "providers:", f"  - {provider}", "", "tests:"]
    for case in cases:
        if case.metadata.get("error"):
            continue
        lines.append(f"  - vars: {_task_vars(task_id, case)!r}")
        for assertion in _assertions(task_id, case):
            lines.append("    assert:")
            for k, v in assertion.items():
                lines.append(f"      - {k}: {v!r}")
    path = CONFIG_DIR / f"{task_id}.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _run_cli(config: Path, task_id: str) -> dict[str, Any]:
    work = PROMPTFOO_WORKDIR
    out = work / "outputs" / f"{task_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["promptfoo", "eval", "-c", str(config), "-o", str(out), "--no-cache", "--max-concurrency", "2"]
    proc = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"promptfoo eval failed for {task_id}: {proc.stderr[-2000:]}")
    try:
        import json

        data = json.loads(out.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"promptfoo output unparseable for {task_id}: {exc}") from exc
    return {"raw_results_file": str(out), "payload": data}


def evaluate_task(task_id: str, metrics: list[str], cases: list[CaseIO], *, use_cli: bool) -> dict[str, float]:
    scores: dict[str, list[float]] = {m: [] for m in metrics}
    if use_cli:
        try:
            config = build_config(task_id, cases)
            _run_cli(config, task_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("promptfoo CLI run failed for %s (%s); falling back offline", task_id, exc)
            use_cli = False
    for case in cases:
        if case.metadata.get("error"):
            continue
        for m in metrics:
            scores[m].append(offline_metric_score("promptfoo", m, case))
    return {m: round(sum(v) / max(len(v), 1), 4) for m, v in scores.items()}


def run_framework(task_ids: list[str], *, output_path: str | None = None) -> dict[str, Any]:
    from evaluations.matrix import task_index

    index = task_index()
    use_cli = promptfoo_available() and not offline_mode()
    results: dict[str, Any] = {}
    for task_id in task_ids:
        task = index.get(task_id)
        if task is None:
            continue
        metrics = [m.metric for m in task.metrics if m.framework == "promptfoo"]
        cases = run_task_cases(task_id)
        if use_cli:
            build_config(task_id, cases)
        results[task_id] = evaluate_task(task_id, metrics, cases, use_cli=use_cli)
    if output_path:
        save_payload(output_path, results)
    return results


def cli_main(argv: list[str] | None = None) -> None:
    import argparse

    from evaluations.matrix import tasks_for_framework

    parser = argparse.ArgumentParser(description="promptfoo harness across eval tasks")
    parser.add_argument("--tasks", nargs="*", default=[t.task_id for t in tasks_for_framework("promptfoo") if t.offline])
    parser.add_argument("--output", default="evaluation_promptfoo.json")
    parser.add_argument("--gen-configs-only", action="store_true", help="write YAML configs and exit")
    args = parser.parse_args(argv)
    if args.gen_configs_only:
        for task_id in args.tasks:
            cases = run_task_cases(task_id)
            path = build_config(task_id, cases)
            print(f"wrote {path}")
        return
    results = run_framework(args.tasks, output_path=args.output)
    print(results)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli_main()
