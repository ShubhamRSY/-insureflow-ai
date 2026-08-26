"""MIB ordering agent — requests and tracks MIB bureau reports.

Extends the existing MIB module to support ordering from the bureau
and tracking order lifecycle through completion.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.mib_ordering import (
    MibOrderPriority,
    MibOrderResult,
    build_mib_order_from_bundle,
    persist_mib_order,
)
from insureflow.underwriting.personal_lines import extract_life_factors


class MibOrderAgent(BaseAgent):
    agent_type = AgentType.MIB_ORDER
    agent_name = "mib_order_agent"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        factors = extract_life_factors(bundle)
        face = float(factors.face_amount or 0)

        priority = MibOrderPriority.ROUTINE
        if face >= 5_000_000:
            priority = MibOrderPriority.EXPEDITED
        if face >= 10_000_000:
            priority = MibOrderPriority.URGENT

        result: MibOrderResult = build_mib_order_from_bundle(
            bundle, priority=priority, requesting_agent=self.agent_name
        )
        persist_mib_order(result.order)

        for f in result.findings:
            self._add_finding(f)

        if result.report and result.report.no_hit:
            self._add_finding(
                Finding(
                    title="MIB order completed — no hit",
                    description="MIB returned no records for this applicant.",
                    severity=RiskSeverity.LOW,
                    category="mib_order",
                )
            )
        elif result.codes_found > 0:
            self._add_finding(
                Finding(
                    title=f"MIB order completed — {result.codes_found} code(s)",
                    description=f"MIB returned {result.codes_found} code(s) with {result.discrepancy_count} discrepancy(ies).",
                    severity=RiskSeverity.HIGH if result.discrepancy_count > 0 else RiskSeverity.LOW,
                    category="mib_order",
                )
            )

        self._order_result = result

    def _build_summary(self) -> str:
        if hasattr(self, "_order_result"):
            r = self._order_result
            return f"MIB order {r.order.order_id}: status={r.order.status.value}, codes={r.codes_found}, discrepancies={r.discrepancy_count}"
        return super()._build_summary()
