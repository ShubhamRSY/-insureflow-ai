"""Hazard classification — Chapter 4.

Chapter 4's property-casualty discussion divides hazards into four categories:
physical hazard (from the property itself), moral hazard (from the character of
the applicant), morale hazard (carelessness / indifference), and legal hazard
(litigiousness and the legal environment). COPE and the moral-hazard screen are
already structured in this codebase; this module adds the morale and legal
screens and folds all four into a single hazard profile so the risk analysis
and rating pipeline can consume them together.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.cope import COPERatingEngine, RiskGrade
from insureflow.underwriting.moral_hazard import assess_moral_hazard

# Carelessness / indifference markers — morale hazard.
_MORALE_MARKERS = (
    "poor housekeeping",
    "clutter",
    "deferred maintenance",
    "neglect",
    "careless",
    "indifferent",
    "unsecured property",
    "blocked exits",
    "overloaded circuits",
    "poorly maintained",
    "housekeeping",
    "dilapidated",
    "trash accumulation",
    "weeds",
    "unmaintained",
    "litter",
    "debris",
)

# Litigiousness / legal-environment markers — legal hazard.
_LEGAL_MARKERS = (
    "litigation",
    "lawsuit",
    "sued",
    "attorney",
    "claimant's attorney",
    "tort",
    "punitive damages",
    "judgment against",
    "sue-happy",
    "plaintiff",
    "discovery",
    "subpoena",
)


class HazardCategory(str, Enum):
    PHYSICAL = "physical"
    MORAL = "moral"
    MORALE = "morale"
    LEGAL = "legal"


class HazardSignal(BaseModel):
    category: HazardCategory
    detail: str
    severity: RiskSeverity = RiskSeverity.MODERATE
    source: str = ""


class HazardAssessment(BaseModel):
    """The four-hazard profile of a single risk."""

    category: HazardCategory
    signals: list[HazardSignal] = Field(default_factory=list)
    status: str = "low"  # low | flagged | high | critical
    summary: str = ""


class HazardProfile(BaseModel):
    """Aggregate of the four hazard categories for one submission."""

    applicant_name: str = ""
    physical: Optional[HazardAssessment] = None
    moral: Optional[HazardAssessment] = None
    morale: Optional[HazardAssessment] = None
    legal: Optional[HazardAssessment] = None

    def worst_severity(self) -> str:
        order = ["low", "flagged", "high", "critical"]
        worst = "low"
        for cat in (self.physical, self.moral, self.morale, self.legal):
            if cat is None:
                continue
            if order.index(cat.status) > order.index(worst):
                worst = cat.status
        return worst

    def as_dict(self) -> dict[str, Any]:
        return {
            "applicant_name": self.applicant_name,
            "worst_hazard": self.worst_severity(),
            "categories": {
                cat.category.value: {
                    "status": cat.status,
                    "signals": [s.detail for s in cat.signals],
                    "summary": cat.summary,
                }
                for cat in (self.physical, self.moral, self.morale, self.legal)
                if cat is not None
            },
        }


def _document_text(bundle: SubmissionBundle) -> list[str]:
    texts: list[str] = []
    if bundle.structured:
        if bundle.structured.raw_xml:
            texts.append(bundle.structured.raw_xml)
        if bundle.structured.raw_json:
            texts.append(bundle.structured.raw_json)
    for doc in (bundle.unstructured or []) + (bundle.supplemental or []):
        texts.append(doc.raw_text)
    return texts


def _match_markers(texts: list[str], markers: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for text in texts:
        lowered = text.lower()
        hits.extend(m for m in markers if m in lowered)
    return list(dict.fromkeys(hits))


def _physical_grade(grade: RiskGrade) -> str:
    return {
        RiskGrade.PREFERRED: "low",
        RiskGrade.STANDARD: "low",
        RiskGrade.NON_STANDARD: "flagged",
        RiskGrade.DECLINED: "critical",
    }.get(grade, "low")


def _floor_plan_signals(bundle: SubmissionBundle) -> list[HazardSignal]:
    """Physical-hazard signals from schematic/floor-plan features."""
    signals: list[HazardSignal] = []
    structured = bundle.structured
    if structured is None or structured.floor_plan is None:
        return signals

    fp = structured.floor_plan

    if fp.number_of_exits is not None and fp.number_of_exits < 2:
        signals.append(
            HazardSignal(
                category=HazardCategory.PHYSICAL,
                detail=f"Floor plan shows only {fp.number_of_exits} exit(s) — inadequate means of egress",
                severity=RiskSeverity.HIGH,
                source="floor_plan",
            )
        )
    elif fp.number_of_exits == 2 and (fp.number_of_stories or 1) >= 2:
        signals.append(
            HazardSignal(
                category=HazardCategory.PHYSICAL,
                detail=f"Multi-story occupancy with only {fp.number_of_exits} exits relies on a single stair core",
                severity=RiskSeverity.MODERATE,
                source="floor_plan",
            )
        )

    if fp.fire_alarm == "no" and fp.sprinklered != "yes":
        signals.append(
            HazardSignal(
                category=HazardCategory.PHYSICAL,
                detail="Floor plan shows no fire alarm and no sprinkler protection",
                severity=RiskSeverity.MODERATE,
                source="floor_plan",
            )
        )

    if fp.compartmentalization in ("open", None) and fp.floor_area_sqft is not None and fp.floor_area_sqft >= 25000:
        signals.append(
            HazardSignal(
                category=HazardCategory.PHYSICAL,
                detail=f"Open-plan floor layout across {int(fp.floor_area_sqft):,} sq ft — limited compartmentalization of fire risk",
                severity=RiskSeverity.MODERATE,
                source="floor_plan",
            )
        )

    if fp.fire_compartments is not None and fp.fire_compartments >= 5:
        signals.append(
            HazardSignal(
                category=HazardCategory.PHYSICAL,
                detail=f"Floor plan contains {fp.fire_compartments} fire compartments — compartmentalized risk",
                severity=RiskSeverity.LOW,
                source="floor_plan",
            )
        )

    return signals


def assess_physical_hazard(bundle: SubmissionBundle) -> HazardAssessment:
    engine = COPERatingEngine()
    cope = engine.analyze(bundle)
    signals: list[HazardSignal] = []
    for label, detail, sev in (
        ("construction", cope.construction_detail, RiskSeverity.HIGH),
        ("occupancy", cope.occupancy_detail, RiskSeverity.HIGH),
        ("protection", cope.protection_detail, RiskSeverity.HIGH),
        ("exposure", cope.exposure_detail, RiskSeverity.HIGH),
    ):
        if detail:
            signals.append(HazardSignal(category=HazardCategory.PHYSICAL, detail=detail, severity=sev, source=label))
    signals.extend(_floor_plan_signals(bundle))
    status = _physical_grade(cope.score.risk_grade)
    if signals and status == "low":
        status = "flagged"
    return HazardAssessment(
        category=HazardCategory.PHYSICAL,
        signals=signals,
        status=status,
        summary=f"COPE grade {cope.score.risk_grade.value} (total {cope.score.total_score:.2f}, schedule {cope.score.schedule_mod_pct:+.0f}%)",
    )


def assess_moral_hazard_hazard(bundle: SubmissionBundle) -> HazardAssessment:
    assessment = assess_moral_hazard(bundle)
    signals = [
        HazardSignal(
            category=HazardCategory.MORAL,
            detail=s.detail,
            severity=s.severity,
            source=s.signal_type.value,
        )
        for s in assessment.signals
    ]
    return HazardAssessment(
        category=HazardCategory.MORAL,
        signals=signals,
        status=assessment.status,
        summary=(f"Moral-hazard screen {assessment.status} (score {assessment.moral_hazard_score:.2f})" if signals else "No moral-hazard signals detected"),
    )


def assess_morale_hazard(bundle: SubmissionBundle) -> HazardAssessment:
    hits = _match_markers(_document_text(bundle), _MORALE_MARKERS)
    signals = [
        HazardSignal(
            category=HazardCategory.MORALE,
            detail=f"Morale-hazard marker '{m}' — suggests carelessness or indifference toward loss prevention",
            severity=RiskSeverity.MODERATE,
            source=m,
        )
        for m in hits
    ]
    if len(hits) >= 4:
        status = "high"
    elif hits:
        status = "flagged"
    else:
        status = "low"
    return HazardAssessment(
        category=HazardCategory.MORALE,
        signals=signals,
        status=status,
        summary=(f"{len(hits)} carelessness/indifference marker(s) found" if hits else "No morale-hazard (carelessness/indifference) markers found"),
    )


def assess_legal_hazard(bundle: SubmissionBundle) -> HazardAssessment:
    hits = _match_markers(_document_text(bundle), _LEGAL_MARKERS)
    signals = [
        HazardSignal(
            category=HazardCategory.LEGAL,
            detail=f"Legal-hazard marker '{m}' — litigiousness or adverse legal environment",
            severity=RiskSeverity.HIGH if m in ("litigation", "lawsuit", "punitive damages") else RiskSeverity.MODERATE,
            source=m,
        )
        for m in hits
    ]
    if hits:
        status = "high" if any(s.severity == RiskSeverity.HIGH for s in signals) else "flagged"
    else:
        status = "low"
    return HazardAssessment(
        category=HazardCategory.LEGAL,
        signals=signals,
        status=status,
        summary=(f"{len(hits)} legal-hazard marker(s) found" if hits else "No legal-hazard (litigiousness / legal environment) markers found"),
    )


def assess_hazards(bundle: SubmissionBundle) -> HazardProfile:
    """Run all four hazard categories and return the aggregate profile."""
    structured = bundle.structured
    applicant = (structured.named_insured.legal_name if structured and structured.named_insured else "") or ""
    return HazardProfile(
        applicant_name=applicant,
        physical=assess_physical_hazard(bundle),
        moral=assess_moral_hazard_hazard(bundle),
        morale=assess_morale_hazard(bundle),
        legal=assess_legal_hazard(bundle),
    )
