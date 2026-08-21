"""Step 1 — Intake & Triage: 10-point checklist compliance.

If any critical item is missing the case is suspended (PENDING) and a broker
deficiency notice is triggered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import _blob, extract_life_factors

# 10-point US checklist — every item must pass for a clean intake
CHECKLIST_ITEMS: list[dict[str, Any]] = [
    {"id": "photo_id", "label": "Government-issued photo ID", "pattern": r"driver.?s?\s+licen[sc]e|state\s+id|passport|photo\s+id", "critical": True},
    {"id": "ssn", "label": "Social Security Number (SSN)", "pattern": r"\bssn\b|social\s+security", "critical": True},
    {"id": "proof_of_address", "label": "Proof of address", "pattern": r"utility\s+bill|bank\s+statement|lease\s+agree|proof\s+of\s+address|address\s+verif", "critical": False},
    {"id": "hipaa_auth", "label": "Signed HIPAA authorization", "pattern": r"hipaa|medical\s+records?\s+release|health\s+information", "critical": True},
    {"id": "mib_auth", "label": "MIB check authorization", "pattern": r"\bmib\b|medical\s+information\s+bureau", "critical": True},
    {"id": "rx_auth", "label": "Rx database check authorization", "pattern": r"rx\s+(?:check|database|history|script)|prescription\s+(?:check|database|history)", "critical": True},
    {"id": "application", "label": "Completed life insurance application", "pattern": r"life\s+insurance\s+applic|proposal\s+form|application\s+form|acord\s+100|acord\s+175", "critical": True},
    {"id": "beneficiary", "label": "Beneficiary details (name, DOB, relationship)", "pattern": r"beneficiar", "critical": True},
    {"id": "income_proof", "label": "Income proof (W-2, tax returns, pay stubs)", "pattern": r"w-?2|tax\s+return|pay\s+stub|income\s+proof|salary\s+slip|earnedincome", "critical": False},
    {"id": "health_questionnaire", "label": "Health questionnaire", "pattern": r"health\s+questionnaire|medical\s+history|health\s+history|paramed|physical\s+exam", "critical": False},
]


@dataclass
class ChecklistResult:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    missing_critical: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    all_passed: bool = True
    findings: list[Finding] = field(default_factory=list)
    decision: UWDecision = UWDecision.ACCEPT

    def to_metadata(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "missing_critical": self.missing_critical,
            "missing_optional": self.missing_optional,
            "all_passed": self.all_passed,
            "checklist_score": f"{len(self.passed)}/{len(CHECKLIST_ITEMS)}",
        }


def run_checklist(bundle: SubmissionBundle) -> ChecklistResult:
    blob = _blob(bundle)
    extract_life_factors(bundle)
    result = ChecklistResult()

    for item in CHECKLIST_ITEMS:
        found = bool(__import__("re").search(item["pattern"], blob, __import__("re").I))
        if found:
            result.passed.append(item["id"])
        else:
            result.failed.append(item["id"])
            if item["critical"]:
                result.missing_critical.append(item["id"])
                result.findings.append(
                    Finding(
                        title=f"Missing critical checklist item: {item['label']}",
                        description=f"The submission is missing {item['label']}, which is required for underwriting.",
                        severity=RiskSeverity.CRITICAL,
                        category="life_checklist",
                    )
                )
            else:
                result.missing_optional.append(item["id"])
                result.findings.append(
                    Finding(
                        title=f"Missing optional checklist item: {item['label']}",
                        description=f"{item['label']} is recommended but not required.",
                        severity=RiskSeverity.MODERATE,
                        category="life_checklist",
                    )
                )

    result.all_passed = len(result.missing_critical) == 0
    if not result.all_passed:
        result.decision = UWDecision.REFER

    return result
