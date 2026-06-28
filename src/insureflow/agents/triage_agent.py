"""Submission Triage Agent — Scores and prioritizes incoming submissions.

In a real small carrier, 100 applications arrive per day. 25 are duds
(wrong industry, state, size). Only 30 are solid fits. The triage agent
scores each submission and surfaces the best-fit ones first, so the UW
team doesn't waste time on applications they'd never accept.

This matches the real-world bottleneck: teams only review 30-40% of
applications, and sorting them manually costs hours per day.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from insureflow.models.submissions import SubmissionBundle


class SubmissionPriority(str, Enum):
    HOT = "hot"            # Best fit — score >= 80
    WARM = "warm"          # Good fit — score >= 50
    COLD = "cold"          # Marginal — score >= 25
    NO_FIT = "no_fit"      # Don't bother — score < 25


@dataclass
class DocumentChecklist:
    acord_form: bool = False
    loss_run: bool = False
    financials: bool = False
    photos: bool = False
    inspection_report: bool = False
    schedule_of_values: bool = False
    supplemental: bool = False
    signed_application: bool = False

    @property
    def completeness_pct(self) -> float:
        total = 8
        present = sum([
            self.acord_form, self.loss_run, self.financials, self.photos,
            self.inspection_report, self.schedule_of_values,
            self.supplemental, self.signed_application,
        ])
        return present / total

    @property
    def missing(self) -> list[str]:
        items: list[str] = []
        if not self.acord_form:
            items.append("ACORD application form")
        if not self.loss_run:
            items.append("Loss run (5 year claims history)")
        if not self.financials:
            items.append("Financial statements")
        if not self.photos:
            items.append("Property photos")
        if not self.inspection_report:
            items.append("Inspection report")
        if not self.schedule_of_values:
            items.append("Schedule of values")
        if not self.supplemental:
            items.append("Supplemental forms")
        if not self.signed_application:
            items.append("Signed application")
        return items


@dataclass
class TriageResult:
    bundle_id: str
    priority: SubmissionPriority
    score: float  # 0-100
    rank: int = 0  # Position in the queue

    # Fit analysis
    naics_fit: float = 0.0      # 0-100
    geography_fit: float = 0.0  # 0-100
    size_fit: float = 0.0       # 0-100
    coverage_fit: float = 0.0   # 0-100

    # Documents
    document_checklist: DocumentChecklist = field(default_factory=DocumentChecklist)
    missing_documents: list[str] = field(default_factory=list)

    # UW recommendation
    review_by: str = ""  # junior_hourly | senior | cuo
    estimated_review_minutes: int = 0
    referral_reason: str = ""


class TriageAgent:
    """Scores and prioritizes incoming submissions based on carrier appetite.

    The triage agent runs before any expensive processing (no LLM, no
    external database queries) to quickly answer: is this worth looking at?
    """

    PREFERRED_NAICS_PREFIXES = ("44", "45", "53", "54", "56", "62", "72", "81")
    PREFERRED_STATES = ("TX", "OK", "LA", "AR", "FL", "GA", "IL", "CA", "NY")

    def __init__(self) -> None:
        self._queue: list[TriageResult] = []

    def score_submission(self, bundle: SubmissionBundle) -> TriageResult:
        """Score a single submission and return a triage result."""
        naics = ""
        state = ""
        tiv = 0.0
        premium = 0.0
        has_loss_run = False
        has_sov = False
        has_financials = False

        if bundle.structured:
            if bundle.structured.risk_profile:
                naics = bundle.structured.risk_profile.naics_code or ""
            if bundle.structured.locations:
                state = bundle.structured.locations[0].state or ""
                for loc in bundle.structured.locations:
                    tiv += (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
            for cov in bundle.structured.coverages:
                premium += cov.premium
            if bundle.structured.financial:
                has_financials = True
                if bundle.structured.financial.loss_run:
                    has_loss_run = True

        # Check unstructured docs for missing info
        for doc in bundle.unstructured:
            if doc.document_type == "loss_run":
                has_loss_run = True
            elif doc.document_type == "schedule_of_values":
                has_sov = True

        # NAICS fit
        naics_fit = 0.0
        if naics:
            if naics[:2] in self.PREFERRED_NAICS_PREFIXES:
                naics_fit = 100.0
            elif any(naics.startswith(p) for p in (
                "7211", "1133", "2131", "4821", "4911", "9211"
            )):
                naics_fit = 0.0  # Excluded
            else:
                naics_fit = 40.0
        else:
            naics_fit = 30.0  # Unknown — query needed

        # Geography fit
        geography_fit = 0.0
        if state in self.PREFERRED_STATES:
            geography_fit = 100.0 if state in ("TX", "OK") else 70.0
        elif state:
            geography_fit = 20.0  # Non-preferred state
        else:
            geography_fit = 50.0  # Unknown

        # Size fit (based on TIV)
        size_fit = 100.0
        if tiv > 0:
            if tiv < 50_000:
                size_fit = 20.0  # Too small
            elif tiv > 25_000_000:
                size_fit = 30.0  # Too large, facultative needed
            elif tiv > 10_000_000:
                size_fit = 60.0  # Large but possible
        elif premium > 0:
            if premium < 2_500:
                size_fit = 20.0
            elif premium > 250_000:
                size_fit = 30.0
        # else unknown → moderate

        # Coverage fit (do we write this type?)
        coverage_fit = 70.0  # Default — unknown
        if bundle.structured and bundle.structured.coverages:
            coverage_fit = 85.0  # Has coverages

        # Document completeness
        checklist = DocumentChecklist(
            acord_form=bundle.structured is not None,
            loss_run=has_loss_run,
            financials=has_financials,
            schedule_of_values=has_sov,
            signed_application=bool(bundle.structured and bundle.structured.named_insured),
        )

        # Weighted total score
        score = (
            naics_fit * 0.30
            + geography_fit * 0.25
            + size_fit * 0.20
            + coverage_fit * 0.15
            + (checklist.completeness_pct * 100.0) * 0.10
        )
        score = max(0.0, min(100.0, score))

        # Priority
        if score >= 80:
            priority = SubmissionPriority.HOT
        elif score >= 50:
            priority = SubmissionPriority.WARM
        elif score >= 25:
            priority = SubmissionPriority.COLD
        else:
            priority = SubmissionPriority.NO_FIT

        # Assign to correct UW level and estimate effort
        review_by = "triage_desk"
        est_minutes = 30
        if priority == SubmissionPriority.HOT:
            if tiv > 10_000_000 or premium > 100_000:
                review_by = "senior"
                est_minutes = 60
            else:
                review_by = "junior_hourly"
                est_minutes = 20
        elif priority == SubmissionPriority.WARM:
            review_by = "junior_hourly"
            est_minutes = 25
        elif priority in (SubmissionPriority.COLD, SubmissionPriority.NO_FIT):
            review_by = "triage_desk"
            est_minutes = 5

        result = TriageResult(
            bundle_id=bundle.bundle_id,
            priority=priority,
            score=round(score, 1),
            naics_fit=naics_fit,
            geography_fit=geography_fit,
            size_fit=size_fit,
            coverage_fit=coverage_fit,
            document_checklist=checklist,
            missing_documents=checklist.missing,
            review_by=review_by,
            estimated_review_minutes=est_minutes,
        )
        self._queue.append(result)
        return result

    def get_queue(
        self,
        priority_filter: Optional[SubmissionPriority] = None,
        limit: int = 50,
    ) -> list[TriageResult]:
        """Get the sorted submission queue (highest score first)."""
        results = sorted(self._queue, key=lambda r: r.score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1
        if priority_filter:
            results = [r for r in results if r.priority == priority_filter]
        return results[:limit]

    def get_statistics(self) -> dict[str, Any]:
        """Return queue stats like a real triage dashboard."""
        counts = {p.value: 0 for p in SubmissionPriority}
        for r in self._queue:
            counts[r.priority.value] = counts.get(r.priority.value, 0) + 1
        return {
            "total_in_queue": len(self._queue),
            "by_priority": counts,
            "hot_need_review": counts.get("hot", 0),
            "warm_could_proceed": counts.get("warm", 0),
            "cold_minimal_effort": counts.get("cold", 0),
            "no_fit_discard": counts.get("no_fit", 0),
        }


_triage: TriageAgent | None = None


def get_triage_agent() -> TriageAgent:
    global _triage
    if _triage is None:
        _triage = TriageAgent()
    return _triage
