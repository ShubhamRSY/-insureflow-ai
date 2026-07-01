from __future__ import annotations

import json
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patch Ragas's broken vertexai import before importing ragas itself.
# Ragas 0.4.3 tries: from langchain_community.chat_models.vertexai import ChatVertexAI
# That module no longer exists in modern langchain-community.
# ---------------------------------------------------------------------------
import types as _types

_MOD = _types.ModuleType("langchain_community.chat_models.vertexai")


class _DummyChatVertexAI:
    _llm_type = "dummy"

    def __init__(self, **kwargs: Any) -> None:
        pass


_MOD.ChatVertexAI = _DummyChatVertexAI

import sys as _sys

_sys.modules["langchain_community.chat_models.vertexai"] = _MOD

# Now safe to import ragas
from ragas import evaluate as ragas_evaluate
from ragas.dataset_schema import EvaluationDataset, EvaluationResult, SingleTurnSample
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

from evaluations.golden_dataset import golden_dataset
from evaluations.runner import extract_field


def _avg(key: str, scores: list[dict[str, Any]]) -> float:
    vals = [s.get(key, 0) or 0 for s in scores]
    return round(sum(vals) / max(len(vals), 1), 4)


def _extract_per_case_scores(
    score: EvaluationResult,
    cases: list,
) -> list[dict[str, Any]]:
    return [
        {
            "case": cases[i].name if i < len(cases) else f"case_{i}",
            "faithfulness": s.get("faithfulness", 0),
            "answer_relevancy": s.get("answer_relevancy", 0),
            "context_precision": s.get("context_precision", 0),
            "context_recall": s.get("context_recall", 0),
        }
        for i, s in enumerate(score.scores)
    ]


_RAG_INITIALIZED = False


def _ensure_rag() -> None:
    global _RAG_INITIALIZED
    if not _RAG_INITIALIZED:
        from insureflow.rag.rag_agent import RAGAgent

        agent = RAGAgent()
        agent.ensure_indexed()
        _RAG_INITIALIZED = True


def _run_pipeline_for_sample(case) -> dict[str, Any]:
    """Run the pipeline and return a dict with synthesis + expected fields."""
    from insureflow.pipeline import UnderwritingPipeline

    pipeline = UnderwritingPipeline()
    raw = pipeline.run(acord_xml=case.acord_xml, bundle_id=case.name)

    synthesis = raw.get("synthesis", {})
    profile = synthesis.get("synthesized_profile", {})

    # RAG context is in graph_state, not top-level
    graph_state = raw.get("graph_state", {})
    rag_context = raw.get("rag_context", "") or graph_state.get("rag_context", "")

    expected = {
        "insured_name": case.expected_insured_name,
        "construction": case.expected_construction,
        "occupancy": case.expected_occupancy,
        "protection_class": case.expected_protection_class,
        "square_footage": case.expected_square_footage,
        "stories": case.expected_stories,
        "naics": case.expected_naics,
        "revenue": case.expected_revenue,
        "payroll": case.expected_payroll,
    }

    actual = {
        "insured_name": extract_field(profile, "legal_name", "named_insured"),
        "construction": extract_field(profile, "construction_type"),
        "occupancy": extract_field(profile, "occupancy_type"),
        "protection_class": extract_field(profile, "protection_class"),
        "square_footage": extract_field(profile, "total_square_footage", "square_footage"),
        "stories": extract_field(profile, "number_of_stories"),
        "naics": extract_field(profile, "naics_code"),
        "revenue": extract_field(profile, "annual_revenue"),
        "payroll": extract_field(profile, "payroll"),
    }

    return {
        "actual": actual,
        "expected": expected,
        "synthesis": synthesis,
        "rag_context": rag_context,
    }


def _build_sample(
    case,
    pipeline_data: dict[str, Any],
) -> SingleTurnSample | None:
    pipeline_data.get("synthesis", {})
    rag_context = pipeline_data.get("rag_context", "")
    expected = pipeline_data.get("expected", {})
    actual = pipeline_data.get("actual", {})

    # Build answer from synthesized profile
    if not actual or not any(v is not None for v in actual.values()):
        return None

    answer_lines = []
    for label, key in [
        ("Insured", "insured_name"),
        ("Construction", "construction"),
        ("Occupancy", "occupancy"),
        ("Protection Class", "protection_class"),
        ("Square Footage", "square_footage"),
        ("Stories", "stories"),
        ("NAICS", "naics"),
        ("Revenue", "revenue"),
        ("Payroll", "payroll"),
    ]:
        val = actual.get(key)
        if val is not None:
            answer_lines.append(f"{label}: {val}")
    if not answer_lines:
        return None
    answer = "\n".join(answer_lines)

    # Build question
    q_parts = ["Underwrite the following commercial risk:"]
    for k in ["insured_name", "occupancy", "construction"]:
        v = expected.get(k)
        if v:
            q_parts.append(f"{k.replace('_', ' ').title()}: {v}")
    question = ". ".join(q_parts)

    # Contexts from RAG
    contexts = []
    if rag_context:
        for chunk in rag_context.split("=== RELEVANT UNDERWRITING GUIDELINES ==="):
            chunk = chunk.strip()
            if chunk:
                contexts.append(chunk)
        if not contexts:
            contexts = [rag_context]

    # Ground truth from expected
    gt_parts = []
    for label, key in [
        ("Insured", "insured_name"),
        ("Construction", "construction"),
        ("Occupancy", "occupancy"),
        ("Protection Class", "protection_class"),
        ("Square Footage", "square_footage"),
        ("Stories", "stories"),
        ("NAICS", "naics"),
        ("Revenue", "revenue"),
        ("Payroll", "payroll"),
    ]:
        val = expected.get(key)
        if val is not None:
            gt_parts.append(f"{label}: {val}")
    ground_truth = ", ".join(gt_parts) if gt_parts else ""

    return SingleTurnSample(
        user_input=question,
        retrieved_contexts=contexts,
        response=answer,
        reference=ground_truth if ground_truth else None,
    )


