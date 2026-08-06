"""Staff underwriter desk — home-office policy, research, guides, audits, training.

Implements the classical staff UW task list: market research, coverage development,
experience evaluation, rating-plan review, underwriting policy/guides, audits, and education.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

STAFF_NS = "staff_uw"


class GuideStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AuditFindingSeverity(str, Enum):
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class MarketResearchNote:
    note_id: str
    title: str
    topic: str  # target_market | state_expansion | product_mix | premium_volume | other
    summary: str
    recommendation: str = ""
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoverageDevelopmentItem:
    item_id: str
    title: str
    change_type: str  # form_mod | endorsement | regulatory | association
    description: str
    status: str = "proposed"  # proposed | in_review | approved | filed
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RatingPlanReview:
    review_id: str
    line_of_business: str
    advisory_org: str  # ISO | AAIS | NCCI | independent
    summary: str
    loss_cost_change_pct: float = 0.0
    expense_load_pct: float = 0.0
    profit_load_pct: float = 0.0
    action: str = "monitor"  # monitor | revise | file
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UnderwritingGuideEntry:
    guide_id: str
    title: str
    line_of_business: str
    body: str
    status: GuideStatus = GuideStatus.DRAFT
    version: str = "1.0"
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnderwritingGuideEntry:
        return cls(
            guide_id=data["guide_id"],
            title=data.get("title", ""),
            line_of_business=data.get("line_of_business", ""),
            body=data.get("body", ""),
            status=GuideStatus(data.get("status", GuideStatus.DRAFT.value)),
            version=data.get("version", "1.0"),
            author=data.get("author", ""),
            created_at=data.get("created_at", datetime.now(tz=timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(tz=timezone.utc).isoformat()),
        )


@dataclass
class UnderwritingAuditFinding:
    finding_id: str
    severity: AuditFindingSeverity
    category: str  # documentation | classification | rating | selection | procedure
    detail: str
    file_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class UnderwritingAudit:
    audit_id: str
    office: str
    auditor: str
    scope: str
    findings: list[UnderwritingAuditFinding] = field(default_factory=list)
    files_reviewed: int = 0
    compliant_pct: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "office": self.office,
            "auditor": self.auditor,
            "scope": self.scope,
            "files_reviewed": self.files_reviewed,
            "compliant_pct": self.compliant_pct,
            "created_at": self.created_at,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class TrainingModule:
    module_id: str
    title: str
    topic: str
    audience: str  # line_uw | producers | all
    outline: str
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_experience(
    *,
    line_of_business: str = "commercial_property",
    class_of_business: str = "",
    territory: str = "",
    earned_premium: float = 0.0,
    incurred_losses: float = 0.0,
    industry_loss_ratio: float = 0.65,
) -> dict[str, Any]:
    """Staff UW experience evaluation — compare book vs industry by slice."""
    loss_ratio = (incurred_losses / earned_premium) if earned_premium > 0 else 0.0
    delta = loss_ratio - industry_loss_ratio
    if delta > 0.10:
        strategy = "tighten"
        narrative = "Book loss ratio is materially worse than industry. Tighten selection, review class/territory appetite, and communicate via underwriting bulletin."
    elif delta < -0.08:
        strategy = "grow"
        narrative = "Book outperforms industry on this slice. Consider controlled growth within guide — update product-mix goals if capacity allows."
    else:
        strategy = "maintain"
        narrative = "Experience is in line with industry. Maintain current marketing and underwriting strategy; monitor quarterly."
    return {
        "line_of_business": line_of_business,
        "class_of_business": class_of_business,
        "territory": territory,
        "earned_premium": earned_premium,
        "incurred_losses": incurred_losses,
        "loss_ratio": round(loss_ratio, 4),
        "industry_loss_ratio": industry_loss_ratio,
        "delta_vs_industry": round(delta, 4),
        "strategy": strategy,
        "narrative": narrative,
        "evaluated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


class StaffUnderwritingDesk:
    """Home-office staff UW workspace with durable org-scoped stores."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def _store(self) -> Any:
        from insureflow.storage.job_store import get_job_store

        return get_job_store()

    def _blank(self) -> dict[str, Any]:
        return {
            "market_research": [],
            "coverage_development": [],
            "rating_reviews": [],
            "guides": [],
            "audits": [],
            "training": [],
            "policy_statements": [],
        }

    def _load(self, org_id: str) -> dict[str, Any]:
        if org_id in self._cache:
            return self._cache[org_id]
        raw = self._store().get(STAFF_NS, "desk", org_id=org_id) or {}
        data = self._blank()
        for key in data:
            data[key] = list(raw.get(key, []))
        if not any(data.values()):
            data = self._seed()
            self._store().set(STAFF_NS, "desk", data, org_id=org_id)
        self._cache[org_id] = data
        return data

    def _persist(self, org_id: str) -> None:
        self._store().set(STAFF_NS, "desk", self._load(org_id), org_id=org_id)

    def _seed(self) -> dict[str, Any]:
        now = datetime.now(tz=timezone.utc).isoformat()
        return {
            "market_research": [
                {
                    "note_id": "mkt-seed-1",
                    "title": "Optimal product mix — GL vs WC",
                    "topic": "product_mix",
                    "summary": ("Evaluate premium mix: general liability vs workers compensation as capacity and loss trends shift."),
                    "recommendation": "Hold GL growth; selective WC expansion in preferred classes.",
                    "author": "staff",
                    "created_at": now,
                }
            ],
            "coverage_development": [
                {
                    "item_id": "cov-seed-1",
                    "title": "Cyber endorsement refresh",
                    "change_type": "endorsement",
                    "description": "Update preprinted cyber endorsements for state privacy statute changes.",
                    "status": "proposed",
                    "author": "staff",
                    "created_at": now,
                }
            ],
            "rating_reviews": [
                {
                    "review_id": "rate-seed-1",
                    "line_of_business": "commercial_property",
                    "advisory_org": "ISO",
                    "summary": "Review ISO loss costs + company expense/profit loads for Q next filing.",
                    "loss_cost_change_pct": 3.5,
                    "expense_load_pct": 28.0,
                    "profit_load_pct": 5.0,
                    "action": "revise",
                    "author": "staff",
                    "created_at": now,
                }
            ],
            "guides": [
                UnderwritingGuideEntry(
                    guide_id="guide-seed-1",
                    title="Commercial Property Selection Guide",
                    line_of_business="commercial_property",
                    body=(
                        "Preferred: masonry noncombustible, sprinklered, PC 1-4.\n"
                        "Refer: coastal wind Tier 1, vacant >90 days, restaurants with fryers lacking suppression.\n"
                        "Decline: unreinforced masonry in seismic zones without retrofit."
                    ),
                    status=GuideStatus.PUBLISHED,
                    version="2026.1",
                    author="staff",
                ).to_dict()
            ],
            "audits": [],
            "training": [
                {
                    "module_id": "train-seed-1",
                    "title": "COPE fundamentals for line underwriters",
                    "topic": "technical_insurance",
                    "audience": "line_uw",
                    "outline": "Construction classes · Occupancy hazards · Protection · Exposure · Documentation standards",
                    "author": "staff",
                    "created_at": now,
                }
            ],
            "policy_statements": [
                {
                    "policy_id": "pol-seed-1",
                    "title": "Large / unusual account referral",
                    "body": ("Accounts above senior authority or outside guide classes require staff underwriter or top management review for fit with overall UW goals."),
                    "author": "staff",
                    "created_at": now,
                }
            ],
        }

    def overview(self, org_id: str = "default") -> dict[str, Any]:
        data = self._load(org_id)
        return {
            "counts": {k: len(v) for k, v in data.items()},
            "tasks": [
                "Researching the market",
                "Researching and developing coverages",
                "Evaluating underwriting experience",
                "Reviewing and revising rating plans",
                "Formulating underwriting policy",
                "Developing underwriting guides",
                "Conducting underwriting audits",
                "Assisting with education and training",
            ],
            "recent_guides": data["guides"][-5:],
            "recent_research": data["market_research"][-5:],
            "recent_audits": data["audits"][-5:],
        }

    def list_section(self, section: str, org_id: str = "default") -> list[dict[str, Any]]:
        data = self._load(org_id)
        if section not in data:
            raise KeyError(section)
        return list(data[section])

    def add_market_research(
        self,
        *,
        title: str,
        topic: str,
        summary: str,
        recommendation: str = "",
        author: str = "",
        org_id: str = "default",
    ) -> dict[str, Any]:
        data = self._load(org_id)
        note = MarketResearchNote(
            note_id=f"mkt-{uuid.uuid4().hex[:8]}",
            title=title.strip(),
            topic=topic.strip() or "other",
            summary=summary.strip(),
            recommendation=recommendation.strip(),
            author=author,
        ).to_dict()
        data["market_research"].append(note)
        self._persist(org_id)
        return note

    def add_coverage_development(
        self,
        *,
        title: str,
        change_type: str,
        description: str,
        author: str = "",
        org_id: str = "default",
    ) -> dict[str, Any]:
        data = self._load(org_id)
        item = CoverageDevelopmentItem(
            item_id=f"cov-{uuid.uuid4().hex[:8]}",
            title=title.strip(),
            change_type=change_type.strip() or "form_mod",
            description=description.strip(),
            author=author,
        ).to_dict()
        data["coverage_development"].append(item)
        self._persist(org_id)
        return item

    def add_rating_review(
        self,
        *,
        line_of_business: str,
        advisory_org: str,
        summary: str,
        loss_cost_change_pct: float = 0.0,
        expense_load_pct: float = 0.0,
        profit_load_pct: float = 0.0,
        action: str = "monitor",
        author: str = "",
        org_id: str = "default",
    ) -> dict[str, Any]:
        data = self._load(org_id)
        review = RatingPlanReview(
            review_id=f"rate-{uuid.uuid4().hex[:8]}",
            line_of_business=line_of_business,
            advisory_org=advisory_org or "independent",
            summary=summary,
            loss_cost_change_pct=loss_cost_change_pct,
            expense_load_pct=expense_load_pct,
            profit_load_pct=profit_load_pct,
            action=action,
            author=author,
        ).to_dict()
        data["rating_reviews"].append(review)
        self._persist(org_id)
        return review

    def upsert_guide(
        self,
        *,
        title: str,
        line_of_business: str,
        body: str,
        status: str = "draft",
        version: str = "1.0",
        author: str = "",
        guide_id: Optional[str] = None,
        org_id: str = "default",
    ) -> dict[str, Any]:
        data = self._load(org_id)
        try:
            gstatus = GuideStatus(status.lower())
        except ValueError:
            gstatus = GuideStatus.DRAFT
        now = datetime.now(tz=timezone.utc).isoformat()
        if guide_id:
            for i, g in enumerate(data["guides"]):
                if g.get("guide_id") == guide_id:
                    merged: dict[str, Any] = {
                        **g,
                        "title": title,
                        "line_of_business": line_of_business,
                        "body": body,
                        "status": gstatus.value,
                        "version": version,
                        "author": author or g.get("author", ""),
                        "updated_at": now,
                    }
                    entry = UnderwritingGuideEntry.from_dict(merged)
                    updated = entry.to_dict()
                    data["guides"][i] = updated
                    self._persist(org_id)
                    return updated
        entry = UnderwritingGuideEntry(
            guide_id=guide_id or f"guide-{uuid.uuid4().hex[:8]}",
            title=title,
            line_of_business=line_of_business,
            body=body,
            status=gstatus,
            version=version,
            author=author,
        )
        created = entry.to_dict()
        data["guides"].append(created)
        self._persist(org_id)
        return created

    def add_policy_statement(
        self,
        *,
        title: str,
        body: str,
        author: str = "",
        org_id: str = "default",
    ) -> dict[str, Any]:
        data = self._load(org_id)
        row = {
            "policy_id": f"pol-{uuid.uuid4().hex[:8]}",
            "title": title.strip(),
            "body": body.strip(),
            "author": author,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        data["policy_statements"].append(row)
        self._persist(org_id)
        return row

    def conduct_audit(
        self,
        *,
        office: str,
        auditor: str,
        scope: str,
        files_reviewed: int = 0,
        findings: Optional[list[dict[str, Any]]] = None,
        org_id: str = "default",
    ) -> dict[str, Any]:
        data = self._load(org_id)
        parsed: list[UnderwritingAuditFinding] = []
        for f in findings or []:
            try:
                sev = AuditFindingSeverity(str(f.get("severity", "info")).lower())
            except ValueError:
                sev = AuditFindingSeverity.INFO
            parsed.append(
                UnderwritingAuditFinding(
                    finding_id=f.get("finding_id") or f"f-{uuid.uuid4().hex[:6]}",
                    severity=sev,
                    category=str(f.get("category", "procedure")),
                    detail=str(f.get("detail", "")),
                    file_ref=str(f.get("file_ref", "")),
                )
            )
        majors = sum(1 for f in parsed if f.severity in (AuditFindingSeverity.MAJOR, AuditFindingSeverity.CRITICAL))
        compliant = 100.0
        if files_reviewed > 0:
            compliant = max(0.0, round(100.0 * (1.0 - majors / max(files_reviewed, 1)), 1))
        audit = UnderwritingAudit(
            audit_id=f"audit-{uuid.uuid4().hex[:8]}",
            office=office.strip() or "branch",
            auditor=auditor,
            scope=scope.strip() or "File documentation, classification, rating, selection vs guide",
            findings=parsed,
            files_reviewed=files_reviewed,
            compliant_pct=compliant,
        )
        data["audits"].append(audit.to_dict())
        self._persist(org_id)
        return audit.to_dict()

    def add_training(
        self,
        *,
        title: str,
        topic: str,
        audience: str,
        outline: str,
        author: str = "",
        org_id: str = "default",
    ) -> dict[str, Any]:
        data = self._load(org_id)
        mod = TrainingModule(
            module_id=f"train-{uuid.uuid4().hex[:8]}",
            title=title.strip(),
            topic=topic.strip() or "technical_insurance",
            audience=audience.strip() or "line_uw",
            outline=outline.strip(),
            author=author,
        ).to_dict()
        data["training"].append(mod)
        self._persist(org_id)
        return mod


_staff_desk: Optional[StaffUnderwritingDesk] = None


def get_staff_desk() -> StaffUnderwritingDesk:
    global _staff_desk
    if _staff_desk is None:
        _staff_desk = StaffUnderwritingDesk()
    return _staff_desk


def reset_staff_desk() -> None:
    global _staff_desk
    _staff_desk = None
