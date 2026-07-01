from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.portfolio.treaty import get_treaty_store


class ReinsuranceAgent(BaseAgent):
    """Evaluates whether a new submission fits within the carrier's
    existing reinsurance treaty structure. Checks treaty eligibility,
    aggregate utilization, and facultative thresholds."""

    agent_type = AgentType.REINSURANCE
    agent_name = "ReinsuranceAgent"

    def __init__(self) -> None:
        super().__init__()
        self._treaty_store = get_treaty_store()

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        state = ""
        naics_code = ""
        occupancy_type = ""
        tiv = 0.0
        premium = 0.0

        if bundle.structured:
            if bundle.structured.locations:
                state = bundle.structured.locations[0].state or ""
                occupancy_type = bundle.structured.locations[0].building_occupancy or ""
            if bundle.structured.risk_profile:
                naics_code = bundle.structured.risk_profile.naics_code or ""
            for loc in bundle.structured.locations:
                tiv += (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
            for cov in bundle.structured.coverages:
                premium += cov.premium

        if not state and not naics_code:
            for doc in bundle.unstructured:
                for fields in doc.extracted_fields.get("state", []):
                    state = fields.value
                for fields in doc.extracted_fields.get("naics_code", []):
                    naics_code = fields.value
                for fields in doc.extracted_fields.get("occupancy_type", []):
                    occupancy_type = fields.value

        allocations = self._treaty_store.apply_treaties(
            tiv=tiv,
            premium=premium,
            state=state,
            naics_code=naics_code,
            occupancy_type=occupancy_type,
        )

        self._add_finding(
            Finding(
                title="Reinsurance treaty analysis",
                description=f"Evaluated {len(allocations)} treaties for risk TIV ${tiv:,.0f}, premium ${premium:,.0f}",
                severity=RiskSeverity.LOW,
                category="reinsurance",
                evidence=[
                    f"State: {state}",
                    f"NAICS: {naics_code}",
                    f"Occupancy: {occupancy_type}",
                ],
            )
        )

        treaties_available = [a for a in allocations if a.is_applicable]
        if not treaties_available:
            self._add_finding(
                Finding(
                    title="No applicable reinsurance treaty",
                    description=f"Risk TIV ${tiv:,.0f} does not fit any active treaty — facultative placement required before binding",
                    severity=RiskSeverity.CRITICAL,
                    category="reinsurance",
                    source_value=tiv,
                )
            )
            return

        for alloc in allocations:
            if alloc.is_applicable:
                self._add_finding(
                    Finding(
                        title=f"Treaty applicable: {alloc.treaty_name}",
                        description=f"{alloc.treaty_type.value} treaty — cedes {alloc.ceded_pct:.0%} (${alloc.ceded_amount:,.0f})",
                        severity=RiskSeverity.LOW,
                        category="reinsurance",
                        source_value=alloc.ceded_amount,
                    )
                )
            else:
                self._add_finding(
                    Finding(
                        title=f"Treaty not applicable: {alloc.treaty_name}",
                        description=f"Excluded: {alloc.exclusion_reason}",
                        severity=RiskSeverity.MODERATE
                        if "exhausted" in alloc.exclusion_reason
                        else RiskSeverity.LOW,
                        category="reinsurance",
                        evidence=[alloc.exclusion_reason],
                    )
                )

        total_ceded = sum(a.ceded_amount for a in allocations if a.is_applicable)
        retained = tiv - total_ceded

        self._add_finding(
            Finding(
                title="Reinsurance summary",
                description=f"Ceded: ${total_ceded:,.0f}, Retained: ${retained:,.0f} ({retained / tiv:.0%} of TIV)"
                if tiv > 0
                else "No TIV to cede",
                severity=RiskSeverity.MODERATE if retained > 15_000_000 else RiskSeverity.LOW,
                category="reinsurance",
                source_value=retained,
            )
        )

        if retained > 15_000_000:
            self._add_finding(
                Finding(
                    title="High net retention — UW approval required",
                    description=f"Net retention of ${retained:,.0f} exceeds $15M threshold — senior underwriter sign-off needed",
                    severity=RiskSeverity.HIGH,
                    category="reinsurance",
                    source_value=retained,
                )
            )
