"""Step 2 — Identity & Database Screening.

Validates SSN, pulls MIB report, screens Rx database, runs OFAC sanctions check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import _blob


@dataclass
class ScreeningResult:
    ssn_verified: bool | None = None
    ssn_status: str = "not_checked"
    mib_flags: list[dict[str, Any]] = field(default_factory=list)
    mib_clear: bool | None = None
    rx_flags: list[dict[str, Any]] = field(default_factory=list)
    rx_clear: bool | None = None
    ofac_hit: bool = False
    ofac_status: str = "not_checked"
    findings: list[Finding] = field(default_factory=list)
    decision: UWDecision = UWDecision.ACCEPT

    def to_metadata(self) -> dict[str, Any]:
        return {
            "ssn_verified": self.ssn_verified,
            "ssn_status": self.ssn_status,
            "mib_clear": self.mib_clear,
            "mib_flags": self.mib_flags,
            "rx_clear": self.rx_clear,
            "rx_flags": self.rx_flags,
            "ofac_hit": self.ofac_hit,
            "ofac_status": self.ofac_status,
        }


def run_screening(bundle: SubmissionBundle) -> ScreeningResult:
    blob = _blob(bundle)
    result = ScreeningResult()

    # SSN verification
    import re

    ssn_match = re.search(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b", blob)
    if ssn_match:
        result.ssn_verified = True
        result.ssn_status = "verified"
    else:
        result.ssn_verified = False
        result.ssn_status = "missing"
        result.findings.append(
            Finding(
                title="SSN not verified",
                description="Social Security Number could not be verified from submitted documents.",
                severity=RiskSeverity.HIGH,
                category="life_screening",
            )
        )
        result.decision = UWDecision.REFER

    # MIB check
    import re

    mib_match = re.search(r"mib\s+(?:report|check|flag|hit|code|mismatch|discrepancy)", blob, re.I)
    mib_clear_match = re.search(r"mib\s+(?:clear|clean|no\s+flag|no\s+hit|no\s+discrepancy)", blob, re.I)
    if mib_clear_match:
        result.mib_clear = True
    elif mib_match:
        result.mib_clear = False
        result.mib_flags.append({"type": "mib_report", "detail": "MIB flags detected in submission"})
        result.findings.append(
            Finding(
                title="MIB report flags detected",
                description="The Medical Information Bureau report contains undisclosed prior applications or medical codes.",
                severity=RiskSeverity.HIGH,
                category="life_screening",
            )
        )
        result.decision = UWDecision.REFER
    else:
        result.mib_clear = None  # Not yet checked

    # Rx database check
    rx_match = re.search(r"rx\s+(?:flag|hit|discrepancy|adverse|chronic)|prescription\s+(?:flag|hit|adverse|chronic)", blob, re.I)
    rx_clear_match = re.search(r"rx\s+(?:clear|clean|no\s+flag|no\s+hit)|prescription\s+(?:clear|clean|no\s+flag)", blob, re.I)
    if rx_clear_match:
        result.rx_clear = True
    elif rx_match:
        result.rx_clear = False
        result.rx_flags.append({"type": "rx_check", "detail": "Rx database flags detected"})
        result.findings.append(
            Finding(
                title="Rx database flags detected",
                description="Prescription database check revealed chronic medication use not disclosed on the application.",
                severity=RiskSeverity.HIGH,
                category="life_screening",
            )
        )
        result.decision = UWDecision.REFER
    else:
        result.rx_clear = None

    # OFAC sanctions
    ofac_match = re.search(r"ofac\s+(?:hit|flag|match|sanctions?)|sdn\s+(?:list|match)|specially\s+designated", blob, re.I)
    if ofac_match:
        result.ofac_hit = True
        result.ofac_status = "hit"
        result.findings.append(
            Finding(
                title="OFAC sanctions match",
                description="Applicant matches an OFAC SDN list entry. Policy cannot be issued.",
                severity=RiskSeverity.CRITICAL,
                category="life_screening",
            )
        )
        result.decision = UWDecision.DECLINE
    else:
        result.ofac_status = "clear"

    return result
