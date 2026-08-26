"""Policy issuance agent — validates issuance readiness and creates binders.

Checks all prerequisites for policy issuance and generates binder records
when the case is ready for binding.
"""

from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import extract_life_factors
from insureflow.underwriting.policy_issuance import (
    IssuanceStatus,
    PolicyIssuanceData,
    PolicyType,
    check_issuance_readiness,
    create_binder,
    persist_binder,
)


class PolicyIssuanceAgent(BaseAgent):
    agent_type = AgentType.POLICY_ISSUANCE
    agent_name = "policy_issuance_agent"

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        factors = extract_life_factors(bundle)
        decision = kwargs.get("decision", UWDecision.ACCEPT)
        face = float(factors.face_amount or 0)

        readiness = check_issuance_readiness(
            decision=decision,
            has_aps=kwargs.get("has_aps", False),
            aps_reviewed=kwargs.get("aps_reviewed", False),
            has_mib=kwargs.get("has_mib", False),
            has_hipaa=kwargs.get("has_hipaa", False),
            has_beneficiary=kwargs.get("has_beneficiary", False),
            has_financial_uw=kwargs.get("has_financial_uw", False),
            reinsured=kwargs.get("reinsured", False),
            reinsured_placed=kwargs.get("reinsured_placed", False),
            premium_calculated=kwargs.get("premium_calculated", False),
            reinsurance_fac_required=kwargs.get("reinsurance_fac_required", False),
            reinsurance_placed=kwargs.get("reinsurance_placed", False),
            human_review_cleared=kwargs.get("human_review_cleared", False),
            all_conditions_met=kwargs.get("all_conditions_met", False),
        )

        for f in readiness.findings:
            self._add_finding(f)

        if readiness.status == IssuanceStatus.PENDING_UW_APPROVAL:
            policy_data = PolicyIssuanceData(
                face_amount=face,
                insured_name="",
                policy_type=PolicyType.TERM_LIFE,
                underwriting_class=kwargs.get("underwriting_class", "standard"),
                annual_premium=kwargs.get("annual_premium", 0),
                monthly_premium=kwargs.get("annual_premium", 0) / 12,
            )
            binder = create_binder(bundle.bundle_id or "", policy_data, issued_by="system")
            persist_binder(binder)
            self._add_finding(
                Finding(
                    title="Binder ready for issuance",
                    description=f"All {len(readiness.ready_checklist)} readiness checks passed. Binder {binder.binder_id} created.",
                    severity=RiskSeverity.LOW,
                    category="policy_issuance",
                )
            )
            self._binder = binder
        elif readiness.blocking_items:
            self._add_finding(
                Finding(
                    title=f"{len(readiness.blocking_items)} item(s) blocking issuance",
                    description=f"Blocking: {', '.join(readiness.blocking_items[:5])}",
                    severity=RiskSeverity.HIGH,
                    category="policy_issuance",
                )
            )

        self._readiness = readiness

    def _build_summary(self) -> str:
        if hasattr(self, "_readiness"):
            r = self._readiness
            return f"Issuance readiness: {r.status.value}, blocking={len(r.blocking_items)}, checklist_pass={sum(1 for v in r.ready_checklist.values() if v)}/{len(r.ready_checklist)}"
        return super()._build_summary()
