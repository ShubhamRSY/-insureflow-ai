"""Evaluation and HITL check frequency / cadence policy.

Defines how often automated evals and human reviews run in a bank-style
operating model. Enforced via GitHub Actions schedule + documented gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CadencePolicy:
    name: str
    frequency: str
    trigger: str
    owner: str
    scope: str
    sla: str


# Bank / MLOps operating cadence
EVAL_CADENCE: list[CadencePolicy] = [
    CadencePolicy(
        name="unit_regression",
        frequency="every_pr_and_push",
        trigger="GitHub Actions CI on pull_request + push to main",
        owner="engineering",
        scope="pytest suite (~340 tests) — parsers, agents, provenance, gateway",
        sla="Must pass before merge",
    ),
    CadencePolicy(
        name="golden_field_scorer",
        frequency="nightly",
        trigger="GitHub Actions cron 0 6 * * * UTC + manual workflow_dispatch",
        owner="ml_ops",
        scope="13 insurance golden cases → precision/recall/hallucination → LangSmith",
        sla="Alert if precision < 0.85 or recall < 0.90",
    ),
    CadencePolicy(
        name="ragas_hybrid_rag_kg",
        frequency="nightly",
        trigger="Same nightly eval workflow (requires LLM key)",
        owner="ml_ops",
        scope="Faithfulness, answer relevancy, context precision/recall on hybrid RAG+KG",
        sla="Alert if overall RAG quality < 0.80",
    ),
    CadencePolicy(
        name="giskard_safety_scan",
        frequency="weekly",
        trigger="GitHub Actions cron 0 7 * * 1 UTC (Mondays)",
        owner="ml_ops + compliance",
        scope="Bias/robustness scan on golden dataset",
        sla="New high-severity issues reviewed within 5 business days",
    ),
    CadencePolicy(
        name="full_eval_report",
        frequency="weekly",
        trigger="Monday nightly after scorer + Ragas + Giskard",
        owner="ml_ops",
        scope="evaluations.report → LangSmith insureflow-evals project",
        sla="Report published every Monday; CUO reads summary weekly",
    ),
]

HITL_CADENCE: list[CadencePolicy] = [
    CadencePolicy(
        name="production_uw_signoff",
        frequency="per_submission",
        trigger="Every insurance job reaching licensed UW queue before bind",
        owner="licensed_uw",
        scope="Approve/refer/decline + override category + UW confidence",
        sla="Human gate required — no bind without LICENSED_UW sign-off",
    ),
    CadencePolicy(
        name="eval_rubric_spot_check",
        frequency="weekly",
        trigger="Sample of golden + recent production outputs scored with HITL rubrics",
        owner="licensed_uw + cuo",
        scope="≥5 cases/week scored on 8 rubric dimensions; tags + agree/disagree",
        sla="Weekly pass rate ≥ 80%; disagree cases escalate to CUO",
    ),
    CadencePolicy(
        name="override_pattern_review",
        frequency="biweekly",
        trigger="Override analytics dashboard + pattern detection",
        owner="cuo + actuarial",
        scope="Recurring override categories → guideline / KG updates",
        sla="Review every 2 weeks; material patterns logged as registry change requests",
    ),
    CadencePolicy(
        name="loss_feedback_calibration",
        frequency="monthly",
        trigger="Bind + loss experience feedback engine",
        owner="actuarial",
        scope="AI vs UW vs actual premium/loss ratio calibration",
        sla="Monthly calibration summary; drift >10% triggers model review",
    ),
]


def cadence_inventory() -> dict[str, Any]:
    def _ser(items: list[CadencePolicy]) -> list[dict[str, str]]:
        return [
            {
                "name": c.name,
                "frequency": c.frequency,
                "trigger": c.trigger,
                "owner": c.owner,
                "scope": c.scope,
                "sla": c.sla,
            }
            for c in items
        ]

    return {
        "automated_eval": _ser(EVAL_CADENCE),
        "human_in_the_loop": _ser(HITL_CADENCE),
        "summary": {
            "unit_tests": "every PR / push to main",
            "golden_and_ragas": "nightly (06:00 UTC)",
            "giskard_and_full_report": "weekly (Mondays)",
            "production_hitl": "every submission before bind",
            "eval_hitl_rubrics": "weekly (≥5 scored cases)",
            "override_patterns": "every 2 weeks",
            "loss_calibration": "monthly",
        },
        "interview_summary": (
            "Automated evals: unit tests on every PR; golden precision/recall + Ragas nightly; "
            "Giskard + full report weekly. "
            "HITL: licensed UW sign-off on every bind-eligible submission; "
            "weekly rubric spot-checks (≥5 cases); biweekly override-pattern review; "
            "monthly loss/premium calibration."
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(cadence_inventory(), indent=2))