def evaluate_ragas(output_path: str | None = None) -> dict[str, Any]:
    """Run Ragas faithfulness / relevancy / context metrics on golden dataset."""
    _ensure_rag()
    cases = golden_dataset()
    samples: list[SingleTurnSample] = []
    errors: list[dict[str, Any]] = []
    case_details: list[dict[str, Any]] = []

    for case in cases:
        try:
            pipeline_data = _run_pipeline_for_sample(case)
            sample = _build_sample(case, pipeline_data)
            if sample is not None:
                samples.append(sample)
                case_details.append(
                    {
                        "case": case.name,
                        "has_sample": True,
                        "context_count": len(sample.retrieved_contexts),
                        "answer_len": len(sample.response),
                    }
                )
                logger.info(
                    "[%s] sample built (ctx=%d, ans=%d)",
                    case.name,
                    len(sample.retrieved_contexts),
                    len(sample.response),
                )
            else:
                logger.warning("[%s] empty profile, skipped", case.name)
                errors.append({"case": case.name, "reason": "empty profile"})
        except Exception as exc:
            logger.error("[%s] failed: %s", case.name, exc)
            errors.append({"case": case.name, "error": str(exc)})

    if not samples:
        msg = "No Ragas samples generated (all empty answers)."
        logger.warning(msg)
        return {
            "framework": "ragas",
            "total_cases": len(cases),
            "samples": 0,
            "error": msg,
            "errors": errors,
        }

    dataset = EvaluationDataset(samples=samples)

    # Check if we have an LLM API key — Ragas needs one for LLM-based metrics
    import os

    has_llm = bool(os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))

    if has_llm:
        logger.info("Computing Ragas metrics (faithfulness, relevancy, context precision/recall)...")
        score: EvaluationResult = ragas_evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            raise_exceptions=False,
        )
        per_case = _extract_per_case_scores(score, cases)
        metrics = {
            "faithfulness": {"avg": _avg("faithfulness", score.scores), "per_case": per_case},
            "answer_relevancy": {
                "avg": _avg("answer_relevancy", score.scores),
                "per_case": per_case,
            },
            "context_precision": {
                "avg": _avg("context_precision", score.scores),
                "per_case": per_case,
            },
            "context_recall": {"avg": _avg("context_recall", score.scores), "per_case": per_case},
        }
        overall = round(sum(m["avg"] for m in metrics.values()) / 4, 4)
    else:
        logger.warning("No LLM API key set — Ragas LLM-based metrics require OPENAI_API_KEY or LLM_API_KEY.")
        logger.info("Computing RAG context stats only (no LLM judge).")
        # Non-LLM fallback: compute context statistics
        per_case = [
            {
                "case": cases[i].name if i < len(cases) else f"case_{i}",
                "context_count": len(s.retrieved_contexts),
                "context_chars": sum(len(c) for c in s.retrieved_contexts),
                "has_response": bool(s.response),
            }
            for i, s in enumerate(samples)
        ]
        avg_ctx_count = sum(pc["context_count"] for pc in per_case) / max(len(per_case), 1)
        metrics = {
            "context_statistics": {
                "avg_context_count": round(avg_ctx_count, 2),
                "total_context_chars": sum(pc["context_chars"] for pc in per_case),
                "per_case": per_case,
            }
        }
        overall = None

    summary = {
        "framework": "ragas",
        "version": "0.4.3",
        "total_cases": len(cases),
        "samples_generated": len(samples),
        "case_details": case_details,
        "errors": errors,
        "metrics": metrics,
    }
    if overall is not None:
        summary["overall_quality_score"] = overall

    if output_path:
        import pathlib

        pathlib.Path(output_path).write_text(json.dumps(summary, indent=2, default=str))
        logger.info("Written to %s", output_path)

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = sys.argv[1] if len(sys.argv) > 1 else "ragas_scores.json"
    result = evaluate_ragas(out)
    print(json.dumps(result, indent=2, default=str))
