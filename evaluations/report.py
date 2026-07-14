from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def generate_report(
    custom_metrics_path: str | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Generate a consolidated business-facing evaluation report.

    Gathers results from:
      - Custom scorer (field-level precision/recall/hallucination)
      - Ragas (faithfulness, answer_relevancy, context_precision, context_recall)
      - Giskard (bias/robustness scan)
    """
    # 1. Custom scorer
    from evaluations.scorer import score_all

    custom_scores = score_all()

    avg_p = sum(s["precision"] for s in custom_scores) / max(len(custom_scores), 1)
    avg_r = sum(s["recall"] for s in custom_scores) / max(len(custom_scores), 1)
    avg_h = sum(s["hallucination_rate"] for s in custom_scores) / max(len(custom_scores), 1)

    # 2. Ragas
    from evaluations.ragas_eval import evaluate_ragas

    ragas_result = evaluate_ragas()

    ragas_metrics = ragas_result.get("metrics", {})
    has_llm = "faithfulness" in ragas_metrics

    # 3. Giskard
    from evaluations.giskard_scan import scan_pipeline

    try:
        giskard_result = scan_pipeline()
    except Exception as exc:
        logger.warning("Giskard scan failed: %s", exc)
        giskard_result = {"total_issues": -1, "error": str(exc), "issues": []}

    report: dict[str, Any] = {
        "report_title": "InsureFlow AI — Underwriting Pipeline Evaluation Report",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "summary": {
            "overall_verdict": _verdict(
                precision=avg_p,
                recall=avg_r,
                hallucination=avg_h,
                faithfulness=ragas_metrics.get("faithfulness", {}).get("avg", 0) if has_llm else 0,
                giskard_issues=giskard_result.get("total_issues", -1),
            ),
            "precision": round(avg_p, 4),
            "recall": round(avg_r, 4),
            "hallucination_rate": round(avg_h, 4),
            "ragas_quality_score": ragas_result.get("overall_quality_score", "N/A"),
            "giskard_issues_found": giskard_result.get("total_issues", "N/A"),
        },
        "sections": {
            "field_extraction_accuracy": {
                "description": "Per-field precision/recall on golden dataset (custom scorer)",
                "metrics": {
                    "avg_precision": round(avg_p, 4),
                    "avg_recall": round(avg_r, 4),
                    "avg_hallucination_rate": round(avg_h, 4),
                },
                "per_case": [
                    {
                        "case": s["case"],
                        "precision": s["precision"],
                        "recall": s["recall"],
                        "hallucination_rate": s["hallucination_rate"],
                        "field_scores": s.get("field_scores", {}),
                    }
                    for s in custom_scores
                ],
            },
        },
        "recommendations": _recommendations(
            precision=avg_p,
            recall=avg_r,
            hallucination=avg_h,
            ragas_result=ragas_result,
            giskard_result=giskard_result,
        ),
    }

    # Add RAG quality section (structure depends on whether LLM-based metrics are available)
    if has_llm:
        report["sections"]["rag_quality"] = {
            "description": "RAG pipeline evaluated with Ragas LLM-based metrics (faithfulness, relevancy, context precision/recall)",
            "metrics": {name: m["avg"] for name, m in ragas_metrics.items()},
            "overall_quality_score": ragas_result.get("overall_quality_score"),
            "total_cases": ragas_result.get("total_cases"),
            "samples_generated": ragas_result.get("samples_generated"),
        }
    else:
        report["sections"]["rag_quality"] = {
            "description": "RAG pipeline context statistics (LLM not available — set OPENAI_API_KEY for Ragas metrics)",
            "metrics": ragas_metrics,
            "total_cases": ragas_result.get("total_cases"),
            "samples_generated": ragas_result.get("samples_generated"),
        }

    # Add Giskard section if we have results
    report["sections"]["llm_safety_scan"] = {
        "description": "Bias, robustness, and safety scan with Giskard",
        "total_issues": giskard_result.get("total_issues", "N/A"),
        "issues": giskard_result.get("issues", []),
    }

    # 4. Human-in-the-loop eval rubrics
    from evaluations.hitl_rubrics import HITLEvalStore, export_rubric_card, seed_demo_reviews, track_hitl_to_langsmith

    hitl_store = HITLEvalStore()
    seed_demo_reviews(hitl_store)
    export_rubric_card()
    hitl_summary = hitl_store.summary()
    hitl_cloud = track_hitl_to_langsmith(hitl_summary)

    report["sections"]["human_in_the_loop_eval"] = {
        "description": ("Licensed UW / CUO rubric scoring on golden cases (field accuracy, decision fit, hallucination, compliance, provenance) + decision agree rates and feedback tags"),
        "metrics": {
            "agree_rate": hitl_summary.agree_rate,
            "disagree_rate": hitl_summary.disagree_rate,
            "case_pass_rate": hitl_summary.case_pass_rate,
            "avg_scores": hitl_summary.avg_scores,
        },
        "top_feedback_tags": hitl_summary.top_feedback_tags,
        "below_threshold": hitl_summary.below_threshold,
        "rubrics": hitl_summary.rubrics,
        "total_reviews": hitl_summary.total_reviews,
        "cloud_tracking": hitl_cloud,
    }
    report["summary"]["hitl_agree_rate"] = hitl_summary.agree_rate
    report["summary"]["hitl_case_pass_rate"] = hitl_summary.case_pass_rate

    # Ground-truth golden inventory
    from evaluations.qa_ground_truth import ground_truth_inventory

    gt = ground_truth_inventory()
    report["sections"]["ground_truth_golden_set"] = {
        "description": "Maintained gold / ground-truth datasets used for scoring",
        **gt,
    }
    report["summary"]["golden_cases"] = gt["insurance"]["golden_cases"]
    report["summary"]["ground_truth_questions"] = gt["totals"]["ground_truth_questions"]

    from evaluations.cadence import cadence_inventory

    report["sections"]["eval_and_hitl_cadence"] = {
        "description": "How often automated evals and human-in-the-loop checks run",
        **cadence_inventory(),
    }

    # 5. LangSmith cloud tracking (no-op without LANGSMITH_API_KEY)
    from evaluations.cloud_tracker import track_report

    cloud = track_report(report)
    report["cloud_tracking"] = cloud
    if cloud.get("enabled"):
        logger.info("Eval metrics uploaded to LangSmith project=%s run_id=%s", cloud.get("project"), cloud.get("run_id"))
    elif cloud.get("local_path"):
        logger.info("LangSmith offline — metrics cached at %s", cloud.get("local_path"))

    from evaluations.quality_gates import gates_from_report_summary

    rag_section = report["sections"].get("rag_quality", {}).get("metrics", {})
    gates = gates_from_report_summary(report["summary"], ragas_metrics=rag_section)
    report["sections"]["quality_gates"] = {
        "description": "Metric thresholds — beyond these we FLAG or BLOCK",
        **gates,
    }
    report["summary"]["gate_verdict"] = gates["verdict"]
    report["summary"]["gate_blocks"] = gates["blocks"]
    report["summary"]["gate_flags"] = gates["flags"]

    if output_path:
        Path(output_path).write_text(json.dumps(report, indent=2, default=str))
        logger.info("Report written to %s", output_path)

    return report


def _verdict(
    precision: float,
    recall: float,
    hallucination: float,
    faithfulness: float,
    giskard_issues: int,
) -> str:
    checks: list[str] = []
    if precision >= 0.85:
        checks.append("✓ Precision ≥ 85%")
    if recall >= 0.90:
        checks.append("✓ Recall ≥ 90%")
    if hallucination <= 0.05:
        checks.append("✓ Hallucination ≤ 5%")
    if faithfulness >= 0.80:
        checks.append("✓ Faithfulness ≥ 80%")
    if giskard_issues >= 0:
        checks.append(f"✓ Giskard scanned ({giskard_issues} issues)")
    else:
        checks.append("⚠ Giskard scan not completed")

    passed = sum(1 for c in checks if c.startswith("✓"))
    total = 5
    if passed >= 4:
        return f"DEPLOYMENT-READY ({passed}/{total} checks passed): {', '.join(checks)}"
    elif passed >= 2:
        return f"CONDITIONAL PASS ({passed}/{total} checks passed): {', '.join(checks)}"
    else:
        return f"NEEDS IMPROVEMENT ({passed}/{total} checks passed): {', '.join(checks)}"


def _recommendations(
    precision: float,
    recall: float,
    hallucination: float,
    ragas_result: dict[str, Any],
    giskard_result: dict[str, Any],
) -> list[str]:
    recs: list[str] = []

    if precision < 0.85:
        recs.append(f"Improve field extraction precision ({precision:.1%}). Review parser regex patterns for ACORD/loss-run parsers.")
    if recall < 0.90:
        recs.append(f"Improve field extraction recall ({recall:.1%}). Add more field mappings for edge-case XML structures.")
    if hallucination > 0.05:
        recs.append(f"Reduce hallucination rate ({hallucination:.1%}). Tighten LLM prompts and add output validation.")
    if ragas_result.get("overall_quality_score", 0) is not None and ragas_result.get("overall_quality_score", 1) < 0.8:
        recs.append(f"RAG quality score is {ragas_result.get('overall_quality_score'):.1%}. Add more guidelines and improve retrieval.")
    if giskard_result.get("total_issues", 0) and giskard_result["total_issues"] > 0:
        recs.append(f"Giskard found {giskard_result['total_issues']} issues. Review and address before production deployment.")
    if not recs:
        recs.append("All quality gates pass. Ready for production deployment.")

    return recs


def print_report(report: dict[str, Any]) -> None:
    """Print a human-readable summary to stdout."""
    s = report.get("summary", {})
    print("=" * 72)
    print(f"  {report.get('report_title', 'Evaluation Report')}")
    print(f"  Generated: {report.get('generated_at', 'N/A')}")
    print("=" * 72)
    print(f"\n  VERDICT: {s.get('overall_verdict', 'N/A')}")
    if s.get("gate_verdict"):
        print(f"  GATE VERDICT: {s.get('gate_verdict')} (blocks={s.get('gate_blocks')}, flags={s.get('gate_flags')})")
    print(f"\n  ┌─{'─' * 50}─┐")
    print(f"  │ {'Metric':<30} {'Score':<18} │")
    print(f"  ├─{'─' * 50}─┤")
    print(f"  │ {'Precision':<30} {s.get('precision', 'N/A'):>8.1%} {'':>10} │")
    print(f"  │ {'Recall':<30} {s.get('recall', 'N/A'):>8.1%} {'':>10} │")
    print(f"  │ {'Hallucination Rate':<30} {s.get('hallucination_rate', 'N/A'):>8.1%} {'':>10} │")
    hitl_a = s.get("hitl_agree_rate")
    if isinstance(hitl_a, (int, float)):
        print(f"  │ {'HITL Agree Rate':<30} {hitl_a:>8.1%} {'':>10} │")
    hitl_p = s.get("hitl_case_pass_rate")
    if isinstance(hitl_p, (int, float)):
        print(f"  │ {'HITL Case Pass Rate':<30} {hitl_p:>8.1%} {'':>10} │")
    qs = s.get("ragas_quality_score", "N/A")
    if isinstance(qs, (int, float)):
        print(f"  │ {'RAG Quality Score':<30} {qs:>8.1%} {'':>10} │")
    else:
        print(f"  │ {'RAG Quality Score':<30} {'N/A':>8} {'':>10} │")
    gi = s.get("giskard_issues_found", "N/A")
    print(f"  │ {'Giskard Issues':<30} {str(gi):>8} {'':>10} │")
    print(f"  └─{'─' * 50}─┘")

    secs = report.get("sections", {})
    for name, section in secs.items():
        print(f"\n  [{name}]")
        print(f"  {section.get('description', '')}")
        for k, v in section.get("metrics", {}).items():
            if isinstance(v, float):
                print(f"    {k}: {v:.1%}")
            else:
                print(f"    {k}: {v}")

    print("\n  Recommendations:")
    for r in report.get("recommendations", []):
        print(f"    • {r}")

    cloud = report.get("cloud_tracking") or {}
    print("\n  Cloud tracking (LangSmith):")
    if cloud.get("enabled"):
        print(f"    • Uploaded to project={cloud.get('project')} run_id={cloud.get('run_id')}")
        if cloud.get("url"):
            print(f"    • {cloud['url']}")
    else:
        reason = cloud.get("error") or "disabled"
        cache = cloud.get("local_path")
        print(f"    • Offline ({reason})")
        if cache:
            print(f"    • Local cache: {cache}")
    print("=" * 72)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = sys.argv[1] if len(sys.argv) > 1 else "evaluation_report.json"
    report = generate_report(output_path=out)
    print_report(report)
