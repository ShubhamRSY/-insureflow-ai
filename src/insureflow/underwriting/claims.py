"""Claims lifecycle — FNOL, adjudication, subrogation, salvage, defense, indemnity.

Covers the back half of the claim lifecycle that loss-run intake does not: the
first notice of loss (FNOL), coverage adjudication (approve / deny / settle),
subrogation against negligent third parties, salvage of damaged property, and
defense-cost handling (defense-in-addition-to vs defense-within-limits).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Iterable

from insureflow.models.policy import (
    AdjudicationReview,
    ClaimAdjudication,
    ClaimDecision,
    NoticeOfLoss,
    SalvageRecovery,
    SubrogationRecovery,
    SubrogationStatus,
)
from insureflow.models.submissions import ClaimRecord, CoverageDetail, SubmissionBundle

# Cause markers suggesting a negligent third party may be liable (subrogation).
_SUBROGATION_MARKERS = (
    "third party",
    "negligence",
    "driver",
    "vehicle",
    "collision",
    "hit by",
    "contractor",
    "subcontractor",
    "defective product",
    "trip and fall",
    "premises liability",
    "water damage from tenant",
    "overturned",
)

# Markers suggesting recoverable physical property (salvage).
_SALVAGE_MARKERS = ("vehicle", "fire damage", "inventory", "stock", "contents", "equipment", "wreck")

# Exclusion keywords that make a claim not-covered.
_EXCLUSION_MARKERS = (
    "wear and tear",
    "gradual deterioration",
    "maintenance",
    "pre-existing",
    "intentional",
    "fraud",
    "war",
    "nuclear",
    "pollution",
    "flood",
)


# ──────────────────────────────────────────────────────────────────────────
# First Notice of Loss (FNOL)
# ──────────────────────────────────────────────────────────────────────────
def create_notice_of_loss(
    *,
    loss_date: date,
    cause: str,
    description: str = "",
    line_of_business: str = "",
    reporter: str = "",
    reported_at: date | None = None,
    claim_id: str = "",
    fnol_id: str = "",
) -> NoticeOfLoss:
    """Create a First Notice of Loss record from the initial notification."""
    return NoticeOfLoss(
        fnol_id=fnol_id or f"FNOL-{uuid.uuid4().hex[:8].upper()}",
        claim_id=claim_id,
        reported_at=reported_at or date.today(),
        loss_date=loss_date,
        line_of_business=line_of_business,
        cause=cause,
        reporter=reporter,
        description=description,
        status="submitted",
    )


def acknowledge_notice(notice: NoticeOfLoss, *, claim_id: str = "") -> NoticeOfLoss:
    """Acknowledge an FNOL, optionally linking it to a new claim file."""
    notice.status = "acknowledged"
    if claim_id:
        notice.claim_id = claim_id
    return notice


# ──────────────────────────────────────────────────────────────────────────
# Claim adjudication
# ──────────────────────────────────────────────────────────────────────────
def _coverage_valid_for(claim: ClaimRecord, coverage: CoverageDetail | None) -> tuple[bool, str]:
    if coverage is None:
        return True, ""
    blob = f"{claim.cause} {claim.description} {claim.notes}".lower()
    blob += f" {coverage.coverage_type}".lower()
    for marker in _EXCLUSION_MARKERS:
        if marker in blob and marker not in coverage.coverage_type.lower():
            return False, f"Excluded cause: {marker}"
    return True, ""


def adjudicate_claim(
    claim: ClaimRecord,
    coverage: CoverageDetail | None = None,
    *,
    defense_costs: float = 0.0,
) -> ClaimAdjudication:
    """Evaluate one claim against the policy's coverage terms."""
    valid, reason = _coverage_valid_for(claim, coverage)
    paid = max(float(claim.paid_amount or 0.0), 0.0)
    reserve = max(float(claim.open_reserve or 0.0), 0.0)
    defense = max(float(defense_costs or claim.defense_cost or 0.0), 0.0)

    if not valid:
        return ClaimAdjudication(
            claim_id=claim.claim_id,
            coverage_valid=False,
            decision=ClaimDecision.DENIED,
            denial_reason=reason,
            disposition_detail=f"Claim {claim.claim_id} denied — {reason}",
        )

    if claim.settlement_amount is not None:
        settlement = float(claim.settlement_amount)
        return ClaimAdjudication(
            claim_id=claim.claim_id,
            coverage_valid=True,
            decision=ClaimDecision.SETTLED,
            settlement_amount=round(settlement, 2),
            paid_indemnity=round(min(settlement, paid) if paid else settlement, 2),
            defense_costs=round(defense, 2),
            disposition_detail=f"Claim {claim.claim_id} settled for {settlement:,.0f}",
        )

    if claim.adjudication_decision == "denied":
        return ClaimAdjudication(
            claim_id=claim.claim_id,
            coverage_valid=True,
            decision=ClaimDecision.DENIED,
            denial_reason=claim.denial_reason or "",
            disposition_detail=f"Claim {claim.claim_id} denied by prior adjudication",
        )

    decision = ClaimDecision.PENDING if reserve > 0 and paid == 0 else ClaimDecision.APPROVED
    return ClaimAdjudication(
        claim_id=claim.claim_id,
        coverage_valid=True,
        decision=decision,
        paid_indemnity=round(paid, 2),
        defense_costs=round(defense, 2),
        settlement_amount=round(paid, 2),
        disposition_detail=(
            f"Claim {claim.claim_id} approved — {paid:,.0f} paid, {reserve:,.0f} held as reserve"
            if decision == ClaimDecision.APPROVED
            else f"Claim {claim.claim_id} pending — reserve {reserve:,.0f} held"
        ),
    )


