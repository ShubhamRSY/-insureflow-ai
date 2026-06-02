from __future__ import annotations

from typing import Any

from insureflow.agents.base import BaseAgent
from insureflow.agents.react_agent import ReActAgent
from insureflow.agents.tools import UnderwritingTools
from insureflow.models.agents import AgentType, Finding, RiskSeverity
from insureflow.models.submissions import LocationData, SubmissionBundle


class RiskAnalystAgent(ReActAgent):
    agent_type = AgentType.RISK_ANALYST
    agent_name = "RiskAnalystAgent"
    prompt_key = "risk_analyst"

    def __init__(self, tools: UnderwritingTools | None = None) -> None:
        super().__init__()
        self.tools = tools or UnderwritingTools()

    def _analyze(self, bundle: SubmissionBundle, **kwargs: Any) -> None:
        profile = self.tools.get_risk_profile(bundle)
        locations = self.tools.get_locations(bundle)

        if profile:
            self._assess_construction(profile)
            self._assess_protection(profile)
            self._assess_sprinklers(profile)
            self._assess_occupancy(profile)

        for loc in locations:
            self._assess_location(loc)

        sovs = self.tools.get_sovs(bundle)
        if sovs:
            self._assess_sov_adequacy(sovs, locations)

    def _assess_construction(self, profile: Any) -> None:
        ctype = profile.construction_type
        if not ctype:
            return
        ctype_lower = ctype.lower()
        hazardous = ("wood", "frame", "combustible")
        fire_resistive = ("steel", "concrete", "fireproof", "masonry")
        if any(h in ctype_lower for h in hazardous) and not any(
            f in ctype_lower for f in fire_resistive
        ):
            self._add_finding(Finding(
                title="Higher-risk construction type",
                description=f"Construction type '{ctype}' has elevated fire risk",
                severity=RiskSeverity.HIGH,
                category="construction",
                field_path="risk_profile.construction_type",
                source_value=ctype,
            ))
        elif any(f in ctype_lower for f in fire_resistive):
            self._add_finding(Finding(
                title="Favorable construction type",
                description=f"Construction type '{ctype}' is fire-resistive",
                severity=RiskSeverity.LOW,
                category="construction",
                field_path="risk_profile.construction_type",
                source_value=ctype,
            ))

    def _assess_protection(self, profile: Any) -> None:
        pclass = profile.protection_class
        sev = self.tools.protection_class_risk(pclass)
        if sev in (RiskSeverity.HIGH, RiskSeverity.CRITICAL):
            self._add_finding(Finding(
                title="Elevated protection class",
                description=f"Protection class {pclass} indicates limited fire protection",
                severity=sev,
                category="protection",
                field_path="risk_profile.protection_class",
                source_value=str(pclass) if pclass else None,
            ))

    def _assess_sprinklers(self, profile: Any) -> None:
        if profile.sprinklered is not None:
            sev = self.tools.sprinkler_risk(profile.sprinklered)
            if sev == RiskSeverity.HIGH:
                self._add_finding(Finding(
                    title="Missing sprinkler system",
                    description="Building is not sprinklered — significant fire risk",
                    severity=RiskSeverity.HIGH,
                    category="sprinklers",
                    field_path="risk_profile.sprinklered",
                    source_value=False,
                ))
            elif sev == RiskSeverity.LOW:
                self._add_finding(Finding(
                    title="Sprinklered building",
                    description="Building has sprinkler system — fire risk mitigated",
                    severity=RiskSeverity.LOW,
                    category="sprinklers",
                    field_path="risk_profile.sprinklered",
                    source_value=True,
                ))

    def _assess_occupancy(self, profile: Any) -> None:
        occ = profile.occupancy_type
        if not occ:
            return
        occ_lower = occ.lower()
        hazardous = ("manufacturing", "chemical", "warehouse", "processing", "storage")
        if any(h in occ_lower for h in hazardous):
            self._add_finding(Finding(
                title="Higher-risk occupancy",
                description=f"Occupancy '{occ}' has elevated hazard profile",
                severity=RiskSeverity.MODERATE,
                category="occupancy",
                field_path="risk_profile.occupancy_type",
                source_value=occ,
            ))

    def _assess_location(self, loc: LocationData) -> None:
        if loc.year_built:
            sev = self.tools.year_built_risk(loc.year_built)
            if sev in (RiskSeverity.HIGH, RiskSeverity.CRITICAL):
                self._add_finding(Finding(
                    title="Aging building",
                    description=f"Location at {loc.address} built in {loc.year_built}",
                    severity=sev,
                    category="age",
                    field_path="location.year_built",
                    source_value=loc.year_built,
                ))

        if loc.building_value and loc.square_footage:
            value_per_sqft = loc.building_value / loc.square_footage
            if value_per_sqft > 500:
                self._add_finding(Finding(
                    title="High building value density",
                    description=f"${value_per_sqft:,.0f}/sqft at {loc.address}",
                    severity=RiskSeverity.MODERATE,
                    category="valuation",
                    field_path="location.building_value",
                    source_value=loc.building_value,
                ))

    def _assess_sov_adequacy(
        self, sovs: Any, locations: list[LocationData]
    ) -> None:
        total_sov = sum(s.total_value for s in sovs)
        total_loc = self.tools.total_insurable_value(
            [l for l in locations if isinstance(l, LocationData)]
        )
        if total_loc > 0 and total_sov > 0:
            ratio = total_sov / total_loc
            if ratio < 0.8:
                self._add_finding(Finding(
                    title="Schedule of Values may be understated",
                    description=f"SOV total ${total_sov:,.0f} vs location total ${total_loc:,.0f} ({ratio:.0%})",
                    severity=RiskSeverity.MODERATE,
                    category="valuation",
                    field_path="schedule_of_values",
                ))
