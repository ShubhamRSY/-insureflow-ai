"""Pilot package PII screening before underwriting."""

from __future__ import annotations

from typing import Any

from insureflow.pilot.package_loader import PilotPackage
from insureflow.redaction.detector import PIICategory, PIIDetector

# Categories that must be cleared (or explicitly waived) before pilot ingest
BLOCKING = {
    PIICategory.SSN,
    PIICategory.CREDIT_CARD,
    PIICategory.BANK_ACCOUNT,
    PIICategory.PASSPORT,
    PIICategory.DRIVERS_LICENSE,
    PIICategory.MEDICAL_RECORD,
    PIICategory.DATE_OF_BIRTH,
}

# Expected on commercial submissions — warn only
WARNING = {
    PIICategory.EMAIL,
    PIICategory.PHONE,
    PIICategory.TAX_ID,
    PIICategory.NAME,
    PIICategory.ADDRESS,
}


def scan_pilot_package(package: PilotPackage) -> dict[str, Any]:
    detector = PIIDetector()
    texts: list[tuple[str, str]] = []
    if package.acord_xml:
        texts.append(("acord.xml", package.acord_xml))
    if package.loss_run:
        texts.append(("loss_run", package.loss_run))
    if package.schedule_of_values:
        texts.append(("sov", package.schedule_of_values))
    for i, doc in enumerate(package.inspection_reports):
        texts.append((f"inspection_{i + 1}", doc))
    for i, doc in enumerate(package.supplemental_docs):
        texts.append((f"supplemental_{i + 1}", doc))

    findings: list[dict[str, Any]] = []
    blocking = 0
    warning = 0
    for source, text in texts:
        for span in detector.detect(text or ""):
            level = "block" if span.category in BLOCKING else "warn" if span.category in WARNING else "info"
            if level == "block":
                blocking += 1
            elif level == "warn":
                warning += 1
            findings.append(
                {
                    "source": source,
                    "category": span.category.value,
                    "level": level,
                    "preview": span.text[:24] + ("…" if len(span.text) > 24 else ""),
                    "score": span.score,
                }
            )

    return {
        "partner": package.partner,
        "submission_id": package.submission_id,
        "path": str(package.path),
        "ok_to_run": blocking == 0,
        "blocking_count": blocking,
        "warning_count": warning,
        "findings": findings[:100],
        "message": (
            "Clear blocking PII (SSN, cards, bank accounts, DOB, etc.) before pilot run"
            if blocking
            else "No blocking PII detected — safe for shadow underwriting"
        ),
    }