def _claims(bundle: SubmissionBundle) -> list[ClaimRecord]:
    structured = bundle.structured
    if structured is None:
        return []
    claims: list[ClaimRecord] = []
    if structured.risk_profile:
        claims.extend(structured.risk_profile.prior_claims or [])
    if structured.financial and structured.financial.loss_run:
        claims.extend(structured.financial.loss_run.claims or [])
    return claims


def adjudicate_claims(
    bundle: SubmissionBundle,
    *,
    coverage: CoverageDetail | None = None,
    defense_costs: float = 0.0,
) -> AdjudicationReview:
    """Adjudicate every claim on the submission and roll up the outcomes."""
    decisions = [adjudicate_claim(c, coverage, defense_costs=defense_costs) for c in _claims(bundle)]
    review = AdjudicationReview(decisions=decisions)
    for d in decisions:
        if d.decision == ClaimDecision.APPROVED:
            review.approved_count += 1
        elif d.decision == ClaimDecision.DENIED:
            review.denied_count += 1
        elif d.decision == ClaimDecision.SETTLED:
            review.settled_count += 1
        else:
            review.pending_count += 1
        review.total_paid_indemnity += d.paid_indemnity
        review.total_defense_costs += d.defense_costs
        review.total_settlements += d.settlement_amount or 0.0
    review.summary = (
        f"{len(decisions)} claim(s): {review.approved_count} approved, {review.denied_count} denied, {review.settled_count} settled, {review.pending_count} pending"
        if decisions
        else "No claims to adjudicate"
    )
    return review


# ──────────────────────────────────────────────────────────────────────────
# Subrogation
# ──────────────────────────────────────────────────────────────────────────
def evaluate_subrogation(claim: ClaimRecord) -> SubrogationRecovery:
    """Assess whether a negligent third party may owe recovery on the claim."""
    blob = f"{claim.cause} {claim.description} {claim.notes}".lower()
    parties = [m for m in _SUBROGATION_MARKERS if m in blob]
    incurred = max(float(claim.incurred_amount or 0.0), 0.0)
    if not parties:
        return SubrogationRecovery(
            claim_id=claim.claim_id,
            status=SubrogationStatus.NOT_PURSUED,
            potential_recovery=0.0,
            recovery_amount=float(getattr(claim, "subrogation_recovery", 0.0) or 0.0),
            detail=f"No third-party liability markers on claim {claim.claim_id}",
        )
    third_party = parties[0]
    potential = round(incurred * 0.60, 2)
    recovered = float(getattr(claim, "subrogation_recovery", 0.0) or 0.0)
    status = SubrogationStatus.RECOVERED if recovered > 0 else SubrogationStatus.PURSUED
    return SubrogationRecovery(
        claim_id=claim.claim_id,
        status=status,
        third_party=third_party,
        potential_recovery=potential,
        recovery_amount=recovered,
        recovery_percent=round(recovered / potential, 4) if potential > 0 else 0.0,
        detail=(f"Subrogation recovered {recovered:,.0f} against {third_party}" if recovered > 0 else f"Subrogation pursued against {third_party} — potential recovery ~{potential:,.0f}"),
    )


