"""Renewal Engine — Pre-Renewal Workflow & Premium Audit.

60-120 days before expiry, the renewal process starts: should we renew,
change price, or non-renew? Bundled policies have 91% retention vs 67%
for single policies, so the engine factors in multi-line attachment.

Premium audit tracks end-of-year revenue reconciliation — comparing
actual vs estimated premium to true-up policies after the policy period ends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


class RenewalAction(str, Enum):
    RENEW = "renew"  # Standard renewal
    RENEW_WITH_MODIFICATION = "renew_with_modification"  # Change terms/price
    NON_RENEW = "non_renew"  # Decline to renew
    REFER_TO_UW = "refer_to_uw"  # Needs UW review


class RetentionRisk(str, Enum):
    LOW = "low"  # Likely to stay
    MEDIUM = "medium"  # May shop around
    HIGH = "high"  # At risk of leaving


class AuditStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISPUTED = "disputed"


class AuditAdjustmentType(str, Enum):
    EXPOSURE_CHANGE = "exposure_change"
    RATE_CORRECTION = "rate_correction"
    CANCELLATION = "cancellation"
    ENDORSEMENT = "endorsement"
    AUDIT_FINDING = "audit_finding"
    DISPUTE_RESOLUTION = "dispute_resolution"


@dataclass
class PolicyLapse:
    """A single policy that might be part of a bundled account."""

    policy_number: str
    line_of_business: str
    current_premium: float
    expiry_date: date
    claims_count: int = 0
    loss_ratio: float = 0.0
    is_active: bool = True


@dataclass
class BundledAccount:
    """All policies for one insured, used for retention analysis."""

    account_id: str
    insured_name: str
    policies: list[PolicyLapse] = field(default_factory=list)

    @property
    def total_premium(self) -> float:
        return sum(p.current_premium for p in self.policies if p.is_active)

    @property
    def policy_count(self) -> int:
        return len([p for p in self.policies if p.is_active])

    @property
    def bundling_score(self) -> float:
        """0.0 = single policy, 1.0 = fully bundled (3+ lines)"""
        count = self.policy_count
        if count >= 4:
            return 1.0
        elif count == 3:
            return 0.9
        elif count == 2:
            return 0.6
        return 0.0


@dataclass
class RenewalRecommendation:
    recommendation_id: str
    bundle_id: str
    org_id: str = "default"

    action: RenewalAction = RenewalAction.RENEW
    retention_risk: RetentionRisk = RetentionRisk.LOW
    retention_score: float = 0.0  # 0-1, higher = more likely to retain

    current_premium: float = 0.0
    proposed_premium: float = 0.0
    premium_change_pct: float = 0.0

    # Bundling analysis
    bundled_account: Optional[BundledAccount] = None
    bundling_discount_pct: float = 0.0
    bundling_premium_savings: float = 0.0

    # Claims experience
    total_claims: int = 0
    loss_ratio: float = 0.0
    loss_ratio_trend: str = "stable"  # improving | stable | deteriorating

    # Narrative
    rationale: str = ""
    conditions: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass
class PremiumAuditAdjustment:
    adjustment_id: str
    type: AuditAdjustmentType
    description: str
    amount: float
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def signed_amount(self) -> float:
        return self.amount


@dataclass
class PremiumAudit:
    audit_id: str
    bundle_id: str
    org_id: str = "default"
    policy_number: str = ""

    policy_period_start: Optional[date] = None
    policy_period_end: Optional[date] = None

    estimated_premium: float = 0.0
    actual_premium: float = 0.0
    audited_exposure: str = ""
    status: AuditStatus = AuditStatus.PENDING

    adjustments: list[PremiumAuditAdjustment] = field(default_factory=list)
    reconciliation_notes: str = ""
    reconciled_at: Optional[datetime] = None
    reconciled_by: str = ""

    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def total_adjustments(self) -> float:
        return sum(a.signed_amount for a in self.adjustments)

    @property
    def premium_delta(self) -> float:
        return self.actual_premium - self.estimated_premium + self.total_adjustments

    @property
    def premium_delta_pct(self) -> float:
        if self.estimated_premium == 0:
            return 0.0
        return (self.premium_delta / self.estimated_premium) * 100.0

    @property
    def is_past_due(self) -> bool:
        if self.status != AuditStatus.COMPLETED and self.policy_period_end:
            return date.today() > self.policy_period_end + timedelta(days=90)
        return False


RENEWAL_LR_THRESHOLDS = {
    "improving": 0.35,
    "stable": 0.55,
    "deteriorating": 0.70,
}


class RenewalEngine:
    """Evaluates renewal risk and generates recommendations.

    Mirrors the real small-carrier renewal process: 60-120 days before
    expiry, analyze loss experience, market conditions, and bundling
    to decide terms.
    """

    def __init__(self) -> None:
        self._lapse_store: dict[str, list[PolicyLapse]] = {}

    def register_policy(self, policy: PolicyLapse) -> None:
        self._lapse_store.setdefault(policy.policy_number, [])
        self._lapse_store[policy.policy_number].append(policy)

    def analyze_renewal(
        self,
        bundle_id: str,
        insured_name: str,
        current_premium: float,
        loss_ratio: float,
        claims_count: int = 0,
        line_of_business: str = "commercial_package",
        expiry_date: Optional[date] = None,
        policy_number: str = "",
        org_id: str = "default",
    ) -> RenewalRecommendation:
        now = date.today()
        months_to_expiry = ((expiry_date.year - now.year) * 12 + (expiry_date.month - now.month)) if expiry_date else 6

        # Determine loss ratio trend
        if loss_ratio <= RENEWAL_LR_THRESHOLDS["improving"]:
            lr_trend = "improving"
        elif loss_ratio <= RENEWAL_LR_THRESHOLDS["stable"]:
            lr_trend = "stable"
        else:
            lr_trend = "deteriorating"

        # Check for bundled account
        account = self._find_account(insured_name)
        bundling_discount = 0.0
        bundling_savings = 0.0
        retention_score = 0.5  # baseline

        if account and account.policy_count > 1:
            bundling_discount = min(15.0, account.policy_count * 5.0)  # 5% per line, max 15%
            bundling_savings = current_premium * (bundling_discount / 100.0)
            retention_score += 0.2 + (account.bundling_score * 0.25)
            # Bundled policies stick 91% of the time
            retention_score = min(0.95, retention_score + 0.15)

        # Adjust premium
        premium_change = 0.0
        if lr_trend == "deteriorating":
            premium_change = min(25.0, (loss_ratio - 0.55) * 50.0)
        elif lr_trend == "improving":
            premium_change = max(-15.0, -(0.35 - loss_ratio) * 50.0)

        # Bundled discount offsets premium increase
        net_change = premium_change - bundling_discount
        proposed_premium = current_premium * (1 + net_change / 100.0)
        proposed_premium = max(proposed_premium, current_premium * 0.85)  # max 15% decrease
        proposed_premium = min(proposed_premium, current_premium * 1.35)  # max 35% increase

        # Determine action
        action = RenewalAction.RENEW
        conditions: list[str] = []

        if loss_ratio > 0.75 and claims_count >= 3:
            action = RenewalAction.NON_RENEW
            retention_score = max(0.1, retention_score - 0.4)
            rationale = f"Loss ratio of {loss_ratio:.0%} with {claims_count} claims exceeds renewal threshold — recommending non-renewal"
        elif loss_ratio > 0.60:
            action = RenewalAction.RENEW_WITH_MODIFICATION
            retention_score = max(0.2, retention_score - 0.2)
            conditions.append("Reduce limits or increase deductible by 25%")
            conditions.append("Consider excluding problem coverages")
            rationale = f"Loss ratio of {loss_ratio:.0%} is elevated — renewing with modified terms ({net_change:+.0f}% premium change)"
        elif net_change < -5.0:
            action = RenewalAction.RENEW_WITH_MODIFICATION
            rationale = f"Favorable experience — reducing premium {net_change:+.0f}% (bundling discount: {bundling_discount:.0f}%)"
        else:
            rationale = f"Standard renewal — experience within thresholds, premium {net_change:+.0f}%"

        if bundling_discount > 0:
            conditions.append(f"Multi-policy bundling discount: {bundling_discount:.0f}%")
            conditions.append(f"Retention incentive: ${bundling_savings:,.0f} savings")

        if months_to_expiry < 2:
            action = RenewalAction.REFER_TO_UW
            rationale += " — Expiring within 60 days, requires UW expedite"

        # Retention risk assessment
        if retention_score >= 0.75:
            retention_risk = RetentionRisk.LOW
        elif retention_score >= 0.45:
            retention_risk = RetentionRisk.MEDIUM
        else:
            retention_risk = RetentionRisk.HIGH

        return RenewalRecommendation(
            recommendation_id=f"ren-{uuid4().hex[:10]}",
            bundle_id=bundle_id,
            org_id=org_id,
            action=action,
            retention_risk=retention_risk,
            retention_score=round(retention_score, 3),
            current_premium=current_premium,
            proposed_premium=round(proposed_premium, 2),
            premium_change_pct=round(net_change, 1),
            bundled_account=account,
            bundling_discount_pct=round(bundling_discount, 1),
            bundling_premium_savings=round(bundling_savings, 2),
            total_claims=claims_count,
            loss_ratio=round(loss_ratio, 4),
            loss_ratio_trend=lr_trend,
            rationale=rationale,
            conditions=conditions,
        )

    def _find_account(self, insured_name: str) -> Optional[BundledAccount]:
        """Try to find a bundled account for this insured."""
        if not insured_name:
            return None
        # In real system, this queries policy admin system.
        # For demo, return None so bundling logic still works with explicit data.
        return None

    def find_expiring_policies(
        self,
        within_days: int = 120,
        org_id: str = "default",
    ) -> list[PolicyLapse]:
        """Find policies expiring within the window for renewal processing."""
        target = date.today() + timedelta(days=within_days)
        expiring: list[PolicyLapse] = []
        for policies in self._lapse_store.values():
            for p in policies:
                if p.expiry_date <= target and p.is_active:
                    expiring.append(p)
        return expiring


class PremiumAuditEngine:
    """End-of-year premium audit tracking and reconciliation.

    After a policy period ends, carriers perform a premium audit to compare
    actual exposure/revenue against the estimated premium charged at inception.
    Differences are reconciled via adjustments (additional premium or return
    premium).
    """

    def __init__(self) -> None:
        self._audits: dict[str, PremiumAudit] = {}

    def create_audit(
        self,
        bundle_id: str,
        estimated_premium: float,
        policy_period_start: Optional[date] = None,
        policy_period_end: Optional[date] = None,
        policy_number: str = "",
        org_id: str = "default",
    ) -> PremiumAudit:
        audit = PremiumAudit(
            audit_id=f"aud-{uuid4().hex[:10]}",
            bundle_id=bundle_id,
            org_id=org_id,
            policy_number=policy_number,
            policy_period_start=policy_period_start,
            policy_period_end=policy_period_end,
            estimated_premium=estimated_premium,
            status=AuditStatus.PENDING,
        )
        self._audits[audit.audit_id] = audit
        return audit

    def start_audit(self, audit_id: str, started_by: str = "") -> PremiumAudit:
        audit = self._get_audit(audit_id)
        audit.status = AuditStatus.IN_PROGRESS
        return audit

    def add_adjustment(
        self,
        audit_id: str,
        adjustment_type: AuditAdjustmentType,
        description: str,
        amount: float,
    ) -> PremiumAudit:
        audit = self._get_audit(audit_id)
        adj = PremiumAuditAdjustment(
            adjustment_id=f"adj-{uuid4().hex[:8]}",
            type=adjustment_type,
            description=description,
            amount=amount,
        )
        audit.adjustments.append(adj)
        return audit

    def complete_audit(
        self,
        audit_id: str,
        actual_premium: float,
        audited_exposure: str = "",
        notes: str = "",
        reconciled_by: str = "",
    ) -> PremiumAudit:
        audit = self._get_audit(audit_id)
        audit.actual_premium = actual_premium
        audit.audited_exposure = audited_exposure
        audit.status = AuditStatus.COMPLETED
        audit.reconciliation_notes = notes
        audit.reconciled_by = reconciled_by
        audit.reconciled_at = datetime.now(tz=timezone.utc)
        return audit

    def dispute_audit(self, audit_id: str, reason: str) -> PremiumAudit:
        audit = self._get_audit(audit_id)
        audit.status = AuditStatus.DISPUTED
        audit.reconciliation_notes = reason
        return audit

    def get_audit(self, audit_id: str) -> Optional[PremiumAudit]:
        return self._audits.get(audit_id)

    def list_audits(
        self,
        org_id: str = "default",
        status: Optional[AuditStatus] = None,
        include_past_due: bool = False,
    ) -> list[PremiumAudit]:
        results = [a for a in self._audits.values() if a.org_id == org_id]
        if status:
            results = [a for a in results if a.status == status]
        if include_past_due:
            results = [a for a in results if a.is_past_due or status is None or a.status == status]
        return sorted(results, key=lambda a: a.created_at, reverse=True)

    def audits_needing_renewal_review(self, org_id: str = "default") -> list[PremiumAudit]:
        """Audits with material adjustments needing UW attention."""
        material: list[PremiumAudit] = []
        for a in self.list_audits(org_id):
            if a.status == AuditStatus.COMPLETED and abs(a.premium_delta_pct) > 15.0:
                material.append(a)
            elif a.status == AuditStatus.DISPUTED:
                material.append(a)
        return material

    def _get_audit(self, audit_id: str) -> PremiumAudit:
        if audit_id not in self._audits:
            raise KeyError(f"Audit not found: {audit_id}")
        return self._audits[audit_id]
