"""Life automatic / facultative reinsurance — retention vs jumbo / facultative."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.personal.manuals import life_manual
from insureflow.underwriting.personal_lines import extract_life_factors


@dataclass
class LifeReinsuranceResult:
    face_amount: float
    retention: float
    automatic_limit: float
    cession: float
    facultative_required: bool
    jumbo: bool
    decision_hint: UWDecision = UWDecision.ACCEPT
    findings: list[Finding] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "face_amount": self.face_amount,
            "retention_limit": self.retention,
            "automatic_reinsurance_limit": self.automatic_limit,
            "cession_amount": self.cession,
            "facultative_required": self.facultative_required,
            "jumbo": self.jumbo,
            "applicable": True,
        }


def evaluate_life_reinsurance(bundle: SubmissionBundle, *, face_amount: float | None = None) -> LifeReinsuranceResult:
    manual = life_manual()
    factors = extract_life_factors(bundle)
    face = float(face_amount if face_amount is not None else factors.face_amount or 0)
    retention = float(manual.get("retention_limit") or 1_000_000)
    automatic = float(manual.get("automatic_reinsurance_limit") or manual.get("jumbo_threshold") or 5_000_000)
    facultative_at = float(manual.get("facultative_threshold") or 10_000_000)

    jumbo = face >= automatic
    facultative = face >= facultative_at
    cession = max(0.0, face - retention) if face > retention else 0.0

    findings: list[Finding] = []
    reasons: list[str] = []
    hint = UWDecision.ACCEPT

    if face <= 0:
        reasons.append("Face amount missing — cannot size life reinsurance")
        findings.append(
            Finding(
                title="Life reinsurance: face unknown",
                description="Retention / cession not calculated without a face amount.",
                severity=RiskSeverity.HIGH,
                category="life_reinsurance",
                source_document="life reinsurance retention/treaty table",
                extraction_method="rule_engine",
            )
        )
        hint = UWDecision.REFER
    elif facultative:
        hint = UWDecision.REFER
        reasons.append(f"Facultative required — face ${face:,.0f} exceeds ${facultative_at:,.0f}")
        findings.append(
            Finding(
                title="Facultative life reinsurance required",
                description=(f"Face ${face:,.0f} is above automatic treaty (${automatic:,.0f}). Retain ${retention:,.0f}; cede ${cession:,.0f} facultatively. Do not bind until placed."),
                severity=RiskSeverity.CRITICAL,
                category="life_reinsurance",
                source_document="life reinsurance retention/treaty table",
                extraction_method="rule_engine",
            )
        )
    elif jumbo:
        hint = UWDecision.REFER
        reasons.append(f"Jumbo — automatic cession ${cession:,.0f}")
        findings.append(
            Finding(
                title="Jumbo life — automatic reinsurance",
                description=f"Retain ${retention:,.0f}; automatic YRT/coinsurance cession ${cession:,.0f}. Confirm treaty capacity before issue.",
                severity=RiskSeverity.HIGH,
                category="life_reinsurance",
                source_document="life reinsurance retention/treaty table",
                extraction_method="rule_engine",
            )
        )
    elif cession > 0:
        findings.append(
            Finding(
                title="Life automatic reinsurance cession",
                description=f"Retain ${retention:,.0f}; cede ${cession:,.0f} under automatic treaty.",
                severity=RiskSeverity.LOW,
                category="life_reinsurance",
                source_document="life reinsurance retention/treaty table",
                extraction_method="rule_engine",
            )
        )
    else:
        findings.append(
            Finding(
                title="Within life retention",
                description=f"Face ${face:,.0f} is within retention ${retention:,.0f} — no cession.",
                severity=RiskSeverity.LOW,
                category="life_reinsurance",
                source_document="life reinsurance retention/treaty table",
                extraction_method="rule_engine",
            )
        )

    return LifeReinsuranceResult(
        face_amount=face,
        retention=retention,
        automatic_limit=automatic,
        cession=round(cession, 2),
        facultative_required=facultative,
        jumbo=jumbo,
        decision_hint=hint,
        findings=findings,
        reasons=reasons,
    )
