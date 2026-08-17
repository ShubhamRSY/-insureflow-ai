from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from insureflow.regulatory.models import (
    ComplianceFlag,
    ComplianceSeverity,
    RateFilingMethod,
    StateComplianceResult,
    StateRule,
    SurplusLinesRequirement,
    TortModel,
)

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_RULES_FILE = _DATA_DIR / "state_rules.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class StateRegulatoryEngine:
    """Loads per-state regulatory rules and produces compliance flags."""

    def __init__(self) -> None:
        self._rules: dict[str, StateRule] = {}
        self._raw: dict[str, Any] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            data = _load_yaml(_RULES_FILE)
            raw_states = data.get("states", {})
            for code, raw in raw_states.items():
                self._rules[code.upper()] = self._parse_rule(code.upper(), raw)
            self._raw = raw_states
            self._loaded = True
            logger.info("Loaded state rules for %d jurisdictions", len(self._rules))
        except Exception as exc:
            logger.warning("Failed to load state rules: %s", exc)

    @staticmethod
    def _parse_rule(code: str, raw: dict[str, Any]) -> StateRule:
        def _enum_safe(cls: Any, val: str, default: Any) -> Any:
            try:
                return cls(val)
            except (ValueError, KeyError):
                return default

        sl_raw = raw.get("surplus_lines", [])
        sl_reqs: list[SurplusLinesRequirement] = []
        for s in sl_raw:
            try:
                sl_reqs.append(SurplusLinesRequirement(s))
            except (ValueError, KeyError):
                pass

        return StateRule(
            state_code=code,
            state_name=raw.get("name", code),
            rate_filing=_enum_safe(RateFilingMethod, raw.get("rate_filing", "no_file"), RateFilingMethod.NO_FILE),
            rate_filing_notes=raw.get("rate_filing_notes", ""),
            surplus_lines=sl_reqs,
            surplus_lines_notes=raw.get("surplus_lines_notes", ""),
            binder_requires_written=bool(raw.get("binder_requires_written", False)),
            binder_notes=raw.get("binder_notes", ""),
            claims_prompt_pay_days=raw.get("claims_prompt_pay_days"),
            claims_notes=raw.get("claims_notes", ""),
            commission_cap_pct=raw.get("commission_cap_pct"),
            commission_cap_notes=raw.get("commission_cap_notes", ""),
            tort_model=_enum_safe(TortModel, raw.get("tort_model", "pure_comparative"), TortModel.PURE_COMPARATIVE),
            tort_notes=raw.get("tort_notes", ""),
            windstorm_hurricane_deductible=bool(raw.get("windstorm_hurricane_deductible", False)),
            windstorm_notes=raw.get("windstorm_notes", ""),
            hurricane_license_required=bool(raw.get("hurricane_license_required", False)),
            workers_comp_state_fund=bool(raw.get("workers_comp_state_fund", False)),
            workers_comp_notes=raw.get("workers_comp_notes", ""),
            surplus_lines_tax_rate=float(raw.get("surplus_lines_tax_rate", 0.0)),
            surplus_lines_stamping_fee=float(raw.get("surplus_lines_stamping_fee", 0.0)),
            admitted_only=bool(raw.get("admitted_only", False)),
            admitted_notes=raw.get("admitted_notes", ""),
            mandatory_coverages=raw.get("mandatory_coverages", []),
            mandatory_coverages_notes=raw.get("mandatory_coverages_notes", ""),
            regulatory_notes=raw.get("regulatory_notes", ""),
        )

    def get_rule(self, state_code: str) -> Optional[StateRule]:
        self._ensure_loaded()
        return self._rules.get(state_code.upper())

    def get_all_rules(self) -> dict[str, StateRule]:
        self._ensure_loaded()
        return dict(self._rules)

    def get_available_states(self) -> list[str]:
        self._ensure_loaded()
        return sorted(self._rules.keys())

    def detect_state(self, locations: list[dict[str, str]]) -> str:
        """Extract primary state from submission locations."""
        for loc in locations:
            state = loc.get("state", "").strip().upper()
            if state and len(state) == 2:
                return state
            city = loc.get("city", "").strip()
            if city:
                state_from_city = self._resolve_state_from_city(city)
                if state_from_city:
                    return state_from_city
        return ""

    @staticmethod
    def _resolve_state_from_city(city: str) -> str:
        city_state_map: dict[str, str] = {
            "new york": "NY",
            "los angeles": "CA",
            "chicago": "IL",
            "houston": "TX",
            "phoenix": "AZ",
            "philadelphia": "PA",
            "san antonio": "TX",
            "san diego": "CA",
            "dallas": "TX",
            "san jose": "CA",
            "austin": "TX",
            "jacksonville": "FL",
            "fort worth": "TX",
            "columbus": "OH",
            "charlotte": "NC",
            "indianapolis": "IN",
            "san francisco": "CA",
            "seattle": "WA",
            "denver": "CO",
            "nashville": "TN",
            "oklahoma city": "OK",
            "el paso": "TX",
            "boston": "MA",
            "portland": "OR",
            "las vegas": "NV",
            "memphis": "TN",
            "louisville": "KY",
            "baltimore": "MD",
            "milwaukee": "WI",
            "albuquerque": "NM",
            "tucson": "AZ",
            "fresno": "CA",
            "sacramento": "CA",
            "mesa": "AZ",
            "kansas city": "MO",
            "atlanta": "GA",
            "omaha": "NE",
            "miami": "FL",
            "minneapolis": "MN",
            "new orleans": "LA",
            "cleveland": "OH",
            "tampa": "FL",
            "honolulu": "HI",
            "detroit": "MI",
            "st louis": "MO",
        }
        return city_state_map.get(city.lower().strip(), "")

    def evaluate(
        self,
        state_code: str,
        *,
        line_of_business: str = "",
        is_surplus_lines: bool = False,
        is_windstorm_zone: bool = False,
        has_oral_binder: bool = False,
        is_admitted: bool = True,
    ) -> StateComplianceResult:
        """Evaluate compliance flags for a submission in a given state."""
        self._ensure_loaded()
        rule = self.get_rule(state_code)
        if rule is None:
            return StateComplianceResult(
                state_code=state_code,
                state_name=state_code,
                flags=[
                    ComplianceFlag(
                        state_code=state_code,
                        rule_category="unknown_state",
                        severity=ComplianceSeverity.WARNING,
                        message=f"No regulatory rules found for state '{state_code}'",
                        action_required="Verify state code; consult state DOI manual",
                    )
                ],
                summary=f"No rules loaded for {state_code}",
            )

        flags: list[ComplianceFlag] = []

        if rule.rate_filing == RateFilingMethod.PRIOR_APPROVAL:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="rate_filing",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{rule.state_name} requires prior approval for rate changes",
                    action_required="Ensure rate filing is approved before quoting",
                )
            )

        if rule.binder_requires_written and has_oral_binder:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="binder",
                    severity=ComplianceSeverity.ERROR,
                    message=f"{rule.state_name} requires written binder; oral binder not valid",
                    action_required="Issue written binder immediately",
                )
            )

        if is_surplus_lines:
            if SurplusLinesRequirement.DILIGENT_SEARCH in rule.surplus_lines:
                flags.append(
                    ComplianceFlag(
                        state_code=state_code,
                        rule_category="surplus_lines",
                        severity=ComplianceSeverity.WARNING,
                        message=f"{rule.state_name} requires diligent search for admitted coverage before placing surplus lines",
                        action_required="Document diligent search — at least 3 admitted carriers declined",
                    )
                )
            if SurplusLinesRequirement.STAMPING_OFFICE in rule.surplus_lines:
                flags.append(
                    ComplianceFlag(
                        state_code=state_code,
                        rule_category="surplus_lines",
                        severity=ComplianceSeverity.INFO,
                        message=f"{rule.state_name} requires surplus lines stamping office filing",
                        action_required="Submit policy to state stamping office",
                    )
                )
            if rule.surplus_lines_tax_rate > 0:
                flags.append(
                    ComplianceFlag(
                        state_code=state_code,
                        rule_category="surplus_lines",
                        severity=ComplianceSeverity.INFO,
                        message=f"{rule.state_name} surplus lines tax: {rule.surplus_lines_tax_rate * 100:.2f}%",
                        action_required="Collect and remit surplus lines tax",
                    )
                )

        if rule.claims_prompt_pay_days is not None and rule.claims_prompt_pay_days <= 20:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="claims_handling",
                    severity=ComplianceSeverity.INFO,
                    message=f"{rule.state_name} has strict prompt pay: {rule.claims_prompt_pay_days} days",
                    action_required=f"Ensure claims are processed within {rule.claims_prompt_pay_days} days",
                )
            )

        if is_windstorm_zone and rule.windstorm_hurricane_deductible:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="windstorm",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{rule.state_name} requires hurricane/windstorm deductible disclosure",
                    action_required="Ensure hurricane deductible is disclosed and accepted by insured",
                )
            )

        if not is_admitted and rule.admitted_only:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="admitted",
                    severity=ComplianceSeverity.CRITICAL,
                    message=f"{rule.state_name} may require admitted carrier coverage",
                    action_required="Verify non-admitted placement is permitted",
                )
            )

        for cov in rule.mandatory_coverages:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="mandatory_coverage",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{rule.state_name} mandates: {cov}",
                    action_required=f"Verify {cov} coverage is included or waiver obtained",
                )
            )

        summary = f"{rule.state_name}: rate_filing={rule.rate_filing.value}, tort={rule.tort_model.value}"
        if rule.surplus_lines:
            summary += f", surplus_lines_tax={rule.surplus_lines_tax_rate * 100:.2f}%"
        if rule.claims_prompt_pay_days:
            summary += f", claims_pay={rule.claims_prompt_pay_days}d"

        return StateComplianceResult(
            state_code=state_code,
            state_name=rule.state_name,
            flags=flags,
            rule=rule,
            summary=summary,
        )

    def check_coverage_admitted(self, state_code: str, line_of_business: str, coverage_type: str) -> dict[str, Any]:
        """Check if a coverage is admitted in a state (simplified lookup)."""
        rule = self.get_rule(state_code)
        if rule is None:
            return {"admitted": None, "notes": f"No data for {state_code}"}
        return {
            "admitted": not rule.admitted_only,
            "rate_filing_method": rule.rate_filing.value,
            "notes": rule.admitted_notes or rule.regulatory_notes,
        }
