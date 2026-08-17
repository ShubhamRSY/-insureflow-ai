"""Structured explanation tree — /explain endpoint logic.

Produces a human-readable, structured explanation of how a decision was reached,
linking every field to its source document, confidence, and contribution to the
final decision.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FieldExplanation(BaseModel):
    field_name: str
    extracted_value: str = ""
    confidence: float = 0.0
    source_document: str = ""
    source_page: int | None = None
    source_quote: str = ""
    verification_status: str = "unverified"
    contribution_to_decision: str = "neutral"
    issues: list[str] = Field(default_factory=list)


class DecisionPath(BaseModel):
    step: int = 0
    description: str = ""
    outcome: str = ""
    confidence_at_step: float = 0.0


class ExplanationTree(BaseModel):
    bundle_id: str
    org_id: str = "default"
    decision: str = ""
    overall_confidence: float = 0.0
    abstained: bool = False
    abstention_reasons: list[str] = Field(default_factory=list)
    field_explanations: list[FieldExplanation] = Field(default_factory=list)
    decision_path: list[DecisionPath] = Field(default_factory=list)
    routing_tier: str = ""
    guardian_flags: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


def _extract_source_info(field: Any) -> tuple[str, int | None, str]:
    source_doc = ""
    page: int | None = None
    quote = ""
    if hasattr(field, "source"):
        source_doc = str(getattr(field, "source", ""))
    if hasattr(field, "page_number"):
        page = getattr(field, "page_number", None)
    if hasattr(field, "evidence") and isinstance(field.evidence, list) and field.evidence:
        quote = str(field.evidence[0])
    if hasattr(field, "source_quote"):
        sq = getattr(field, "source_quote", "")
        if sq:
            quote = sq
    return source_doc, page, quote


def _assess_contribution(
    field_name: str,
    confidence: float,
    issues: list[Any],
) -> str:
    field_issues = [i for i in issues if getattr(i, "field_name", "") == field_name]
    if any(any(t in getattr(i, "severity", "").lower() for t in ("error", "critical")) for i in field_issues):
        return "negative"
    if any(any(t in getattr(i, "severity", "").lower() for t in ("warning",)) for i in field_issues):
        return "cautionary"
    if confidence >= 0.9:
        return "supportive"
    return "neutral"


def build_explanation(
    bundle_id: str,
    fields: dict[str, Any],
    verification_report: Any = None,
    *,
    decision: str = "",
    routing_decision: Any = None,
    abstention_verdict: Any = None,
    org_id: str = "default",
) -> ExplanationTree:
    field_explanations: list[FieldExplanation] = []
    all_issues: list[Any] = []
    if verification_report and hasattr(verification_report, "issues"):
        all_issues = verification_report.issues

    overall_confidences: list[float] = []
    for field_name, entries in fields.items():
        if not isinstance(entries, list):
            entries = [entries]
        for entry in entries[:1]:
            conf = getattr(entry, "confidence", 0.0) if hasattr(entry, "confidence") else 0.5
            overall_confidences.append(conf)
            source_doc, page, quote = _extract_source_info(entry)
            field_value = getattr(entry, "value", str(entry)) if hasattr(entry, "value") else str(entry)

            field_issues = [getattr(i, "message", "") for i in all_issues if getattr(i, "field_name", "") == field_name]

            field_explanations.append(
                FieldExplanation(
                    field_name=field_name,
                    extracted_value=str(field_value),
                    confidence=conf,
                    source_document=source_doc,
                    source_page=page,
                    source_quote=quote,
                    verification_status="verified" if conf >= 0.9 else "uncertain" if conf >= 0.5 else "low_confidence",
                    contribution_to_decision=_assess_contribution(field_name, conf, all_issues),
                    issues=field_issues,
                )
            )

    avg_conf = sum(overall_confidences) / len(overall_confidences) if overall_confidences else 0.0

    decision_path = _build_decision_path(
        field_explanations=field_explanations,
        decision=decision,
        verification_report=verification_report,
        abstention_verdict=abstention_verdict,
        routing_decision=routing_decision,
    )

    guardian_flags = []
    if verification_report and hasattr(verification_report, "issues"):
        guardian_flags = [getattr(i, "message", "") for i in verification_report.issues if getattr(i, "severity", "") in ("error", "critical")]

    abstained = False
    abstention_reasons: list[str] = []
    if abstention_verdict and hasattr(abstention_verdict, "abstain"):
        abstained = abstention_verdict.abstain
        if hasattr(abstention_verdict, "reasons"):
            abstention_reasons = [str(r) for r in abstention_verdict.reasons]

    routing_tier = ""
    if routing_decision and hasattr(routing_decision, "tier"):
        routing_tier = str(routing_decision.tier.value) if hasattr(routing_decision.tier, "value") else str(routing_decision.tier)

    return ExplanationTree(
        bundle_id=bundle_id,
        org_id=org_id,
        decision=decision,
        overall_confidence=avg_conf,
        abstained=abstained,
        abstention_reasons=abstention_reasons,
        field_explanations=field_explanations,
        decision_path=decision_path,
        routing_tier=routing_tier,
        guardian_flags=guardian_flags,
    )


def _build_decision_path(
    field_explanations: list[FieldExplanation],
    decision: str,
    verification_report: Any = None,
    abstention_verdict: Any = None,
    routing_decision: Any = None,
) -> list[DecisionPath]:
    steps: list[DecisionPath] = []
    step = 1

    steps.append(
        DecisionPath(
            step=step,
            description="Document ingestion and field extraction",
            outcome=f"{len(field_explanations)} fields extracted",
            confidence_at_step=0.5,
        )
    )
    step += 1

    avg_conf = sum(f.confidence for f in field_explanations) / len(field_explanations) if field_explanations else 0.0
    steps.append(
        DecisionPath(
            step=step,
            description="Confidence assessment",
            outcome=f"Average confidence: {avg_conf:.2f}",
            confidence_at_step=avg_conf,
        )
    )
    step += 1

    if verification_report:
        issues = getattr(verification_report, "issues", [])
        error_count = sum(1 for i in issues if getattr(i, "severity", "") in ("error", "critical"))
        steps.append(
            DecisionPath(
                step=step,
                description="Verification gate",
                outcome=f"{error_count} errors, {len(issues) - error_count} warnings" if issues else "No issues found",
                confidence_at_step=avg_conf,
            )
        )
        step += 1

    if abstention_verdict and hasattr(abstention_verdict, "abstain") and abstention_verdict.abstain:
        reasons = [str(r) for r in getattr(abstention_verdict, "reasons", [])]
        steps.append(
            DecisionPath(
                step=step,
                description="Abstention gate",
                outcome=f"Abstained: {'; '.join(reasons)}",
                confidence_at_step=0.0,
            )
        )
        step += 1
        decision = "abstain — human review required"

    if routing_decision:
        tier = str(getattr(routing_decision, "tier", "unknown"))
        steps.append(
            DecisionPath(
                step=step,
                description="Authority routing",
                outcome=f"Routed to: {tier}",
                confidence_at_step=avg_conf,
            )
        )
        step += 1

    steps.append(
        DecisionPath(
            step=step,
            description="Final decision",
            outcome=decision or "pending",
            confidence_at_step=avg_conf,
        )
    )

    return steps
