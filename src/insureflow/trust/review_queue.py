"""HITL review queue — prioritize and serve work items for human underwriters.

Builds a prioritized queue of submissions requiring human review, scored by
urgency, complexity, and time-in-queue.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_ESCALATION_HOURS = float(os.getenv("REVIEW_QUEUE_ESCALATION_HOURS", "24"))


class PriorityLevel(str, Enum):
    HOT = "hot"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewItem(BaseModel):
    item_id: str
    bundle_id: str
    org_id: str = "default"
    priority: PriorityLevel = PriorityLevel.MEDIUM
    reason: str = ""
    ai_decision: str = ""
    verification_issues: int = 0
    confidence_score: float = 0.0
    routing_tier: str = ""
    assigned_to: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    time_in_queue_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compute_priority(self) -> PriorityLevel:
        score = 0.0
        if self.verification_issues >= 5:
            score += 3
        elif self.verification_issues >= 3:
            score += 2
        elif self.verification_issues >= 1:
            score += 1
        if self.confidence_score < 0.3:
            score += 3
        elif self.confidence_score < 0.5:
            score += 2
        elif self.confidence_score < 0.7:
            score += 1
        hours = self.time_in_queue_seconds / 3600.0
        escalation = _ESCALATION_HOURS if _ESCALATION_HOURS > 0 else 24.0
        if hours > escalation:
            score += 2
        elif hours > escalation / 2:
            score += 1
        if self.ai_decision.lower() in ("decline", "no_quote"):
            score += 1

        if score >= 6:
            return PriorityLevel.HOT
        if score >= 4:
            return PriorityLevel.HIGH
        if score >= 2:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW


class ReviewQueue:
    def __init__(self, org_id: str = "default") -> None:
        self.org_id = org_id
        self._items: dict[str, ReviewItem] = {}

    def add(
        self,
        bundle_id: str,
        reason: str = "",
        ai_decision: str = "",
        verification_issues: int = 0,
        confidence_score: float = 0.0,
        routing_tier: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ReviewItem:
        item_id = f"rq-{bundle_id[:12]}-{len(self._items) + 1:04d}"
        item = ReviewItem(
            item_id=item_id,
            bundle_id=bundle_id,
            org_id=self.org_id,
            reason=reason,
            ai_decision=ai_decision,
            verification_issues=verification_issues,
            confidence_score=confidence_score,
            routing_tier=routing_tier,
            metadata=metadata or {},
        )
        item.priority = item.compute_priority()
        self._items[item_id] = item
        return item

    def get(self, item_id: str) -> ReviewItem | None:
        return self._items.get(item_id)

    def assign(self, item_id: str, username: str) -> ReviewItem | None:
        item = self._items.get(item_id)
        if not item:
            return None
        item.assigned_to = username
        item.updated_at = datetime.now(tz=timezone.utc)
        return item

    def complete(self, item_id: str) -> ReviewItem | None:
        item = self._items.pop(item_id, None)
        return item

    def queue(
        self,
        *,
        priority: PriorityLevel | None = None,
        assigned_to: str | None = None,
        limit: int = 50,
    ) -> list[ReviewItem]:
        now = datetime.now(tz=timezone.utc)
        items = list(self._items.values())
        for item in items:
            delta = (now - item.created_at).total_seconds()
            item.time_in_queue_seconds = delta
            item.priority = item.compute_priority()

        if priority is not None:
            items = [i for i in items if i.priority == priority]
        if assigned_to is not None:
            items = [i for i in items if i.assigned_to == assigned_to]

        priority_order = {PriorityLevel.HOT: 0, PriorityLevel.HIGH: 1, PriorityLevel.MEDIUM: 2, PriorityLevel.LOW: 3}
        items.sort(key=lambda i: (priority_order.get(i.priority, 99), -i.time_in_queue_seconds))
        return items[:limit]

    def stats(self) -> dict[str, Any]:
        items = list(self._items.values())
        by_priority: dict[str, int] = {}
        for item in items:
            by_priority[item.priority.value] = by_priority.get(item.priority.value, 0) + 1
        assigned = sum(1 for i in items if i.assigned_to)
        return {
            "org_id": self.org_id,
            "total_pending": len(items),
            "by_priority": by_priority,
            "assigned": assigned,
            "unassigned": len(items) - assigned,
        }

    def age_oldest(self) -> float:
        if not self._items:
            return 0.0
        now = datetime.now(tz=timezone.utc)
        return max((now - item.created_at).total_seconds() for item in self._items.values())


_review_queues: dict[str, ReviewQueue] = {}


def get_review_queue(org_id: str = "default") -> ReviewQueue:
    if org_id not in _review_queues:
        _review_queues[org_id] = ReviewQueue(org_id=org_id)
    return _review_queues[org_id]
