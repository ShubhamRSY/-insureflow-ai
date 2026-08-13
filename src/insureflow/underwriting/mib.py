"""Medical Information Bureau (MIB) report handling — Chapter 4.

Chapter 4's life-underwriting preliminary processing includes requesting an
MIB report on the applicant. The MIB alerts underwriters to information that
may differ from the application (heart disease, cancer, hazardous avocations,
etc.) so the underwriter can order medical records. This module models the
report, its coded findings, and the discrepancy check against the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import SubmissionBundle

MIB_NS = "mib"


class MibCodeType(str, Enum):
    HEART_DISEASE = "heart_disease"
    CANCER = "cancer"
    HYPERTENSION = "hypertension"
    DIABETES = "diabetes"
    PSYCHOLOGICAL = "psychological"
    SUBSTANCE_ABUSE = "substance_abuse"
    HAZARDOUS_AVOCATION = "hazardous_avocation"
    MOTOR_VEHICLE = "motor_vehicle"
    UNKNOWN = "unknown"


@dataclass
class MibCode:
    """One coded finding on an MIB report."""

    code: str
    code_type: MibCodeType
    description: str
    reported_date: Optional[date] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "code_type": self.code_type.value,
            "description": self.description,
            "reported_date": self.reported_date.isoformat() if self.reported_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MibCode:
        rd = data.get("reported_date")
        return cls(
            code=data["code"],
            code_type=MibCodeType(data.get("code_type", "unknown")),
            description=data.get("description", ""),
            reported_date=date.fromisoformat(rd) if rd else None,
        )


class MibDiscrepancy(BaseModel):
    code_type: MibCodeType
    description: str
    severity: RiskSeverity = RiskSeverity.MODERATE
    reason: str = ""


class MibReport(BaseModel):
    """An MIB report returned for an applicant."""

    applicant_name: str = ""
    report_date: date = Field(default_factory=date.today)
    report_id: str = ""
    codes: list[MibCode] = Field(default_factory=list)
    no_hit: bool = False
    discrepancies: list[MibDiscrepancy] = Field(default_factory=list)

    @property
    def has_discrepancies(self) -> bool:
        return len(self.discrepancies) > 0


# Common MIB codes → type/description mapping (illustrative, non-exhaustive).
_MIB_CODE_TABLE: dict[str, tuple[MibCodeType, str]] = {
    "HD": (MibCodeType.HEART_DISEASE, "Heart disease"),
    "CAN": (MibCodeType.CANCER, "Cancer"),
    "HTN": (MibCodeType.HYPERTENSION, "Hypertension"),
    "DIA": (MibCodeType.DIABETES, "Diabetes"),
    "PSY": (MibCodeType.PSYCHOLOGICAL, "Psychological condition"),
    "SUB": (MibCodeType.SUBSTANCE_ABUSE, "Substance abuse"),
    "HAZ": (MibCodeType.HAZARDOUS_AVOCATION, "Hazardous avocation"),
    "MVA": (MibCodeType.MOTOR_VEHICLE, "Motor vehicle record"),
}


def _known_code_table() -> dict[str, tuple[MibCodeType, str]]:
    return dict(_MIB_CODE_TABLE)


def request_mib_report(bundle: SubmissionBundle) -> MibReport:
    """Build the MIB report for an applicant, reading any submitted report.

    In production the report is fetched from the bureau; for the automation the
    report may arrive with the submission (parsed from an uploaded document).
    If the submission carries MIB codes they are decoded here; otherwise the
    report is created as a no-hit pending report.
    """
    structured = bundle.structured
    applicant = (structured.named_insured.legal_name if structured and structured.named_insured else "") or ""
    report = MibReport(applicant_name=applicant)

    codes_raw: list[tuple[str, str]] = []
    for doc in (bundle.unstructured or []) + (bundle.supplemental or []):
        for fv in doc.extracted_fields.get("mib_code", []):
            codes_raw.append((fv.value, doc.document_type))

    table = _known_code_table()
    if not codes_raw:
        report.no_hit = True
        try:
            from insureflow.billing.plan import current_plan

            if current_plan().require_live_oracles:
                report.discrepancies.append(
                    MibDiscrepancy(
                        code_type=MibCodeType.UNKNOWN,
                        description="Live MIB required",
                        severity=RiskSeverity.CRITICAL,
                        reason="Desk+ does not treat a simulated MIB no-hit or auth form as a bureau query. Upload an MIB report or connect a live vendor.",
                    )
                )
        except Exception:
            pass
        return report

    for code, _src in codes_raw:
        normalized = code.strip().upper()
        if normalized not in table:
            report.codes.append(
                MibCode(
                    code=normalized,
                    code_type=MibCodeType.UNKNOWN,
                    description=f"Unrecognized MIB code {normalized}",
                )
            )
            continue
        code_type, description = table[normalized]
        report.codes.append(MibCode(code=normalized, code_type=code_type, description=description))

    report.discrepancies = process_mib_codes(report.codes, _disclosed_conditions(bundle))
    return report


def process_mib_codes(
    codes: list[MibCode],
    disclosed_conditions: list[str],
) -> list[MibDiscrepancy]:
    """Compare MIB-coded findings against conditions disclosed on the application.

    Any MIB condition not disclosed on the application is a discrepancy the
    underwriter must resolve by ordering medical records before binding.
    """
    discrepancies: list[MibDiscrepancy] = []
    disclosed_lower = " ".join(disclosed_conditions).lower()

    for code in codes:
        if code.code_type == MibCodeType.UNKNOWN:
            discrepancies.append(
                MibDiscrepancy(
                    code_type=code.code_type,
                    description=code.description,
                    severity=RiskSeverity.HIGH,
                    reason="Unrecognized MIB code requires manual review",
                )
            )
            continue

        keyword = code.description.lower()
        if keyword in disclosed_lower:
            continue
        severity = RiskSeverity.CRITICAL if code.code_type in (MibCodeType.HEART_DISEASE, MibCodeType.CANCER) else RiskSeverity.HIGH
        discrepancies.append(
            MibDiscrepancy(
                code_type=code.code_type,
                description=code.description,
                severity=severity,
                reason=f"MIB reports '{code.description}' but the application does not disclose it — order APS / medical records",
            )
        )
    return discrepancies


def _disclosed_conditions(bundle: SubmissionBundle) -> list[str]:
    conditions: list[str] = []
    for doc in (bundle.unstructured or []) + (bundle.supplemental or []):
        for fv in doc.extracted_fields.get("disclosed_condition", []):
            conditions.append(fv.value)
        for fv in doc.extracted_fields.get("medical_condition", []):
            conditions.append(fv.value)
    return conditions


def persist_mib_report(report: MibReport, org_id: str = "default") -> None:
    """Persist an MIB report for auditability on the case file."""
    from insureflow.storage.job_store import get_job_store

    data = {
        "applicant_name": report.applicant_name,
        "report_date": report.report_date.isoformat(),
        "report_id": report.report_id,
        "no_hit": report.no_hit,
        "codes": [c.to_dict() for c in report.codes],
        "discrepancies": [d.model_dump() for d in report.discrepancies],
    }
    get_job_store().set(MIB_NS, f"applicant:{report.applicant_name.lower()}", data, org_id=org_id)
