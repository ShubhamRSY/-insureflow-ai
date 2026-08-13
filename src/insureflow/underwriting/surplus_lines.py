"""Admitted vs surplus-lines (E&S) classification and stamping gates.

Does not file a stamping office return. It flags when a risk is non-admitted
and what documents (diligent search, SL broker license, SL tax) must be on
file before bind.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine
from insureflow.underwriting.personal_lines import _blob

# Lines that are frequently non-admitted / E&S when the admitted market declines.
_ES_PRONE_LINES = frozenset(
    {
        InsuranceLine.CYBER.value,
        InsuranceLine.DIRECTORS_AND_OFFICERS.value,
        InsuranceLine.ERRORS_AND_OMISSIONS.value,
        "pollution",
        "liquor_liability",
        "kidnap_ransom",
        "aviation",
        "political_risk",
        "product_recall",
        "media_liability",
        "event_insurance",
    }
)

# Representative surplus-lines tax rates (state SL tax, not stamping fee).
_SL_TAX: dict[str, float] = {
    "CA": 0.03,
    "NY": 0.036,
    "TX": 0.0485,
    "FL": 0.05,
    "IL": 0.035,
    "NJ": 0.05,
}


@dataclass
class SurplusLinesResult:
    admitted: bool
    status: str  # admitted | surplus_lines | unknown
    reason: str = ""
    sl_tax_rate: float = 0.0
    missing_documents: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    can_bind: bool = True

    def to_metadata(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "market_status": self.status,
            "reason": self.reason,
            "sl_tax_rate": self.sl_tax_rate,
            "missing_stamping_docs": list(self.missing_documents),
            "can_bind": self.can_bind,
        }


def classify_surplus_lines(
    bundle: SubmissionBundle,
    *,
    line: InsuranceLine | str = "",
    state: str = "",
    product_id: str = "",
) -> SurplusLinesResult:
    blob = _blob(bundle)
    line_key = line.value if isinstance(line, InsuranceLine) else str(line or "").strip().lower()
    product_id = (product_id or "").strip().lower()
    st = (state or "").strip().upper()[:2]

    explicit_es = bool(re.search(r"\b(?:e\s*&\s*s|surplus\s*lines|non-?admitted|excess\s*&\s*surplus)\b", blob, re.I))
    explicit_admitted = bool(re.search(r"\badmitted\s+market\b|\badmitted\s+carrier\b", blob, re.I))
    declined_admitted = bool(re.search(r"admitted\s+(?:market\s+)?(?:declin|refus)|three\s+declinations|diligent\s+search", blob, re.I))

    prone = line_key in _ES_PRONE_LINES or product_id in _ES_PRONE_LINES
    if explicit_admitted and not explicit_es:
        status = "admitted"
        reason = "Package indicates admitted placement"
    elif explicit_es or declined_admitted or (prone and declined_admitted):
        status = "surplus_lines"
        reason = "Non-admitted / surplus-lines placement indicated"
    elif prone:
        status = "unknown"
        reason = "Line is frequently E&S — confirm admitted vs surplus-lines before bind"
    else:
        status = "admitted"
        reason = "Treated as admitted unless the package says otherwise"

    missing: list[str] = []
    findings: list[Finding] = []
    can_bind = True
    sl_tax = _SL_TAX.get(st, 0.036) if status == "surplus_lines" else 0.0

    if status == "surplus_lines":
        if not re.search(r"diligent\s+search|affidavit\s+of\s+due\s+diligence", blob, re.I):
            missing.append("Diligent search / due-diligence affidavit")
        if not re.search(r"surplus\s*lines?\s*(?:broker|license)|sl\s*license", blob, re.I):
            missing.append("Surplus lines broker license")
        if st and not re.search(r"stamp(?:ing)?\s*(?:office|fee)|sl\s*tax", blob, re.I):
            missing.append(f"{st} stamping office / surplus-lines tax disclosure")
        if missing:
            can_bind = False
            findings.append(
                Finding(
                    title="E&S / stamping documents missing",
                    description="Non-admitted placement requires: " + "; ".join(missing),
                    severity=RiskSeverity.CRITICAL,
                    category="surplus_lines",
                )
            )
        else:
            findings.append(
                Finding(
                    title="Surplus lines placement",
                    description=f"SL tax approx. {sl_tax:.2%} of premium — confirm stamping office filing at bind.",
                    severity=RiskSeverity.MODERATE,
                    category="surplus_lines",
                )
            )
    elif status == "unknown":
        findings.append(
            Finding(
                title="Admitted vs E&S not confirmed",
                description=reason,
                severity=RiskSeverity.HIGH,
                category="surplus_lines",
            )
        )

    return SurplusLinesResult(
        admitted=status == "admitted",
        status=status,
        reason=reason,
        sl_tax_rate=sl_tax,
        missing_documents=missing,
        findings=findings,
        can_bind=can_bind,
    )