# ──────────────────────────────────────────────────────────────────────────
# Salvage
# ──────────────────────────────────────────────────────────────────────────
def evaluate_salvage(claim: ClaimRecord) -> SalvageRecovery:
    """Assess recovery from retaining/reselling damaged physical property."""
    blob = f"{claim.cause} {claim.description} {claim.notes}".lower()
    markers = [m for m in _SALVAGE_MARKERS if m in blob]
    salvage_value = float(getattr(claim, "salvage_value", 0.0) or 0.0)
    if not markers:
        return SalvageRecovery(
            claim_id=claim.claim_id,
            salvage_value=salvage_value,
            offset_amount=0.0,
            detail=f"No salvageable property markers on claim {claim.claim_id}",
        )
    if salvage_value <= 0:
        salvage_value = round(max(float(claim.incurred_amount or 0.0), 0.0) * 0.25, 2)
    resale = round(salvage_value * 0.80, 2)
    return SalvageRecovery(
        claim_id=claim.claim_id,
        property_description=markers[0],
        salvage_value=round(salvage_value, 2),
        resale_amount=resale,
        offset_amount=resale,
        detail=f"Salvage of {markers[0]} valued at {salvage_value:,.0f}; resale offsets {resale:,.0f} of claim cost",
    )


def claims_recovery_review(bundle: SubmissionBundle) -> dict[str, Any]:
    """Subrogation + salvage review across the whole claim history."""
    claims = _claims(bundle)
    subrogations = [evaluate_subrogation(c) for c in claims]
    salvages = [evaluate_salvage(c) for c in claims]
    return {
        "claim_count": len(claims),
        "subrogation_potential": round(sum(s.potential_recovery for s in subrogations), 2),
        "subrogation_recovered": round(sum(s.recovery_amount for s in subrogations), 2),
        "subrogation_pursued": sum(1 for s in subrogations if s.status in (SubrogationStatus.PURSUED, SubrogationStatus.RECOVERED)),
        "salvage_value": round(sum(s.salvage_value for s in salvages), 2),
        "salvage_offset": round(sum(s.offset_amount for s in salvages), 2),
        "subrogations": [s.model_dump() for s in subrogations if s.status != SubrogationStatus.NOT_PURSUED],
        "salvages": [s.model_dump() for s in salvages if s.salvage_value > 0],
    }


# ──────────────────────────────────────────────────────────────────────────
# Defense counsel & indemnity-vs-liability
# ──────────────────────────────────────────────────────────────────────────
def defense_cost_assessment(
    claims: Iterable[ClaimRecord],
    *,
    policy_limit: float = 0.0,
    defense_in_addition_to_limits: bool = True,
) -> dict[str, Any]:
    """Defense costs handled inside or outside the policy limits."""
    claims = list(claims)
    defense_total = sum(float(getattr(c, "defense_cost", 0.0) or 0.0) for c in claims)
    limit = max(float(policy_limit or 0.0), 0.0)
    if not defense_in_addition_to_limits and limit > 0:
        erosion = defense_total / limit if limit > 0 else 0.0
        remaining = max(limit - defense_total, 0.0)
        return {
            "defense_total": round(defense_total, 2),
            "defense_in_addition_to_limits": False,
            "limit_erosion_pct": round(min(erosion, 1.0), 4),
            "remaining_indemnity_capacity": round(remaining, 2),
            "detail": f"Defense within limits — {defense_total:,.0f} of {limit:,.0f} eroded ({min(erosion, 1.0):.1%}); {remaining:,.0f} left for indemnity",
        }
    return {
        "defense_total": round(defense_total, 2),
        "defense_in_addition_to_limits": True,
        "limit_erosion_pct": 0.0,
        "remaining_indemnity_capacity": limit,
        "detail": "Defense costs are in addition to the limits — indemnity capacity is intact",
    }


def indemnity_valuation(
    *,
    replacement_cost: float,
    depreciation_pct: float = 0.0,
    policy_limit: float = 0.0,
    basis: str = "rcv",
) -> dict[str, Any]:
    """Valuation basis: replacement cost vs actual cash value (replacement − depreciation).

    Indemnity pays the lower of the value of the loss and the policy limit.
    """
    rcv = max(float(replacement_cost or 0.0), 0.0)
    dep = max(min(float(depreciation_pct or 0.0), 1.0), 0.0)
    limit = max(float(policy_limit or 0.0), 0.0)
    acv = rcv * (1.0 - dep)
    if basis == "acv":
        value = acv
        label = "actual cash value"
    elif basis == "agreed_value":
        value = limit if limit > 0 else rcv
        label = "agreed value"
    else:
        value = rcv
        label = "replacement cost"
    indemnity = min(value, limit) if limit > 0 else value
    return {
        "basis": label,
        "replacement_cost": round(rcv, 2),
        "depreciation_pct": round(dep, 4),
        "acv": round(acv, 2),
        "indemnity_amount": round(indemnity, 2),
        "policy_limit": limit,
        "detail": f"Indemnity {indemnity:,.0f} = min({label} {value:,.0f}, limit {limit:,.0f})",
    }
