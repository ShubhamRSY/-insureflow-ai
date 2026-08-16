"""Bounded Extractor ↔ Auditor loop.

Unifies citation failures, epistemic variance, and optional LLM critic into one
recursive correct-or-route cycle. Caps loops and wall time so agents cannot
spiral on a hallucinated discrepancy.

Default: deterministic only (citation + variance). Critic refine needs an LLM
and ``USE_CRITIC_REVIEW`` / ``USE_AUDIT_LOOP``.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from insureflow.models.submissions import ExtractedField, VerificationIssue
from insureflow.verification.citation_gate import citation_issues, is_grounded
from insureflow.verification.common import SEVERITY_ERROR, SEVERITY_WARNING
from insureflow.verification.critic import critic_enabled, critic_review
from insureflow.verification.uncertainty import uncertainty_issues, variance_from_extracted_fields

logger = logging.getLogger(__name__)


def audit_loop_enabled() -> bool:
    raw = os.getenv("USE_AUDIT_LOOP", "1").strip().lower()
    return raw not in {"0", "false", "off", "no", "none"}


@dataclass
class AuditLoopResult:
    fields: dict[str, list[ExtractedField]]
    issues: list[VerificationIssue] = field(default_factory=list)
    loops_run: int = 0
    timed_out: bool = False
    routed_to_human: bool = False
    history: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "loops_run": self.loops_run,
            "timed_out": self.timed_out,
            "routed_to_human": self.routed_to_human,
            "issue_count": len(self.issues),
            "history": list(self.history),
            "issues": [i.model_dump() if hasattr(i, "model_dump") else i for i in self.issues],
        }


def run_audit_loop(
    fields: Mapping[str, list[ExtractedField]],
    *,
    raw_text: str = "",
    llm: Any = None,
    refine: Callable[[dict[str, list[ExtractedField]], list[VerificationIssue]], dict[str, list[ExtractedField]]] | None = None,
    max_loops: int | None = None,
    timeout_seconds: float | None = None,
) -> AuditLoopResult:
    """Iterate: verify → optional refine → re-verify until clean, capped, or timed out."""
    working = {k: list(v) for k, v in fields.items()}
    if not audit_loop_enabled():
        return AuditLoopResult(fields=working, history=["audit_loop_disabled"])

    max_loops = max_loops if max_loops is not None else int(os.getenv("AUDIT_MAX_LOOPS", "2"))
    timeout_seconds = timeout_seconds if timeout_seconds is not None else float(os.getenv("AUDIT_LOOP_TIMEOUT_SECONDS", "8"))
    started = time.monotonic()
    history: list[str] = []
    last_issues: list[VerificationIssue] = []

    for loop_i in range(max(0, max_loops) + 1):
        if time.monotonic() - started > timeout_seconds:
            history.append(f"timeout_after_loop_{loop_i}")
            return AuditLoopResult(
                fields=working,
                issues=last_issues
                + [
                    VerificationIssue(
                        code="audit_loop_timeout",
                        severity=SEVERITY_ERROR,
                        message=f"Extractor↔Auditor loop timed out after {timeout_seconds:.1f}s — routed to human",
                    )
                ],
                loops_run=loop_i,
                timed_out=True,
                routed_to_human=True,
                history=history,
            )

        issues = list(citation_issues(working))
        issues.extend(uncertainty_issues(variance_from_extracted_fields(working)))
        if llm is not None and critic_enabled():
            try:
                issues.extend(critic_review(raw_text, working, llm))
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("audit_loop critic failed: %s", exc)
                history.append(f"critic_failed:{type(exc).__name__}")

        last_issues = issues
        errors = [i for i in issues if i.severity == SEVERITY_ERROR]
        history.append(f"loop_{loop_i}:errors={len(errors)}:warnings={sum(1 for i in issues if i.severity == SEVERITY_WARNING)}")

        if not errors:
            return AuditLoopResult(
                fields=working,
                issues=issues,
                loops_run=loop_i,
                routed_to_human=bool(issues),
                history=history,
            )

        if loop_i >= max_loops or refine is None:
            break

        try:
            refined = refine(working, errors)
            if refined:
                working = {k: list(v) for k, v in refined.items()}
                history.append(f"refined_loop_{loop_i}")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("audit_loop refine failed: %s", exc)
            history.append(f"refine_failed:{type(exc).__name__}")
            break

    ungrounded = [k for k, entries in working.items() if entries and entries[0].value and not is_grounded(entries[0])]
    if ungrounded and not any(i.code == "uncited_claim" for i in last_issues):
        last_issues.append(
            VerificationIssue(
                code="audit_loop_exhausted",
                severity=SEVERITY_ERROR,
                message=f"Audit loop exhausted with ungrounded fields: {', '.join(ungrounded[:8])}",
            )
        )

    return AuditLoopResult(
        fields=working,
        issues=last_issues,
        loops_run=max_loops,
        routed_to_human=True,
        history=history,
    )
