"""Surplus lines / E&S compliance module.

Checks surplus lines submissions against state-specific requirements:
1. Diligent search (3 admitted carriers must be approached)
2. Stamping office filing requirements
3. Tax calculation and remittance
4. Broker of record / license verification
5. Export fee calculation
6. State-specific filing deadlines

Designed for: Surplus lines brokers, wholesale brokers, program administrators
Serving the $80B+ surplus lines market where compliance errors = $50K+ fines.

    USE_SURPLUS_LINES_COMPLIANCE=1  enable surplus lines checks (default: on)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_SL_ENABLED = os.getenv("USE_SURPLUS_LINES_COMPLIANCE", "1").strip().lower() not in {"0", "false", "off", "no"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DiligentSearchEntry(BaseModel):
    carrier_name: str
    declination_reason: str = ""
    declination_date: str = ""
    coverage_offered: bool = False


class SurplusLinesComplianceFlag(BaseModel):
    state_code: str
    rule_category: str
    severity: str
    message: str
    action_required: str = ""


class SurplusLinesComplianceResult(BaseModel):
    state_code: str
    state_name: str = ""
    line_of_business: str = "surplus_lines"
    flags: list[SurplusLinesComplianceFlag] = Field(default_factory=list)
    has_blockers: bool = False
    has_warnings: bool = False
    tax_amount: float = 0.0
    stamping_fee: float = 0.0
    export_fee: float = 0.0
    total_fees: float = 0.0
    summary: str = ""


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

_SL_DATA: dict[str, Any] | None = None
_SL_DATA_PATH = Path(__file__).parent / "data" / "specialty.yaml"


def _load_sl_data() -> dict[str, Any]:
    global _SL_DATA
    if _SL_DATA is not None:
        return _SL_DATA
    try:
        with open(_SL_DATA_PATH) as f:
            _SL_DATA = yaml.safe_load(f) or {}
        return _SL_DATA
    except Exception as exc:
        logger.warning("Failed to load specialty.yaml: %s", exc)
        _SL_DATA = {"states": {}}
        return _SL_DATA


def _get_state_sl_rule(state_code: str) -> dict[str, Any]:
    data = _load_sl_data()
    states = data.get("states", {})
    return states.get(state_code.upper(), {})


# ---------------------------------------------------------------------------
# Compliance checks
# ---------------------------------------------------------------------------


class SurplusLinesComplianceChecker:
    """Check surplus lines submissions against state-specific requirements."""

    def __init__(self) -> None:
        if not _SL_ENABLED:
            logger.info("Surplus lines compliance disabled via USE_SURPLUS_LINES_COMPLIANCE=0")

    def check(
        self,
        state_code: str,
        premium: float = 0.0,
        diligent_search: list[DiligentSearchEntry] | None = None,
        submission: dict[str, Any] | None = None,
    ) -> SurplusLinesComplianceResult:
        """Run all surplus lines compliance checks for a state.

        Args:
            state_code: 2-letter state code
            premium: policy premium amount (for tax calculation)
            diligent_search: list of admitted carriers approached (for diligent search verification)
            submission: optional submission data

        Returns:
            SurplusLinesComplianceResult with flags, fees, and summary
        """
        state_code = state_code.upper()
        rule = _get_state_sl_rule(state_code)
        if not rule:
            return SurplusLinesComplianceResult(
                state_code=state_code,
                flags=[
                    SurplusLinesComplianceFlag(
                        state_code=state_code,
                        rule_category="data",
                        severity="warning",
                        message=f"No surplus lines regulatory data found for {state_code}",
                    )
                ],
                summary=f"No data for {state_code}",
            )

        flags: list[SurplusLinesComplianceFlag] = []

        flags.extend(self._check_diligent_search(state_code, rule, diligent_search))
        flags.extend(self._check_stamping_office(state_code, rule))
        flags.extend(self._check_broker_license(state_code, rule))
        flags.extend(self._check_filing_deadline(state_code, rule))

        # Calculate fees
        tax_rate = rule.get("surplus_lines_tax_rate", 0.0)
        stamping_fee = rule.get("surplus_lines_stamping_fee", 0.0)
        export_fee = rule.get("export_fee", 0.0) * premium if premium > 0 else 0.0
        tax_amount = premium * tax_rate if premium > 0 else 0.0

        blockers = any(f.severity in ("block", "critical") for f in flags)
        warnings = any(f.severity == "warning" for f in flags)

        summary_parts = [f"{state_code} surplus lines:"]
        if blockers:
            blocker_count = sum(1 for f in flags if f.severity in ("block", "critical"))
            summary_parts.append(f"{blocker_count} blocker(s)")
        if warnings:
            warn_count = sum(1 for f in flags if f.severity == "warning")
            summary_parts.append(f"{warn_count} warning(s)")
        if tax_amount > 0:
            summary_parts.append(f"tax=${tax_amount:,.2f}")
        if not flags:
            summary_parts.append("all checks passed")

        return SurplusLinesComplianceResult(
            state_code=state_code,
            state_name=rule.get("name", state_code),
            flags=flags,
            has_blockers=blockers,
            has_warnings=warnings,
            tax_amount=round(tax_amount, 2),
            stamping_fee=round(stamping_fee, 2),
            export_fee=round(export_fee, 2),
            total_fees=round(tax_amount + stamping_fee + export_fee, 2),
            summary=" ".join(summary_parts),
        )

    def _check_diligent_search(
        self,
        state_code: str,
        rule: dict[str, Any],
        diligent_search: list[DiligentSearchEntry] | None,
    ) -> list[SurplusLinesComplianceFlag]:
        """Verify diligent search requirements — the #1 compliance risk in surplus lines."""
        flags: list[SurplusLinesComplianceFlag] = []

        required_carriers = rule.get("diligent_search_carriers", 3)

        if not rule.get("diligent_search_required", False):
            flags.append(
                SurplusLinesComplianceFlag(
                    state_code=state_code,
                    rule_category="diligent_search",
                    severity="info",
                    message=f"{state_code}: Diligent search NOT required for surplus lines placement",
                )
            )
            return flags

        if diligent_search is None:
            flags.append(
                SurplusLinesComplianceFlag(
                    state_code=state_code,
                    rule_category="diligent_search",
                    severity="block",
                    message=f"{state_code}: Diligent search REQUIRED — {required_carriers} admitted carriers must be approached. NO SEARCH RECORD PROVIDED.",
                    action_required="Record diligent search: approach " + str(required_carriers) + " admitted carriers and document declinations",
                )
            )
            return flags

        # Count carriers approached
        carriers_approached = len(diligent_search)
        if carriers_approached < required_carriers:
            flags.append(
                SurplusLinesComplianceFlag(
                    state_code=state_code,
                    rule_category="diligent_search",
                    severity="block",
                    message=f"{state_code}: Diligent search INCOMPLETE — {carriers_approached} carriers approached, {required_carriers} required.",
                    action_required=f"Approach {required_carriers - carriers_approached} more admitted carrier(s)",
                )
            )
        else:
            flags.append(
                SurplusLinesComplianceFlag(
                    state_code=state_code,
                    rule_category="diligent_search",
                    severity="info",
                    message=f"{state_code}: Diligent search satisfied — {carriers_approached} carriers approached ({required_carriers} required)",
                )
            )

        # Check each entry has declination reason
        for i, entry in enumerate(diligent_search):
            if not entry.declination_reason:
                flags.append(
                    SurplusLinesComplianceFlag(
                        state_code=state_code,
                        rule_category="diligent_search",
                        severity="warning",
                        message=f"{state_code}: Carrier #{i + 1} ({entry.carrier_name}) — no declination reason recorded",
                        action_required="Document why carrier declined coverage",
                    )
                )

        return flags

    def _check_stamping_office(self, state_code: str, rule: dict[str, Any]) -> list[SurplusLinesComplianceFlag]:
        """Check stamping office filing requirements."""
        flags: list[SurplusLinesComplianceFlag] = []

        if rule.get("stamping_office", False):
            flags.append(
                SurplusLinesComplianceFlag(
                    state_code=state_code,
                    rule_category="stamping_office",
                    severity="warning",
                    message=f"{state_code}: Stamping office filing REQUIRED. Surplus lines policies must be submitted to the state stamping office.",
                    action_required="Submit policy to stamping office within required timeframe",
                )
            )
        else:
            flags.append(
                SurplusLinesComplianceFlag(
                    state_code=state_code,
                    rule_category="stamping_office",
                    severity="info",
                    message=f"{state_code}: No stamping office filing required",
                )
            )

        return flags

    def _check_broker_license(self, state_code: str, rule: dict[str, Any]) -> list[SurplusLinesComplianceFlag]:
        """Check surplus lines broker license requirements."""
        flags: list[SurplusLinesComplianceFlag] = []

        if rule.get("surplus_lines_broker_license", False):
            flags.append(
                SurplusLinesComplianceFlag(
                    state_code=state_code,
                    rule_category="broker_license",
                    severity="warning",
                    message=f"{state_code}: Surplus lines broker license REQUIRED. General producer license is NOT sufficient.",
                    action_required="Verify surplus lines broker license is current and valid",
                )
            )

        return flags

    def _check_filing_deadline(self, state_code: str, rule: dict[str, Any]) -> list[SurplusLinesComplianceFlag]:
        """Check filing deadline requirements."""
        flags: list[SurplusLinesComplianceFlag] = []

        deadline_days = rule.get("filing_deadline_days")
        if deadline_days:
            flags.append(
                SurplusLinesComplianceFlag(
                    state_code=state_code,
                    rule_category="filing_deadline",
                    severity="warning",
                    message=f"{state_code}: Filing deadline — {deadline_days} days from policy effective date",
                    action_required=f"Complete all filings within {deadline_days} days",
                )
            )

        return flags

    def calculate_fees(self, state_code: str, premium: float) -> dict[str, float]:
        """Calculate total surplus lines fees for a state and premium.

        Returns dict with tax, stamping_fee, export_fee, total.
        """
        rule = _get_state_sl_rule(state_code.upper())
        if not rule:
            return {"tax": 0.0, "stamping_fee": 0.0, "export_fee": 0.0, "total": 0.0}

        tax = premium * rule.get("surplus_lines_tax_rate", 0.0)
        stamping = rule.get("surplus_lines_stamping_fee", 0.0)
        export = premium * rule.get("export_fee", 0.0)
        total = tax + stamping + export

        return {
            "tax": round(tax, 2),
            "stamping_fee": round(stamping, 2),
            "export_fee": round(export, 2),
            "total": round(total, 2),
        }

    def get_all_state_requirements(self, state_code: str) -> dict[str, Any]:
        """Get full surplus lines regulatory requirements for a state."""
        rule = _get_state_sl_rule(state_code.upper())
        if not rule:
            return {"error": f"No data for {state_code.upper()}"}

        return {
            "state_code": state_code.upper(),
            "state_name": rule.get("name", ""),
            "tax_rate": rule.get("surplus_lines_tax_rate", 0.0),
            "stamping_office": rule.get("stamping_office", False),
            "stamping_fee": rule.get("surplus_lines_stamping_fee", 0.0),
            "diligent_search_required": rule.get("diligent_search_required", False),
            "diligent_search_carriers": rule.get("diligent_search_carriers", 3),
            "broker_license_required": rule.get("surplus_lines_broker_license", False),
            "export_fee_rate": rule.get("export_fee", 0.0),
            "filing_deadline_days": rule.get("filing_deadline_days"),
            "notes": rule.get("notes", ""),
        }
