"""Zero Token Architecture router.

``ZeroTokenRouter.route()`` classifies a pipeline task as deterministic
(zero tokens), LLM, human escalation, or skip.  The heuristics encode the ZTA
principle: try the deterministic path first; only fall through to an LLM when
the deterministic path is genuinely insufficient and a budget allows it.
"""

from __future__ import annotations

import math
from typing import Any, Union

from insureflow.zta.config import ZtaConfig
from insureflow.zta.models import (
    RouteContext,
    RouteDecision,
    RouteResult,
    ZtaTask,
)

# Expected field counts per document type — used to judge extraction coverage.
DEFAULT_EXPECTED_FIELDS: dict[str, int] = {
    "inspection_report": 12,
    "loss_run": 8,
    "schedule_of_values": 10,
    "broker_application": 8,
    "policy_declaration": 8,
}
FALLBACK_EXPECTED_FIELDS = 6


def estimate_tokens(text: str | None) -> int:
    """Rough token estimate (~4 chars/token).  Used to report tokens avoided."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _coerce_context(ctx: Union[RouteContext, dict[str, Any]]) -> RouteContext:
    if isinstance(ctx, RouteContext):
        return ctx
    return RouteContext(**ctx)


_router_singleton: ZeroTokenRouter | None = None


def get_router(llm_available: bool = True) -> ZeroTokenRouter:
    """Return the shared router (config from env at first call)."""
    global _router_singleton
    if _router_singleton is None:
        _router_singleton = ZeroTokenRouter(llm_available=llm_available)
    return _router_singleton


class ZeroTokenRouter:
    """Decides deterministic-vs-LLM for each task."""

    def __init__(
        self,
        config: ZtaConfig | None = None,
        llm_available: bool = True,
    ) -> None:
        self.config = config or ZtaConfig()
        self.llm_available = llm_available
        self._llm_tasks_used = 0

    def reset_job(self) -> None:
        """Reset the per-job LLM task budget."""
        self._llm_tasks_used = 0

    @property
    def _llm_budget_exhausted(self) -> bool:
        return self._llm_tasks_used >= self.config.max_llm_tasks_per_job

    def _allow_llm(self) -> bool:
        if not self.llm_available or self.config.strict:
            return False
        if self._llm_budget_exhausted:
            return False
        return True

    def _decide_llm(self, task: ZtaTask, reason: str, tokens_saved_est: int = 0, tokens_used_est: int = 0) -> RouteResult:
        if self._allow_llm():
            self._llm_tasks_used += 1
            return RouteResult(task, RouteDecision.LLM, reason, tokens_saved_est, tokens_used_est)
        if self.llm_available and not self.config.strict and self._llm_budget_exhausted:
            return RouteResult(task, RouteDecision.ESCALATE_HUMAN, f"{reason} — LLM task budget exhausted", tokens_saved_est)
        if self.config.strict:
            return RouteResult(task, RouteDecision.ESCALATE_HUMAN, f"{reason} — strict mode forbids LLM", tokens_saved_est)
        return RouteResult(task, RouteDecision.ESCALATE_HUMAN, f"{reason} — LLM unavailable", tokens_saved_est)

    def route(self, task: ZtaTask, ctx: Union[RouteContext, dict[str, Any], None] = None) -> RouteResult:
        context = _coerce_context(ctx or {})
        text = context.text or ""
        input_tokens = estimate_tokens(text)

        if task == ZtaTask.EXTRACT_STRUCTURED:
            return RouteResult(
                task,
                RouteDecision.DETERMINISTIC,
                "ACORD/structured documents parse with a rule-based parser — zero tokens",
                tokens_saved_est=input_tokens,
            )

        if task == ZtaTask.EXTRACT_UNSTRUCTURED:
            if not text.strip():
                return RouteResult(task, RouteDecision.ESCALATE_HUMAN, "no text available to extract")
            expected = context.expected_fields or DEFAULT_EXPECTED_FIELDS.get(context.doc_type, FALLBACK_EXPECTED_FIELDS)
            ratio = context.regex_field_count / max(1, expected)
            if ratio >= self.config.expected_fields_ratio:
                return RouteResult(
                    task,
                    RouteDecision.DETERMINISTIC,
                    f"regex/rule extraction captured {ratio:.0%} of expected fields — deterministic",
                    tokens_saved_est=input_tokens,
                )
            return self._decide_llm(
                task,
                f"regex coverage only {ratio:.0%} — ambiguous document needs LLM",
                tokens_saved_est=input_tokens,
                tokens_used_est=input_tokens + 200,
            )

        if task == ZtaTask.RECONCILE:
            if context.conflict_count == 0:
                return RouteResult(task, RouteDecision.DETERMINISTIC, "no cross-document conflicts — deterministic")
            reason = f"{context.conflict_count} conflict(s) need reconciliation reasoning"
            return self._decide_llm(
                task,
                reason,
                tokens_saved_est=400,
                tokens_used_est=400 + 200,
            )

        if task in (ZtaTask.SCORE, ZtaTask.PRICE, ZtaTask.DECIDE):
            if context.required_features_present:
                return RouteResult(
                    task,
                    RouteDecision.DETERMINISTIC,
                    f"{task.value} solved by rule engine + trained ML model — zero tokens",
                )
            missing = ", ".join(context.missing_required[:3]) or "required inputs"
            return RouteResult(
                task,
                RouteDecision.ESCALATE_HUMAN,
                f"{task.value} blocked — missing required inputs: {missing}",
            )

        if task == ZtaTask.MEMO:
            if not self._allow_llm() or not self.config.memo_llm:
                return RouteResult(
                    task,
                    RouteDecision.DETERMINISTIC,
                    "memo built deterministically from agent findings (template)",
                    tokens_saved_est=600,
                )
            self._llm_tasks_used += 1
            return RouteResult(task, RouteDecision.LLM, "memo is generative output", tokens_used_est=600 + 250)

        if task == ZtaTask.VISION:
            if self.config.strict or not self.llm_available:
                return RouteResult(task, RouteDecision.SKIP, "photo analysis has no deterministic substitute — skipped")
            self._llm_tasks_used += 1
            return RouteResult(task, RouteDecision.LLM, "photo analysis is vision-only (LLM)", tokens_used_est=500 * max(1, context.photo_count))

        return RouteResult(task, RouteDecision.DETERMINISTIC, "task has no registered heuristics — assume deterministic")
