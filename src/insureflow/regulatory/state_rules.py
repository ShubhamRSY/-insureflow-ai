from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from insureflow.regulatory.models import (
    ComplianceFlag,
    ComplianceSeverity,
    LineSpecificRule,
    RateFilingMethod,
    StateComplianceResult,
    StateRule,
    SurplusLinesRequirement,
    TortModel,
)

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"

LINE_FILES: dict[str, str] = {
    "auto": "auto.yaml",
    "property": "property.yaml",
    "liability": "liability.yaml",
    "workers_comp": "workers_comp.yaml",
    "life": "life.yaml",
    "health": "health.yaml",
    "cyber": "cyber.yaml",
    "marine": "marine.yaml",
    "financial": "financial.yaml",
    "specialty": "specialty.yaml",
    "package": "package.yaml",
    "flood": "flood.yaml",
}

_LINE_ALIASES: dict[str, str] = {
    "auto": "auto",
    "automobile": "auto",
    "car": "auto",
    "personal_auto": "auto",
    "commercial_auto": "auto",
    "property": "property",
    "commercial_property": "property",
    "homeowners": "property",
    "home": "property",
    "dwelling": "property",
    "liability": "liability",
    "general_liability": "liability",
    "professional_liability": "liability",
    "gl": "liability",
    "e_o": "liability",
    "e_and_o": "liability",
    "workers_comp": "workers_comp",
    "workers_compensation": "workers_comp",
    "wc": "workers_comp",
    "workforce": "workers_comp",
    "life": "life",
    "life_insurance": "life",
    "term_life": "life",
    "whole_life": "life",
    "universal_life": "life",
    "annuity": "life",
    "health": "health",
    "health_insurance": "health",
    "medical": "health",
    "group_health": "health",
    "individual_health": "health",
    "cyber": "cyber",
    "data_breach": "cyber",
    "cybersecurity": "cyber",
    "marine": "marine",
    "ocean_marine": "marine",
    "inland_marine": "marine",
    "financial": "financial",
    "credit": "financial",
    "credit_life": "financial",
    "specialty": "specialty",
    "excess": "specialty",
    "surplus_lines": "specialty",
    "e_s": "specialty",
    "package": "package",
    "bundle": "package",
    "bundled": "package",
    "commercial_package": "package",
    "flood": "flood",
    "nfip": "flood",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_line(line: str) -> Optional[str]:
    normalized = line.lower().strip().replace("-", "_").replace(" ", "_")
    return _LINE_ALIASES.get(normalized, _LINE_ALIASES.get(line.lower().strip()))


class StateRegulatoryEngine:
    """Loads per-state regulatory rules (general + line-specific) and produces compliance flags."""

    def __init__(self) -> None:
        self._general_rules: dict[str, StateRule] = {}
        self._line_rules: dict[str, dict[str, dict[str, Any]]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            self._load_general()
            self._load_line_rules()
            self._loaded = True
            line_summary = ", ".join(f"{k}({len(v)})" for k, v in self._line_rules.items() if v)
            logger.info(
                "Loaded general rules for %d jurisdictions; line-specific: %s",
                len(self._general_rules),
                line_summary,
            )
        except Exception as exc:
            logger.warning("Failed to load regulatory rules: %s", exc)

    def _load_general(self) -> None:
        path = _DATA_DIR / "state_rules.yaml"
        if not path.exists():
            return
        data = _load_yaml(path)
        for code, raw in data.get("states", {}).items():
            self._general_rules[code.upper()] = self._parse_general_rule(code.upper(), raw)

    def _load_line_rules(self) -> None:
        for line_key, filename in LINE_FILES.items():
            path = _DATA_DIR / filename
            if not path.exists():
                continue
            data = _load_yaml(path)
            states_data = data.get("states", {})
            if not states_data:
                continue
            self._line_rules[line_key] = {}
            for code, raw in states_data.items():
                self._line_rules[line_key][code.upper()] = {
                    "name": raw.get("name", code),
                    **{k: v for k, v in raw.items() if k != "name"},
                }

    @staticmethod
    def _parse_general_rule(code: str, raw: dict[str, Any]) -> StateRule:
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
        return self._general_rules.get(state_code.upper())

    def get_line_rule(self, state_code: str, line_of_business: str) -> Optional[LineSpecificRule]:
        self._ensure_loaded()
        resolved = _resolve_line(line_of_business)
        if not resolved:
            return None
        states = self._line_rules.get(resolved, {})
        raw = states.get(state_code.upper())
        if raw is None:
            return None
        return LineSpecificRule(
            state_code=state_code.upper(),
            state_name=raw.get("name", state_code),
            line_of_business=resolved,
            data={k: v for k, v in raw.items() if k != "name"},
        )

    def get_all_rules(self) -> dict[str, StateRule]:
        self._ensure_loaded()
        return dict(self._general_rules)

    def get_all_line_rules(self, line_of_business: str) -> dict[str, LineSpecificRule]:
        self._ensure_loaded()
        resolved = _resolve_line(line_of_business)
        if not resolved:
            return {}
        states = self._line_rules.get(resolved, {})
        return {
            code: LineSpecificRule(
                state_code=code,
                state_name=raw.get("name", code),
                line_of_business=resolved,
                data={k: v for k, v in raw.items() if k != "name"},
            )
            for code, raw in states.items()
        }

    def get_available_states(self) -> list[str]:
        self._ensure_loaded()
        return sorted(self._general_rules.keys())

    def get_available_lines(self) -> list[str]:
        self._ensure_loaded()
        return sorted(self._line_rules.keys())

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
        """Evaluate compliance flags for a submission in a given state and line."""
        self._ensure_loaded()
        rule = self.get_rule(state_code)
        line_rule = self.get_line_rule(state_code, line_of_business) if line_of_business else None

        if rule is None and line_rule is None:
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

        if rule is not None:
            flags.extend(self._check_general_flags(rule, state_code, is_surplus_lines, is_windstorm_zone, has_oral_binder, is_admitted))

        if line_rule is not None:
            flags.extend(self._check_line_flags(line_rule, state_code, line_of_business))

        summary = f"{rule.state_name}: rate_filing={rule.rate_filing.value}, tort={rule.tort_model.value}" if rule else ""
        if rule and rule.surplus_lines:
            summary += f", surplus_lines_tax={rule.surplus_lines_tax_rate * 100:.2f}%"
        if rule and rule.claims_prompt_pay_days:
            summary += f", claims_pay={rule.claims_prompt_pay_days}d"
        if line_rule:
            summary += f" [{line_of_business}: {len(line_rule.data)} fields]"

        return StateComplianceResult(
            state_code=state_code,
            state_name=rule.state_name if rule else line_rule.state_name if line_rule else state_code,
            flags=flags,
            rule=rule,
            line_rule=line_rule,
            summary=summary,
        )

    def _check_general_flags(
        self,
        rule: StateRule,
        state_code: str,
        is_surplus_lines: bool,
        is_windstorm_zone: bool,
        has_oral_binder: bool,
        is_admitted: bool,
    ) -> list[ComplianceFlag]:
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

        return flags

    def _check_line_flags(
        self,
        line_rule: LineSpecificRule,
        state_code: str,
        line_of_business: str,
    ) -> list[ComplianceFlag]:
        flags: list[ComplianceFlag] = []
        data = line_rule.data
        resolved_line = _resolve_line(line_of_business) or line_of_business

        # Rate filing for this specific line
        line_rate_filing = data.get("rate_filing", "")
        if line_rate_filing and line_rate_filing == "prior_approval":
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="rate_filing",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{line_rule.state_name} requires prior approval for {resolved_line} rate changes",
                    action_required=f"Ensure {resolved_line} rate filing is approved before quoting",
                    line_of_business=resolved_line,
                )
            )

        # No-fault / PIP (auto-specific)
        pip_required = data.get("pip_required", data.get("mandatory_pip", False))
        if pip_required:
            pip_amount = data.get("pip_amount", data.get("minimum_pip_amount", ""))
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="mandatory_pip",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{line_rule.state_name} requires PIP for auto: {pip_amount}",
                    action_required=f"Ensure PIP coverage of {pip_amount} is included",
                    line_of_business=resolved_line,
                )
            )

        # UM/UIM requirements
        um_required = data.get("um_required", data.get("mandatory_um", False))
        if um_required:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="mandatory_um",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{line_rule.state_name} requires uninsured motorist coverage",
                    action_required="Ensure UM coverage is offered/accepted",
                    line_of_business=resolved_line,
                )
            )

        uim_required = data.get("uim_required", data.get("mandatory_uim", False))
        if uim_required:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="mandatory_uim",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{line_rule.state_name} requires underinsured motorist coverage",
                    action_required="Ensure UIM coverage is offered/accepted",
                    line_of_business=resolved_line,
                )
            )

        # Windstorm deductible (property)
        wind_deductible = data.get("windstorm_hurricane_deductible", data.get("hurricane_deductible", False))
        if wind_deductible:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="windstorm",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{line_rule.state_name} requires windstorm/hurricane deductible for {resolved_line}",
                    action_required="Ensure windstorm deductible is disclosed and accepted",
                    line_of_business=resolved_line,
                )
            )

        # Data breach notification (cyber)
        breach_days = data.get("data_breach_notification_days")
        if breach_days:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="data_breach",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{line_rule.state_name} data breach notification: {breach_days} days",
                    action_required=f"Ensure breach response plan meets {breach_days}-day notification window",
                    line_of_business=resolved_line,
                )
            )

        breach_ag = data.get("data_breach_notification_ag", False)
        if breach_ag:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="data_breach",
                    severity=ComplianceSeverity.INFO,
                    message=f"{line_rule.state_name} requires AG notification for data breach",
                    action_required="Notify state Attorney General per breach notification statute",
                    line_of_business=resolved_line,
                )
            )

        # State fund (workers comp)
        state_fund = data.get("state_fund", False)
        if state_fund:
            fund_type = data.get("state_fund_type", "")
            if fund_type == "monopolistic":
                flags.append(
                    ComplianceFlag(
                        state_code=state_code,
                        rule_category="state_fund",
                        severity=ComplianceSeverity.CRITICAL,
                        message=f"{line_rule.state_name} has monopolistic state fund — must purchase from state",
                        action_required="Cannot purchase from private carriers; purchase from state fund",
                        line_of_business=resolved_line,
                    )
                )
            else:
                flags.append(
                    ComplianceFlag(
                        state_code=state_code,
                        rule_category="state_fund",
                        severity=ComplianceSeverity.WARNING,
                        message=f"{line_rule.state_name} has competitive state fund for {resolved_line}",
                        action_required="State fund is available but private market may also be used",
                        line_of_business=resolved_line,
                    )
                )

        # Individual mandate (health)
        indiv_mandate = data.get("state_individual_mandate", False)
        if indiv_mandate:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="individual_mandate",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{line_rule.state_name} has state individual health insurance mandate",
                    action_required="Ensure individual mandate compliance is addressed",
                    line_of_business=resolved_line,
                )
            )

        # Free look period (life)
        free_look = data.get("free_look_period_days")
        if free_look and int(free_look) > 10:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="free_look",
                    severity=ComplianceSeverity.INFO,
                    message=f"{line_rule.state_name} requires {free_look}-day free look period for life insurance",
                    action_required=f"Ensure {free_look}-day free look disclosure is provided",
                    line_of_business=resolved_line,
                )
            )

        # Surplus lines (specialty)
        sl_tax = data.get("surplus_lines_tax_rate")
        if sl_tax and float(sl_tax) > 0:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="surplus_lines_tax",
                    severity=ComplianceSeverity.INFO,
                    message=f"{line_rule.state_name} surplus lines tax for {resolved_line}: {float(sl_tax) * 100:.2f}%",
                    action_required="Collect and remit surplus lines tax",
                    line_of_business=resolved_line,
                )
            )

        diligent_search = data.get("diligent_search_required", False)
        if diligent_search:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="diligent_search",
                    severity=ComplianceSeverity.WARNING,
                    message=f"{line_rule.state_name} requires diligent search for admitted coverage",
                    action_required="Document diligent search — at least 3 admitted carriers declined",
                    line_of_business=resolved_line,
                )
            )

        # NFIP participation (flood)
        nfip = data.get("nfip_participation", False)
        if nfip:
            flags.append(
                ComplianceFlag(
                    state_code=state_code,
                    rule_category="nfip",
                    severity=ComplianceSeverity.INFO,
                    message=f"{line_rule.state_name} participates in NFIP for flood insurance",
                    action_required="Check NFIP participation and community rating",
                    line_of_business=resolved_line,
                )
            )

        # Minimum limits (generic)
        min_limits = data.get("minimum_limits")
        if isinstance(min_limits, dict):
            for limit_type, limit_value in min_limits.items():
                if limit_value:
                    flags.append(
                        ComplianceFlag(
                            state_code=state_code,
                            rule_category="minimum_limits",
                            severity=ComplianceSeverity.INFO,
                            message=f"{line_rule.state_name} minimum {limit_type}: {limit_value}",
                            action_required=f"Ensure minimum {limit_type} limit of {limit_value}",
                            line_of_business=resolved_line,
                        )
                    )

        # Required coverages (generic)
        required_covs = data.get("required_coverages", [])
        if isinstance(required_covs, list):
            for cov in required_covs:
                if cov:
                    flags.append(
                        ComplianceFlag(
                            state_code=state_code,
                            rule_category="required_coverage",
                            severity=ComplianceSeverity.WARNING,
                            message=f"{line_rule.state_name} requires {cov} for {resolved_line}",
                            action_required=f"Ensure {cov} coverage is included",
                            line_of_business=resolved_line,
                        )
                    )

        return flags

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
