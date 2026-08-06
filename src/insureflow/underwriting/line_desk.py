"""Line underwriter desk — coverage determination and producer/policyholder service.

Complements the submission pipeline (risk selection) with the classic line UW
service activities: matching coverage to exposures and processing routine service.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

LINE_SERVICE_NS = "line_uw_service"


class CoverageAction(str, Enum):
    BROADEN = "broaden"
    NARROW = "narrow"
    VERIFY = "verify"
    MANUSCRIPT = "manuscript"


class ServiceRequestType(str, Enum):
    QUOTE = "quote"
    ENDORSEMENT = "endorsement"
    CERTIFICATE = "certificate"
    CANCELLATION = "cancellation"
    RENEWAL = "renewal"
    CORRESPONDENCE = "correspondence"
    POLICYHOLDER_INQUIRY = "policyholder_inquiry"


class ServiceStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class CoverageRecommendation:
    action: CoverageAction
    title: str
    rationale: str
    suggested_form: str = ""
    suggested_endorsements: list[str] = field(default_factory=list)
    exposure_gap: str = ""
    priority: str = "medium"  # low | medium | high


@dataclass
class CoverageAssistResult:
    applicant: str
    occupancy: str
    recommendations: list[CoverageRecommendation]
    summary: str
    generated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "applicant": self.applicant,
            "occupancy": self.occupancy,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "recommendations": [
                {
                    "action": r.action.value,
                    "title": r.title,
                    "rationale": r.rationale,
                    "suggested_form": r.suggested_form,
                    "suggested_endorsements": r.suggested_endorsements,
                    "exposure_gap": r.exposure_gap,
                    "priority": r.priority,
                }
                for r in self.recommendations
            ],
        }


@dataclass
class ServiceTicket:
    ticket_id: str
    request_type: ServiceRequestType
    status: ServiceStatus
    subject: str
    detail: str
    requester: str  # producer | policyholder | internal
    requester_name: str = ""
    policy_number: str = ""
    submission_id: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    resolution_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["request_type"] = self.request_type.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceTicket:
        return cls(
            ticket_id=data["ticket_id"],
            request_type=ServiceRequestType(data["request_type"]),
            status=ServiceStatus(data.get("status", ServiceStatus.OPEN.value)),
            subject=data.get("subject", ""),
            detail=data.get("detail", ""),
            requester=data.get("requester", "producer"),
            requester_name=data.get("requester_name", ""),
            policy_number=data.get("policy_number", ""),
            submission_id=data.get("submission_id", ""),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at", datetime.now(tz=timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(tz=timezone.utc).isoformat()),
            resolution_notes=data.get("resolution_notes", ""),
        )


# Heuristic coverage gaps keyed by occupancy / exposure keywords (textbook inland marine example).
_EXPOSURE_RULES: list[dict[str, Any]] = [
    {
        "keywords": ("manufactur", "warehouse", "distributor", "wholesaler"),
        "exposure": "property_in_transit",
        "action": CoverageAction.BROADEN,
        "title": "Add inland marine for property in transit",
        "rationale": ("Operations suggest goods moving between locations. Standard property forms often leave transit inadequately covered — offer an inland marine policy."),
        "form": "Inland Marine — Motor Truck Cargo / Transit",
        "endorsements": ["Cargo named perils or all-risk transit endorsement"],
        "priority": "high",
    },
    {
        "keywords": ("contractor", "construction", "builder"),
        "exposure": "tools_equipment",
        "action": CoverageAction.BROADEN,
        "title": "Contractors equipment / tools floater",
        "rationale": "Mobile equipment and tools at job sites typically need inland marine floaters.",
        "form": "Contractors Equipment Floater",
        "endorsements": ["Rented / borrowed equipment", "Employee tools"],
        "priority": "high",
    },
    {
        "keywords": ("restaurant", "food service", "bar", "tavern"),
        "exposure": "liquor_liability",
        "action": CoverageAction.BROADEN,
        "title": "Liquor liability / host liquor review",
        "rationale": "Food-service operations may need liquor liability beyond CGL host liquor.",
        "form": "Liquor Liability",
        "endorsements": ["Assault & battery exclusion review"],
        "priority": "medium",
    },
    {
        "keywords": ("cyber", "saas", "software", "data center", "fintech"),
        "exposure": "cyber",
        "action": CoverageAction.BROADEN,
        "title": "Standalone cyber coverage",
        "rationale": "Tech-heavy operations often need cyber beyond property/GL packages.",
        "form": "Cyber Liability",
        "endorsements": ["Breach response", "Business interruption — cyber"],
        "priority": "high",
    },
    {
        "keywords": ("coastal", "flood", "hurricane", "cat"),
        "exposure": "flood_wind",
        "action": CoverageAction.NARROW,
        "title": "Higher wind/hail deductible or flood exclusion",
        "rationale": ("Rather than decline, offer limited terms: higher deductibles or fewer causes of loss so the producer can place reduced coverage the applicant may accept."),
        "form": "Property — limited causes of loss",
        "endorsements": ["Percentage wind/hail deductible", "Flood exclusion"],
        "priority": "medium",
    },
]


def assist_coverage(
    *,
    applicant: str = "",
    occupancy: str = "",
    operations_description: str = "",
    requested_coverages: Optional[list[str]] = None,
    complex_submission: bool = False,
) -> CoverageAssistResult:
    """Recommend broaden / narrow / verify / manuscript actions for a submission."""
    blob = f"{occupancy} {operations_description}".lower()
    recs: list[CoverageRecommendation] = []
    seen: set[str] = set()

    for rule in _EXPOSURE_RULES:
        if any(k in blob for k in rule["keywords"]):
            key = rule["exposure"]
            if key in seen:
                continue
            seen.add(key)
            recs.append(
                CoverageRecommendation(
                    action=rule["action"],
                    title=rule["title"],
                    rationale=rule["rationale"],
                    suggested_form=rule["form"],
                    suggested_endorsements=list(rule["endorsements"]),
                    exposure_gap=key,
                    priority=rule["priority"],
                )
            )

    requested = [c.lower() for c in (requested_coverages or [])]
    if requested:
        recs.append(
            CoverageRecommendation(
                action=CoverageAction.VERIFY,
                title="Verify forms and endorsements on routine package",
                rationale=(f"For simple or routine submissions, confirm the policy issues with the appropriate forms for: {', '.join(requested_coverages or [])}."),
                suggested_form="Package / BOP / monoline as quoted",
                suggested_endorsements=[],
                priority="low",
            )
        )

    if complex_submission or len(recs) >= 3:
        recs.append(
            CoverageRecommendation(
                action=CoverageAction.MANUSCRIPT,
                title="Consider manuscript endorsement language",
                rationale=("Complex or unique submissions may need manuscript policies or endorsements drafted to the characteristics of this account."),
                suggested_form="Manuscript endorsement",
                priority="medium",
            )
        )

    if not recs:
        recs.append(
            CoverageRecommendation(
                action=CoverageAction.VERIFY,
                title="Standard forms appear adequate",
                rationale=("No obvious uncovered exposures from the occupancy narrative. Verify classification, limits, and deductibles against the underwriting guide."),
                priority="low",
            )
        )

    broaden = sum(1 for r in recs if r.action == CoverageAction.BROADEN)
    narrow = sum(1 for r in recs if r.action == CoverageAction.NARROW)
    summary = f"{len(recs)} coverage action(s) for {applicant or 'applicant'}: {broaden} broaden, {narrow} narrow, {len(recs) - broaden - narrow} verify/manuscript."
    return CoverageAssistResult(
        applicant=applicant or "Unknown applicant",
        occupancy=occupancy or "unspecified",
        recommendations=recs,
        summary=summary,
    )


class LineServiceDesk:
    """Producer and policyholder service ticket store for line underwriters."""

    def __init__(self) -> None:
        self._tickets: dict[str, list[ServiceTicket]] = {}
        self._loaded: set[str] = set()

    def _store(self) -> Any:
        from insureflow.storage.job_store import get_job_store

        return get_job_store()

    def _ensure(self, org_id: str) -> None:
        if org_id in self._loaded:
            return
        raw = self._store().get(LINE_SERVICE_NS, "tickets", org_id=org_id)
        tickets: list[ServiceTicket] = []
        if raw:
            for row in raw.get("tickets", []):
                try:
                    tickets.append(ServiceTicket.from_dict(row))
                except (KeyError, ValueError):
                    continue
        self._tickets[org_id] = tickets
        self._loaded.add(org_id)

    def _persist(self, org_id: str) -> None:
        data = {"tickets": [t.to_dict() for t in self._tickets.get(org_id, [])]}
        self._store().set(LINE_SERVICE_NS, "tickets", data, org_id=org_id)

    def list_tickets(
        self,
        org_id: str = "default",
        *,
        status: Optional[str] = None,
        requester: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        self._ensure(org_id)
        rows = self._tickets.get(org_id, [])
        out = []
        for t in rows:
            if status and t.status.value != status:
                continue
            if requester and t.requester != requester:
                continue
            out.append(t.to_dict())
        return sorted(out, key=lambda x: x.get("updated_at", ""), reverse=True)

    def create_ticket(
        self,
        *,
        request_type: str,
        subject: str,
        detail: str = "",
        requester: str = "producer",
        requester_name: str = "",
        policy_number: str = "",
        submission_id: str = "",
        created_by: str = "",
        org_id: str = "default",
    ) -> dict[str, Any]:
        self._ensure(org_id)
        try:
            rtype = ServiceRequestType(request_type.lower())
        except ValueError:
            valid = ", ".join(t.value for t in ServiceRequestType)
            raise ValueError(f"Invalid request_type. Valid: {valid}") from None
        ticket = ServiceTicket(
            ticket_id=f"svc-{uuid.uuid4().hex[:10]}",
            request_type=rtype,
            status=ServiceStatus.OPEN,
            subject=subject.strip() or "Service request",
            detail=detail.strip(),
            requester=requester,
            requester_name=requester_name,
            policy_number=policy_number,
            submission_id=submission_id,
            created_by=created_by,
        )
        self._tickets.setdefault(org_id, []).append(ticket)
        self._persist(org_id)
        return ticket.to_dict()

    def update_ticket(
        self,
        ticket_id: str,
        *,
        status: Optional[str] = None,
        resolution_notes: Optional[str] = None,
        org_id: str = "default",
    ) -> dict[str, Any]:
        self._ensure(org_id)
        for t in self._tickets.get(org_id, []):
            if t.ticket_id != ticket_id:
                continue
            if status:
                try:
                    t.status = ServiceStatus(status.lower())
                except ValueError:
                    valid = ", ".join(s.value for s in ServiceStatus)
                    raise ValueError(f"Invalid status. Valid: {valid}") from None
            if resolution_notes is not None:
                t.resolution_notes = resolution_notes
            t.updated_at = datetime.now(tz=timezone.utc).isoformat()
            self._persist(org_id)
            return t.to_dict()
        raise KeyError(ticket_id)


_line_desk: Optional[LineServiceDesk] = None


def get_line_service_desk() -> LineServiceDesk:
    global _line_desk
    if _line_desk is None:
        _line_desk = LineServiceDesk()
    return _line_desk


def reset_line_service_desk() -> None:
    global _line_desk
    _line_desk = None
