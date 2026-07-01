from __future__ import annotations

from collections import defaultdict
from typing import Optional
from uuid import uuid4

from insureflow.outcomes.override import (
    OverrideAnalyticsQuery,
    OverrideAnalyticsSummary,
    OverrideDetail,
    OverridePattern,
    OverrideReasonCategory,
    PremiumDelta,
)


class OverrideAnalyticsEngine:
    """Tracks UW override events, detects recurring patterns, and produces
    analytics summaries that can inform underwriting rule updates.

    This is the core of the lifecycle layer — it closes the loop between
    UW decisions and AI model improvement.
    """

    def __init__(self) -> None:
        self._overrides: dict[str, OverrideDetail] = {}
        self._patterns: dict[str, OverridePattern] = {}
        self._load_seed_data()

    def _load_seed_data(self) -> None:
        """Populate with demo overrides to enable analytics out of the box."""
        seeds = [
            OverrideDetail(
                override_id="ovr-seed-001",
                sign_off_id="so-seed-001",
                bundle_id="seed-override-001",
                ai_decision="decline",
                uw_decision="accept",
                decision_changed=True,
                premium_delta=PremiumDelta(
                    ai_premium=0,
                    uw_premium=8_500,
                    delta=8_500,
                    delta_pct=1.0,
                    reason="Client has strong loss history elsewhere",
                ),
                reason_category=OverrideReasonCategory.CLIENT_RELATIONSHIP,
                reason_freeform="Long-standing client with profitable book elsewhere",
                uw_confidence="high",
            ),
            OverrideDetail(
                override_id="ovr-seed-002",
                sign_off_id="so-seed-002",
                bundle_id="seed-override-002",
                ai_decision="accept",
                uw_decision="accept",
                decision_changed=False,
                premium_delta=PremiumDelta(
                    ai_premium=12_000, uw_premium=12_000, delta=0, delta_pct=0.0, reason="No change"
                ),
                reason_category=OverrideReasonCategory.PRICING,
                reason_freeform="Premium within acceptable range",
                uw_confidence="high",
            ),
            OverrideDetail(
                override_id="ovr-seed-003",
                sign_off_id="so-seed-003",
                bundle_id="seed-override-003",
                ai_decision="accept",
                uw_decision="decline",
                decision_changed=True,
                premium_delta=PremiumDelta(
                    ai_premium=22_000,
                    uw_premium=0,
                    delta=-22_000,
                    delta_pct=-1.0,
                    reason="Building age + location risk",
                ),
                reason_category=OverrideReasonCategory.APPETITE,
                reason_freeform="Building over 50 years in CAT-exposed zone — AI missed construction quality",
                uw_confidence="high",
                post_bind_verdict="correct",
            ),
        ]
        for s in seeds:
            self._overrides[s.override_id] = s
        self._detect_patterns()

    def record_override(self, detail: OverrideDetail) -> None:
        self._overrides[detail.override_id] = detail
        self._detect_patterns()

    def get_override(self, override_id: str) -> Optional[OverrideDetail]:
        return self._overrides.get(override_id)

    def query_overrides(self, query: OverrideAnalyticsQuery) -> list[OverrideDetail]:
        results = [o for o in self._overrides.values() if o.org_id == query.org_id]
        if query.reason_category:
            results = [o for o in results if o.reason_category == query.reason_category]
        if query.decision_changed_only:
            results = [o for o in results if o.decision_changed]
        if query.date_from:
            results = [o for o in results if o.created_at >= query.date_from]
        if query.date_to:
            results = [o for o in results if o.created_at <= query.date_to]
        results.sort(key=lambda o: o.created_at, reverse=True)
        return results[query.offset : query.offset + query.limit]

    def get_patterns(self, active_only: bool = True) -> list[OverridePattern]:
        if active_only:
            return [p for p in self._patterns.values() if p.active]
        return list(self._patterns.values())

    def generate_summary(self, org_id: str = "default") -> OverrideAnalyticsSummary:
        org_overrides = [o for o in self._overrides.values() if o.org_id == org_id]
        total = len(org_overrides)
        decision_changes = [o for o in org_overrides if o.decision_changed]
        category_counts: dict[str, int] = defaultdict(int)

        premium_deltas: list[float] = []
        for o in org_overrides:
            category_counts[o.reason_category.value] += 1
            if o.premium_delta:
                premium_deltas.append(o.premium_delta.delta_pct)

        return OverrideAnalyticsSummary(
            total_overrides=total,
            total_decision_changes=len(decision_changes),
            decision_change_rate=len(decision_changes) / total if total else 0.0,
            avg_premium_delta_pct=sum(premium_deltas) / len(premium_deltas)
            if premium_deltas
            else 0.0,
            by_category=dict(category_counts),
            top_patterns=self.get_patterns(),
        )

    def _detect_patterns(self) -> None:
        """Analyze existing overrides and group into patterns."""
        patterns: dict[str, dict] = {}

        for o in self._overrides.values():
            if not o.decision_changed:
                continue

            key = f"{o.reason_category.value}:{o.ai_decision}->{o.uw_decision}"
            if key not in patterns:
                patterns[key] = {
                    "count": 0,
                    "categories": [],
                    "premium_deltas": [],
                    "first_seen": o.created_at,
                    "last_seen": o.created_at,
                    "description": f"Overrides of type {o.reason_category.value}: {o.ai_decision} → {o.uw_decision}",
                    "suggested_rule": self._suggest_rule_update(o),
                }
            p = patterns[key]
            p["count"] += 1
            if o.reason_category not in p["categories"]:
                p["categories"].append(o.reason_category)
            if o.premium_delta:
                p["premium_deltas"].append(o.premium_delta.delta_pct)
            if o.created_at < p["first_seen"]:
                p["first_seen"] = o.created_at
            if o.created_at > p["last_seen"]:
                p["last_seen"] = o.created_at

        self._patterns.clear()
        for i, (key, data) in enumerate(
            sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True)
        ):
            avg_delta = (
                sum(data["premium_deltas"]) / len(data["premium_deltas"])
                if data["premium_deltas"]
                else 0.0
            )
            common_shift = key.split(":", 1)[1] if ":" in key else ""
            self._patterns[f"pat-{uuid4().hex[:8]}"] = OverridePattern(
                pattern_id=f"pat-{uuid4().hex[:8]}",
                description=data["description"],
                reason_categories=data["categories"],
                trigger_count=data["count"],
                avg_premium_delta_pct=avg_delta,
                common_decision_shift=common_shift,
                suggested_rule_update=data["suggested_rule"],
                rule_priority=data["count"] * 10,
                first_seen=data["first_seen"],
                last_seen=data["last_seen"],
            )

    def _suggest_rule_update(self, override: OverrideDetail) -> str:
        if override.reason_category == OverrideReasonCategory.APPETITE:
            return "Review appetite filter thresholds — AI may be excluding risks UW consistently accepts"
        elif override.reason_category == OverrideReasonCategory.PRICING:
            delta_pct = abs(override.premium_delta.delta_pct) * 100 if override.premium_delta else 0
            return f"Calibrate rating model — UW consistently adjusts premium by {delta_pct:.0f}% when delta exists"
        elif override.reason_category == OverrideReasonCategory.CLIENT_RELATIONSHIP:
            return "Add client-relationship override rule for existing book rollovers"
        elif override.reason_category == OverrideReasonCategory.DATA_QUALITY:
            return (
                "Improve extraction pipeline — UW often corrects data that AI extracted incorrectly"
            )
        elif override.reason_category == OverrideReasonCategory.MARKET_CONDITIONS:
            return "Add market-condition override signal — UW considers competitive environment"
        return "Review underwriting guidelines for this override type"


_analytics_engine: OverrideAnalyticsEngine | None = None


def get_analytics_engine() -> OverrideAnalyticsEngine:
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = OverrideAnalyticsEngine()
    return _analytics_engine
