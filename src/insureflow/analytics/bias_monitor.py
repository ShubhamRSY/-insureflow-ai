"""Bias monitoring — track decision outcomes by insured attributes.

Monitors rejection rates, premium deltas, and override patterns across
demographic and geographic dimensions to detect disparate impact.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_DISPARATE_IMPACT_THRESHOLD = 0.80
_FOUR_FIFTHS_RULE = 0.80


class BiasDimension(str, Enum):
    # Protected class dimensions (ECOA / state fair-lending)
    AGE = "age"
    GENDER = "gender"
    MARITAL_STATUS = "marital_status"
    RACE_ETHNICITY = "race_ethnicity"
    DISABILITY = "disability"
    # Non-protected dimensions
    STATE = "state"
    INDUSTRY = "industry"
    OCCUPANCY = "occupancy"
    BROKER = "broker"
    POLICY_SIZE = "policy_size"

    @classmethod
    def protected(cls) -> list[BiasDimension]:
        """Dimensions protected under ECOA / state fair-lending statutes."""
        return [cls.AGE, cls.GENDER, cls.MARITAL_STATUS, cls.RACE_ETHNICITY, cls.DISABILITY]


class OutcomeBucket(BaseModel):
    dimension: BiasDimension
    group: str
    total_submissions: int = 0
    approved: int = 0
    declined: int = 0
    referred: int = 0
    overridden: int = 0
    approval_rate: float = 0.0
    avg_premium: float = 0.0
    avg_ai_confidence: float = 0.0


class BiasAlert(BaseModel):
    alert_id: str
    dimension: BiasDimension
    group_a: str
    group_b: str
    rate_a: float
    rate_b: float
    ratio: float
    threshold: float = _FOUR_FIFTHS_RULE
    message: str = ""
    severity: str = "warning"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class BiasReport(BaseModel):
    org_id: str = "default"
    buckets: list[OutcomeBucket] = Field(default_factory=list)
    alerts: list[BiasAlert] = Field(default_factory=list)
    total_submissions: int = 0
    overall_approval_rate: float = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class BiasMonitor:
    def __init__(self, org_id: str = "default") -> None:
        self.org_id = org_id
        self._records: list[dict[str, Any]] = []

    def record(
        self,
        submission_id: str,
        decision: str,
        attributes: dict[str, str],
        premium: float = 0.0,
        ai_confidence: float = 0.0,
        overridden: bool = False,
    ) -> None:
        self._records.append(
            {
                "submission_id": submission_id,
                "decision": decision,
                "attributes": attributes,
                "premium": premium,
                "ai_confidence": ai_confidence,
                "overridden": overridden,
                "recorded_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        )

    def _bucketize(self, dimension: BiasDimension) -> dict[str, OutcomeBucket]:
        buckets: dict[str, OutcomeBucket] = {}
        for rec in self._records:
            group = rec.get("attributes", {}).get(dimension.value, "unknown")
            if group not in buckets:
                buckets[group] = OutcomeBucket(dimension=dimension, group=group)
            b = buckets[group]
            b.total_submissions += 1
            decision = rec.get("decision", "").lower()
            if decision in ("accept", "approve", "quote"):
                b.approved += 1
            elif decision in ("decline", "no_quote"):
                b.declined += 1
            else:
                b.referred += 1
            if rec.get("overridden"):
                b.overridden += 1
            b.avg_premium += rec.get("premium", 0.0)
            b.avg_ai_confidence += rec.get("ai_confidence", 0.0)
        for b in buckets.values():
            if b.total_submissions > 0:
                b.approval_rate = b.approved / b.total_submissions
                b.avg_premium /= b.total_submissions
                b.avg_ai_confidence /= b.total_submissions
        return buckets

    def _detect_disparate_impact(
        self,
        buckets: dict[str, OutcomeBucket],
        dimension: BiasDimension | None = None,
    ) -> list[BiasAlert]:
        alerts: list[BiasAlert] = []
        entries = list(buckets.values())
        if len(entries) < 2:
            return alerts
        rates = {e.group: e.approval_rate for e in entries if e.total_submissions >= 5}
        if len(rates) < 2:
            return alerts
        rate_list = list(rates.items())
        dim = dimension or BiasDimension.STATE
        for i in range(len(rate_list)):
            for j in range(i + 1, len(rate_list)):
                g_a, r_a = rate_list[i]
                g_b, r_b = rate_list[j]
                if r_b == 0:
                    ratio = 0.0 if r_a > 0 else 1.0
                elif r_a == 0:
                    ratio = 0.0 if r_b > 0 else 1.0
                else:
                    ratio = min(r_a, r_b) / max(r_a, r_b)
                if ratio < _DISPARATE_IMPACT_THRESHOLD:
                    alerts.append(
                        BiasAlert(
                            alert_id=f"bias-{dim.value}-{g_a}-{g_b}",
                            dimension=dim,
                            group_a=g_a,
                            group_b=g_b,
                            rate_a=r_a,
                            rate_b=r_b,
                            ratio=ratio,
                            message=f"[{dim.value}] Approval rate ratio {ratio:.2f} < {_FOUR_FIFTHS_RULE:.2f} between {g_a} ({r_a:.1%}) and {g_b} ({r_b:.1%})",
                            severity="critical" if dim in BiasDimension.protected() else "warning",
                        )
                    )
        return alerts

    def generate_report(self, dimensions: list[BiasDimension] | None = None) -> BiasReport:
        dims = dimensions or list(BiasDimension)
        all_buckets: list[OutcomeBucket] = []
        all_alerts: list[BiasAlert] = []
        for dim in dims:
            buckets = self._bucketize(dim)
            all_buckets.extend(buckets.values())
            all_alerts.extend(self._detect_disparate_impact(buckets, dimension=dim))
        total = len(self._records)
        approved = sum(1 for r in self._records if r.get("decision", "").lower() in ("accept", "approve", "quote"))
        return BiasReport(
            org_id=self.org_id,
            buckets=all_buckets,
            alerts=all_alerts,
            total_submissions=total,
            overall_approval_rate=approved / total if total > 0 else 0.0,
        )

    def check_protected_class_alerts(self) -> list[BiasAlert]:
        """Return only alerts on protected-class dimensions for quick compliance review."""
        report = self.generate_report(dimensions=BiasDimension.protected())
        return report.alerts
