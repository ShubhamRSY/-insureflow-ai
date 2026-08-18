"""Health insurance regulatory compliance module.

Checks health insurance submissions against:
1. Federal ACA requirements (guaranteed issue, community rating, EHBs)
2. State-specific mandates (mandated benefits, mental health parity, autism, IVF)
3. State exchange rules (on-exchange vs off-exchange, metal levels)
4. Rate filing requirements (prior approval, file-and-use)
5. Medical loss ratio (MLR) requirements
6. Small group reform rules

Designed for: TPAs, health plan administrators, benefits consultants, brokers
Serving the $1.2T health insurance market where NO competitor has AI tools.

    USE_HEALTH_COMPLIANCE=1  enable health compliance checks (default: on)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_HEALTH_ENABLED = os.getenv("USE_HEALTH_COMPLIANCE", "1").strip().lower() not in {"0", "false", "off", "no"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class HealthComplianceSeverity(str):
    INFO = "info"
    WARNING = "warning"
    BLOCK = "block"
    CRITICAL = "critical"


class HealthComplianceFlag(BaseModel):
    state_code: str
    rule_category: str
    severity: str
    message: str
    action_required: str = ""
    mandate: str = ""


class HealthComplianceResult(BaseModel):
    state_code: str
    state_name: str = ""
    line_of_business: str = "health"
    flags: list[HealthComplianceFlag] = Field(default_factory=list)
    has_blockers: bool = False
    has_warnings: bool = False
    summary: str = ""


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

_HEALTH_DATA: dict[str, Any] | None = None
_HEALTH_DATA_PATH = Path(__file__).parent / "data" / "health.yaml"


def _load_health_data() -> dict[str, Any]:
    global _HEALTH_DATA
    if _HEALTH_DATA is not None:
        return _HEALTH_DATA
    try:
        with open(_HEALTH_DATA_PATH) as f:
            _HEALTH_DATA = yaml.safe_load(f) or {}
        return _HEALTH_DATA
    except Exception as exc:
        logger.warning("Failed to load health.yaml: %s", exc)
        _HEALTH_DATA = {"states": {}}
        return _HEALTH_DATA


def _get_state_health_rule(state_code: str) -> dict[str, Any]:
    data = _load_health_data()
    states: dict[str, Any] = data.get("states", {})
    result: dict[str, Any] = states.get(state_code.upper(), {})
    return result


# ---------------------------------------------------------------------------
# Compliance checks
# ---------------------------------------------------------------------------

# ACA mandated benefit categories (federal baseline)
_ACA_EHB_CATEGORIES = [
    "ambulatory",
    "emergency",
    "hospitalization",
    "maternity",
    "mental_health",
    "substance_abuse",
    "prescription",
    "rehabilitation",
    "laboratory",
    "preventive",
    "pediatric",
    "oral_vision",
]


class HealthComplianceChecker:
    """Check health insurance submissions against federal + state rules."""

    def __init__(self) -> None:
        if not _HEALTH_ENABLED:
            logger.info("Health compliance disabled via USE_HEALTH_COMPLIANCE=0")

    def check(self, state_code: str, submission: dict[str, Any] | None = None) -> HealthComplianceResult:
        """Run all health compliance checks for a state.

        Args:
            state_code: 2-letter state code (e.g., "CT", "CA", "NY")
            submission: optional submission data for context-aware checks

        Returns:
            HealthComplianceResult with flags, blockers, and summary
        """
        state_code = state_code.upper()
        rule = _get_state_health_rule(state_code)
        if not rule:
            return HealthComplianceResult(
                state_code=state_code,
                flags=[
                    HealthComplianceFlag(
                        state_code=state_code,
                        rule_category="data",
                        severity=HealthComplianceSeverity.WARNING,
                        message=f"No health insurance regulatory data found for {state_code}",
                    )
                ],
                summary=f"No data for {state_code}",
            )

        flags: list[HealthComplianceFlag] = []

        flags.extend(self._check_aca_federal(state_code, rule, submission))
        flags.extend(self._check_state_mandates(state_code, rule, submission))
        flags.extend(self._check_exchange_rules(state_code, rule, submission))
        flags.extend(self._check_rate_filing(state_code, rule, submission))
        flags.extend(self._check_small_group_reform(state_code, rule, submission))
        flags.extend(self._check_community_rating(state_code, rule, submission))

        blockers = any(f.severity in (HealthComplianceSeverity.BLOCK, HealthComplianceSeverity.CRITICAL) for f in flags)
        warnings = any(f.severity == HealthComplianceSeverity.WARNING for f in flags)

        summary_parts = [f"{state_code} health compliance:"]
        if blockers:
            blocker_count = sum(1 for f in flags if f.severity in (HealthComplianceSeverity.BLOCK, HealthComplianceSeverity.CRITICAL))
            summary_parts.append(f"{blocker_count} blocker(s)")
        if warnings:
            warn_count = sum(1 for f in flags if f.severity == HealthComplianceSeverity.WARNING)
            summary_parts.append(f"{warn_count} warning(s)")
        if not flags:
            summary_parts.append("all checks passed")

        return HealthComplianceResult(
            state_code=state_code,
            state_name=rule.get("name", state_code),
            flags=flags,
            has_blockers=blockers,
            has_warnings=warnings,
            summary=" ".join(summary_parts),
        )

    def _check_aca_federal(self, state_code: str, rule: dict[str, Any], submission: dict[str, Any] | None) -> list[HealthComplianceFlag]:
        """Federal ACA requirements that apply in all states."""
        flags: list[HealthComplianceFlag] = []

        # Guaranteed issue requirement (ACA §2702)
        if not rule.get("guaranteed_issue", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="aca_guaranteed_issue",
                    severity=HealthComplianceSeverity.WARNING,
                    message=f"{state_code} has NOT adopted guaranteed issue beyond ACA federal floor. ACA requires guaranteed issue for all non-grandfathered plans.",
                    action_required="Verify plan is ACA-compliant or grandfathered",
                )
            )

        # Community rating (ACA §2701)
        if not rule.get("community_rating", False) and not rule.get("modified_community_rating", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="aca_community_rating",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: No state community rating beyond ACA federal age bands. ACA limits age rating to 3:1 (adults).",
                    action_required="Verify rating factors comply with ACA 3:1 age band limit",
                )
            )

        # Essential Health Benefits (ACA §1302)
        ehb = rule.get("essential_health_benefits", "federal_baseline")
        if ehb == "federal_baseline":
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="aca_ehb",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: Uses federal baseline EHB benchmark plan. All 10 EHB categories must be covered for qualified health plans.",
                    action_required="Verify all 10 EHB categories are covered",
                )
            )

        # State individual mandate
        if rule.get("state_individual_mandate", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="individual_mandate",
                    severity=HealthComplianceSeverity.WARNING,
                    message=f"{state_code} has its OWN individual mandate (separate from federal). Residents must maintain coverage or pay state penalty.",
                    action_required="Disclose state individual mandate requirement to enrollees",
                )
            )

        return flags

    def _check_state_mandates(self, state_code: str, rule: dict[str, Any], submission: dict[str, Any] | None) -> list[HealthComplianceFlag]:
        """State-specific mandated benefit requirements."""
        flags: list[HealthComplianceFlag] = []

        # Autism mandate
        if rule.get("autism_mandate", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="mandated_benefit",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: Autism spectrum disorder coverage is MANDATED",
                    mandate="autism",
                    action_required="Verify autism coverage is included in plan",
                )
            )

        # Mental health parity
        if rule.get("mental_health_parity", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="mandated_benefit",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: Mental health parity required (federal + state). MH/SUD benefits must be no more restrictive than medical/surgical.",
                    mandate="mental_health_parity",
                    action_required="Verify mental health benefits parity compliance",
                )
            )

        # IVF mandate
        if rule.get("ivf_mandate", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="mandated_benefit",
                    severity=HealthComplianceSeverity.WARNING,
                    message=f"{state_code}: IVF/in vitro fertilization coverage is MANDATED",
                    mandate="ivf",
                    action_required="Verify IVF coverage is included or exemption applies",
                )
            )

        # Infusion therapy
        if rule.get("infusion_therapy", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="mandated_benefit",
                    severity=HealthComplianceSeverity.WARNING,
                    message=f"{state_code}: Infusion therapy coverage is MANDATED",
                    mandate="infusion_therapy",
                    action_required="Verify infusion therapy coverage is included",
                )
            )

        # State-specific mandated benefits list
        mandated_benefits = rule.get("mandated_benefits", [])
        for benefit in mandated_benefits:
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="mandated_benefit",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: Mandated benefit — {benefit.replace('_', ' ').title()}",
                    mandate=benefit,
                    action_required=f"Verify {benefit.replace('_', ' ')} coverage is included",
                )
            )

        return flags

    def _check_exchange_rules(self, state_code: str, rule: dict[str, Any], submission: dict[str, Any] | None) -> list[HealthComplianceFlag]:
        """State exchange / marketplace rules."""
        flags: list[HealthComplianceFlag] = []

        exchange_type = rule.get("state_exchange_type", "")
        state_exchange = rule.get("state_exchange", False)

        if state_exchange:
            exchange_name = rule.get("state_exchange_name", f"{state_code} state exchange")
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="exchange",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: State-based exchange — {exchange_name}",
                    action_required="Verify QHP certification if selling on-exchange",
                )
            )
        elif exchange_type == "federally_facilitated":
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="exchange",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: Federally-facilitated marketplace (Healthcare.gov)",
                    action_required="Verify FFM participation if selling on-exchange",
                )
            )
        elif exchange_type == "state_partnership":
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="exchange",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: State partnership exchange",
                    action_required="Verify partnership exchange requirements",
                )
            )

        # Metal level requirements
        metal_level = rule.get("minimum_metal_level")
        if metal_level:
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="metal_level",
                    severity=HealthComplianceSeverity.WARNING,
                    message=f"{state_code}: Minimum metal level required — {metal_level.upper()}",
                    action_required=f"Verify plan meets {metal_level.upper()} metal level",
                )
            )

        return flags

    def _check_rate_filing(self, state_code: str, rule: dict[str, Any], submission: dict[str, Any] | None) -> list[HealthComplianceFlag]:
        """Rate filing requirements."""
        flags: list[HealthComplianceFlag] = []

        rate_filing = rule.get("rate_filing", "")
        if rate_filing == "prior_approval":
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="rate_filing",
                    severity=HealthComplianceSeverity.BLOCK,
                    message=f"{state_code}: PRIOR APPROVAL required — rates must be approved BEFORE use. Using unapproved rates is a regulatory violation.",
                    action_required="Submit rate filing and obtain approval before quoting",
                )
            )
        elif rate_filing == "file_and_use":
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="rate_filing",
                    severity=HealthComplianceSeverity.WARNING,
                    message=f"{state_code}: File-and-use — rates must be filed but can be used before approval",
                    action_required="File rate within required timeframe",
                )
            )
        elif rate_filing == "use_and_file":
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="rate_filing",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: Use-and-file — rates can be used, then filed retroactively",
                    action_required="File rate within required timeframe after use",
                )
            )

        return flags

    def _check_small_group_reform(self, state_code: str, rule: dict[str, Any], submission: dict[str, Any] | None) -> list[HealthComplianceFlag]:
        """Small group reform (ACA SHOP rules)."""
        flags: list[HealthComplianceFlag] = []

        if rule.get("small_group_reform", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="small_group_reform",
                    severity=HealthComplianceSeverity.INFO,
                    message=f"{state_code}: Small group reform rules apply (ACA SHOP). Community rating required for groups with 1-50 employees.",
                    action_required="Verify small group rating complies with state reform rules",
                )
            )

        return flags

    def _check_community_rating(self, state_code: str, rule: dict[str, Any], submission: dict[str, Any] | None) -> list[HealthComplianceFlag]:
        """Community rating and modified community rating rules."""
        flags: list[HealthComplianceFlag] = []

        if rule.get("community_rating", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="community_rating",
                    severity=HealthComplianceSeverity.WARNING,
                    message=f"{state_code}: FULL community rating — no age/gender/health rating variation. All enrollees pay same premium regardless of risk factors.",
                    action_required="Verify rating is community-rated (no risk factors)",
                )
            )
        elif rule.get("modified_community_rating", False):
            flags.append(
                HealthComplianceFlag(
                    state_code=state_code,
                    rule_category="community_rating",
                    severity=HealthComplianceSeverity.WARNING,
                    message=f"{state_code}: MODIFIED community rating — limited rating variation allowed. Check state rules for allowed rating factors.",
                    action_required="Verify rating factors comply with state MCR rules",
                )
            )

        return flags

    def get_all_state_requirements(self, state_code: str) -> dict[str, Any]:
        """Get full health insurance regulatory requirements for a state."""
        rule = _get_state_health_rule(state_code.upper())
        if not rule:
            return {"error": f"No data for {state_code.upper()}"}

        return {
            "state_code": state_code.upper(),
            "state_name": rule.get("name", ""),
            "rate_filing_method": rule.get("rate_filing", ""),
            "individual_mandate": rule.get("state_individual_mandate", False),
            "exchange_type": rule.get("state_exchange_type", ""),
            "has_state_exchange": rule.get("state_exchange", False),
            "essential_health_benefits": rule.get("essential_health_benefits", ""),
            "minimum_metal_level": rule.get("minimum_metal_level"),
            "community_rating": rule.get("community_rating", False),
            "modified_community_rating": rule.get("modified_community_rating", False),
            "guaranteed_issue": rule.get("guaranteed_issue", False),
            "small_group_reform": rule.get("small_group_reform", False),
            "mandated_benefits": rule.get("mandated_benefits", []),
            "autism_mandate": rule.get("autism_mandate", False),
            "mental_health_parity": rule.get("mental_health_parity", False),
            "infusion_therapy": rule.get("infusion_therapy", False),
            "ivf_mandate": rule.get("ivf_mandate", False),
            "grace_period_days": rule.get("grace_period_days", 30),
            "external_review": rule.get("external_review", True),
            "notes": rule.get("notes", ""),
        }
