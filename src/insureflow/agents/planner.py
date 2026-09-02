"""Deterministic pre-dispatch agent planning.

The multi-agent system (SupervisorAgent) always runs the same fixed set of
specialist agents, the same way, regardless of what the submission actually
looks like. This is the missing "dynamic task planning/routing" piece: a
fast, explainable, LLM-free pass that decides which specialist agents are
actually worth running for THIS submission — and records why, so a skipped
check is a visible, auditable decision, never a silent one.

Opt-in only: SupervisorAgent.analyze_submission(..., auto_plan=True). The
default (auto_plan=False) leaves every existing caller's behavior
unchanged — this never runs unless explicitly requested.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from insureflow.agents.tools import UnderwritingTools
from insureflow.models.submissions import SubmissionBundle
from insureflow.privacy.decision_memory import tiv_band
from insureflow.rating.models import is_non_property_line

# Fraud ML scoring is skipped only at the smallest TIV band -- reuses the
# exact banding decision_memory.py already established, rather than
# inventing a second, unrelated materiality threshold.
_LOW_MATERIALITY_TIV_BAND = "0-250k"


@dataclass
class AgentPlan:
    run_loss_run_analyst: bool = True
    skip_ml_fraud: bool = False
    reasons: list[str] = field(default_factory=list)

    def note(self, reason: str) -> None:
        self.reasons.append(reason)


class AgentPlanner:
    """Deterministic, LLM-free planning pass over a submission.

    Every rule here already exists as a judgment call somewhere else in the
    pipeline (LossRunAnalystAgent already no-ops on non-property lines;
    funnel mode already defers fraud_ml wholesale) — this just makes those
    same judgment calls automatically, per-submission, instead of requiring
    the caller to either always pay the cost or manually opt out of
    everything via funnel mode.
    """

    def __init__(self, tools: UnderwritingTools | None = None) -> None:
        self.tools = tools or UnderwritingTools()

    def plan(self, bundle: SubmissionBundle, insurance_line: str | None = None) -> AgentPlan:
        decision = AgentPlan()

        if is_non_property_line(insurance_line):
            # LossRunAnalystAgent's own _analyze() already returns
            # immediately for these lines (no P&C-style claims loss-run
            # concept) -- not dispatching it at all saves the thread/Celery
            # slot instead of paying for a no-op.
            decision.run_loss_run_analyst = False
            decision.note(f"Skipped LossRunAnalystAgent — {insurance_line or 'this line'} has no P&C-style claims loss-run concept")
            return decision

        locations = self.tools.get_locations(bundle)
        if not locations:
            return decision
        tiv = self.tools.total_insurable_value(locations)
        if tiv_band(tiv) == _LOW_MATERIALITY_TIV_BAND:
            decision.skip_ml_fraud = True
            decision.note(f"Skipped deep fraud ML scoring — total insurable value ${tiv:,.0f} is in the lowest materiality band ({_LOW_MATERIALITY_TIV_BAND})")

        return decision
