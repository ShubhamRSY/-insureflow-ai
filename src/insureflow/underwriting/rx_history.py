"""Prescription history screen — flags only, not a live Rx database hit.

Auth forms (MIB/Rx authorization) are not a bureau query. This module reads
disclosed medications from the package and applies knockout / refer rules.
Desk+ requires an uploaded Rx report or live vendor; a no-hit simulated feed
is not a clean bill of health.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.billing.plan import current_plan
from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import _blob

_KNOCKOUT = (
    (r"\b(?:chemotherapy|chemo\b|oncolog)", "Active chemotherapy / oncology treatment"),
    (r"\binsulin\b|\bmetformin\b.*insulin", "Insulin-dependent diabetes (refer / table)"),
    (r"\b(?:methadone|suboxone|buprenorphine)\b", "Opioid agonist therapy"),
    (r"\b(?:warfarin|coumadin)\b", "Anticoagulant — cardiac / clotting workup"),
    (r"\b(?:lithium|clozapine)\b", "Serious psychiatric medication"),
    (r"\b(?:interferon|humira|enbrel|remicade)\b", "Immunomodulator — APS likely"),
)

_REFER = (
    (r"\b(?:statin|atorvastatin|lisinopril|amlodipine|metoprolol)\b", "Cardiovascular medication disclosed"),
    (r"\b(?:ssri|zoloft|prozac|lexapro)\b", "Antidepressant disclosed"),
    (r"\b(?:albuterol|advair|symbicort)\b", "Respiratory medication disclosed"),
)


@dataclass
class RxScreenResult:
    medications: list[str] = field(default_factory=list)
    knockout: list[str] = field(default_factory=list)
    referrals: list[str] = field(default_factory=list)
    report_present: bool = False
    auth_present: bool = False
    live_required: bool = False
    findings: list[Finding] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "medications": list(self.medications),
            "knockout": list(self.knockout),
            "referrals": list(self.referrals),
            "rx_report_present": self.report_present,
            "rx_auth_present": self.auth_present,
            "rx_live_required": self.live_required,
        }


def screen_rx(bundle: SubmissionBundle) -> RxScreenResult:
    blob = _blob(bundle)
    plan = current_plan()
    meds = re.findall(r"(?:medication|rx|prescription)s?\s*[:=]\s*([A-Za-z0-9 ,/+-]{3,80})", blob, re.I)
    flat = " ".join(meds) + " " + blob
    medications = [m.strip() for m in meds if m.strip()][:20]

    knockout: list[str] = []
    referrals: list[str] = []
    findings: list[Finding] = []
    for pat, reason in _KNOCKOUT:
        if re.search(pat, flat, re.I):
            knockout.append(reason)
            findings.append(
                Finding(
                    title=f"Rx knockout: {reason}",
                    description="Disclosed medication conflicts with preferred/standard issue without APS.",
                    severity=RiskSeverity.CRITICAL,
                    category="rx_history",
                )
            )
    for pat, reason in _REFER:
        if re.search(pat, flat, re.I) and reason not in knockout:
            referrals.append(reason)
            findings.append(
                Finding(
                    title=f"Rx referral: {reason}",
                    description="Order APS / confirm control before preferred class.",
                    severity=RiskSeverity.HIGH,
                    category="rx_history",
                )
            )

    report_present = bool(re.search(r"rx\s*(?:report|history|database\s+hit)|milliman|scriptcheck|interrogatories", blob, re.I))
    auth_present = bool(re.search(r"mib\s*/?\s*rx|rx\s+authorization|prescription\s+history\s+auth", blob, re.I))
    live_required = bool(plan.require_live_oracles)

    if live_required and not report_present:
        findings.append(
            Finding(
                title="Live Rx history required",
                description="Desk+ does not treat MIB/Rx authorization as a bureau hit. Upload an Rx report or connect a live vendor.",
                severity=RiskSeverity.CRITICAL,
                category="rx_history",
            )
        )
    elif not report_present and not medications:
        findings.append(
            Finding(
                title="Rx history not run",
                description="No prescription report on file — authorization alone is not a query.",
                severity=RiskSeverity.HIGH,
                category="rx_history",
            )
        )
    elif not medications:
        findings.append(
            Finding(
                title="Rx: no medications disclosed",
                description="No Rx report and no medications listed on the application.",
                severity=RiskSeverity.LOW if report_present else RiskSeverity.MODERATE,
                category="rx_history",
            )
        )

    return RxScreenResult(
        medications=medications,
        knockout=knockout,
        referrals=referrals,
        report_present=report_present,
        auth_present=auth_present,
        live_required=live_required,
        findings=findings,
    )
