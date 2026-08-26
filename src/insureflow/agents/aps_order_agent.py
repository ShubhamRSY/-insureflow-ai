"""APS ordering agent — manages Attending Physician Statement requests.

Creates APS orders when medical records are required, tracks order status,
and validates prerequisites (HIPAA authorization, physician identification).
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.aps_ordering import (
    ApsOrderPriority,
    ApsOrderResult,
    ApsPhysicianInfo,
    create_aps_order,
    persist_aps_order,
    process_aps_order,
)
from insureflow.underwriting.personal_lines import extract_life_factors


class ApsOrderAgent(BaseAgent):
    agent_type = AgentType.APS_ORDER
    agent_name = "aps_order_agent"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        factors = extract_life_factors(bundle)
        face = float(factors.face_amount or 0)
        age = factors.age or 40

        priority = ApsOrderPriority.ROUTINE
        if face >= 3_000_000:
            priority = ApsOrderPriority.EXPEDITED
        if face >= 10_000_000:
            priority = ApsOrderPriority.RUSH

        physician = ApsPhysicianInfo()
        blob_lower = " ".join(
            doc.raw_text for doc in (bundle.unstructured or []) if doc.raw_text
        ).lower() if bundle.unstructured else ""

        import re
        name_m = re.search(r"physician\s*[:=]\s*([A-Za-z][A-Za-z ,.'-]{2,50})", blob_lower)
        if name_m:
            physician.name = name_m.group(1).strip()
        spec_m = re.search(r"specialty\s*[:=]\s*([A-Za-z][A-Za-z /-]{2,30})", blob_lower)
        if spec_m:
            physician.specialty = spec_m.group(1).strip()

        order = create_aps_order(
            bundle,
            physician=physician,
            priority=priority,
            requesting_agent=self.agent_name,
        )
        result: ApsOrderResult = process_aps_order(order)
        persist_aps_order(order)

        for f in result.findings:
            self._add_finding(f)

        if order.hipaa_authorization_on_file:
            self._add_finding(
                Finding(
                    title="HIPAA authorization on file",
                    description="APS order can proceed — authorization confirmed.",
                    severity=RiskSeverity.LOW,
                    category="aps_order",
                )
            )

        self._order_result = result

    def _build_summary(self) -> str:
        if hasattr(self, "_order_result"):
            r = self._order_result
            return f"APS order {r.order.order_id}: physician={r.order.physician.name or 'unknown'}, status={r.order.status.value}"
        return super()._build_summary()
