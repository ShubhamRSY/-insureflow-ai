"""Selection standards and book-balance underwriting model.

Implements the actuarial doctrine that an insurer must balance written volume
against risk homogeneity. With only a few policies the law of large numbers
does not yet operate, so loss experience is not predictable and selection
standards must stay strict. As the book grows and becomes more homogeneous the
loss ratio becomes predictable enough that standards can be relaxed in exchange
for volume, and substandard risks are admitted only when their higher premium
loadings offset their higher expected loss ratio.

Selection expense matters on both sides: strict selection (APS, paramedical
exams, deep loss-run review) costs money per risk, so a thin book or small
premium can be overwhelmed by underwriting cost; broad selection cheapens
acquisition but admits risk that a small book cannot absorb.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Sequence

from pydantic import BaseModel, Field

from insureflow.models.agents import UWDecision


class RiskClass(str, Enum):
    PREFERRED = "preferred"
    STANDARD = "standard"
    SUBSTANDARD = "substandard"


class SelectionTier(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    BROAD = "broad"


_RISK_RANK = {
    RiskClass.PREFERRED: 0,
    RiskClass.STANDARD: 1,
    RiskClass.SUBSTANDARD: 2,
}

_TIER_MAX_RANK = {
    SelectionTier.STRICT: 1,  # preferred / standard only
    SelectionTier.BALANCED: 2,  # substandard admitted with loading + evidence
    SelectionTier.BROAD: 2,  # substandard admitted on rate alone
}


class SelectionStandardsConfig(BaseModel):
    """Tunable thresholds for the book-balance model."""

    reference_size: float = 40.0
    cv_cap: float = 1.5
    strict_threshold: float = 0.30
    balanced_threshold: float = 0.60
    strict_expense_per_risk: float = 450.0
    balanced_expense_per_risk: float = 250.0
    broad_expense_per_risk: float = 120.0
    max_selection_expense_ratio: float = 0.05
    max_candidate_expense_ratio: float = 0.30
    min_volume_for_law_of_averages: int = 15
    target_size: int = 100
    min_substandard_loading: float = 15.0
    max_substandard_loading: float = 50.0
    max_intra_class_cv: float = 0.15

    def expense_per_risk(self, tier: SelectionTier) -> float:
        return {
            SelectionTier.STRICT: self.strict_expense_per_risk,
            SelectionTier.BALANCED: self.balanced_expense_per_risk,
            SelectionTier.BROAD: self.broad_expense_per_risk,
        }[tier]


class SelectionCandidate(BaseModel):
    """The risk being underwritten against the current book posture."""

    tiv: float = 0.0
    premium: float = 0.0
    risk_class: RiskClass = RiskClass.STANDARD
    risk_score: float = 0.5  # 0.0 = clean, 1.0 = hazardous
    occupancy_type: str = ""


class BookSnapshot(BaseModel):
    """Derived statistics describing the current written book."""

    policy_count: int = 0
    total_tiv: float = 0.0
    total_premium: float = 0.0
    mean_premium: float = 0.0
    cv_premium: float = 0.0
    cv_tiv: float = 0.0
    homogeneity: float = 0.0  # 0 = wildly mixed, 1 = uniform
    size_score: float = 0.0  # 0 = tiny, 1 = large enough for the law of averages
    predictability: float = 0.0  # blended, 0..1
    tier: SelectionTier = SelectionTier.STRICT
    intra_class_cv: float = 0.0  # spread of risk scores within each class
    class_dispersion: dict[str, float] = Field(default_factory=dict)  # per-class CV


class SelectionAssessment(BaseModel):
    """Outcome of gating a candidate against the current book posture."""

    book: BookSnapshot
    candidate: SelectionCandidate
    action: UWDecision = UWDecision.REFER
    predictability: float = 0.0
    selection_expense_usd: float = 0.0
    selection_expense_ratio: float = 0.0
    candidate_expense_usd: float = 0.0
    substandard_loading_pct: float = 0.0  # premium loading when substandard is admitted
    rationale: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def coefficient_of_variation(values: Sequence[float]) -> float:
    vals = [float(v) for v in values if v and v > 0]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    if mean <= 0:
        return 0.0
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(variance) / mean


def selection_tier_for(predictability: float, config: SelectionStandardsConfig | None = None) -> SelectionTier:
    cfg = config or SelectionStandardsConfig()
    if predictability < cfg.strict_threshold:
        return SelectionTier.STRICT
    if predictability < cfg.balanced_threshold:
        return SelectionTier.BALANCED
    return SelectionTier.BROAD


def class_for_score(risk_score: float) -> RiskClass:
    """Map a numeric risk score back to its underwriting class band."""
    if risk_score < 0.4:
        return RiskClass.PREFERRED
    if risk_score < 0.65:
        return RiskClass.STANDARD
    return RiskClass.SUBSTANDARD


def _class_dispersion(risk_scores: Sequence[float]) -> tuple[float, dict[str, float]]:
    """Within-class spread of risk scores: good and poor risks in the same band.

    Returns (max CV across classes, per-class CV). The text warns that even
    within a class there are good risks and poor risks relative to the rest of
    the class; high dispersion means some weak risks are riding on the class
    average rate.
    """
    bands: dict[str, list[float]] = {}
    for score in risk_scores:
        bands.setdefault(class_for_score(score).value, []).append(float(score))
    per_class: dict[str, float] = {}
    max_cv = 0.0
    for class_name, scores in sorted(bands.items()):
        cv = coefficient_of_variation(scores)
        per_class[class_name] = round(cv, 4)
        max_cv = max(max_cv, cv)
    return round(max_cv, 4), per_class


def build_book_snapshot(
    policy_count: int,
    total_tiv: float,
    total_premium: float,
    premiums: Sequence[float],
    tivs: Sequence[float],
    config: SelectionStandardsConfig | None = None,
    risk_scores: Sequence[float] = (),
) -> BookSnapshot:
    """Compute homogeneity, size and predictability for a written book."""
    cfg = config or SelectionStandardsConfig()

    cv_premium = coefficient_of_variation(premiums)
    cv_tiv = coefficient_of_variation(tivs)

    avg_cv = 0.5 * (cv_premium + cv_tiv)
    homogeneity = max(0.0, 1.0 - min(avg_cv, cfg.cv_cap) / cfg.cv_cap)
    size_score = 1.0 - math.exp(-policy_count / cfg.reference_size)
    # Predictability is fundamentally bounded by volume: a tiny book is not
    # predictable no matter how uniform it is, so homogeneity only scales the
    # size-driven ceiling rather than adding to it.
    predictability = size_score * (0.5 + 0.5 * homogeneity)

    intra_class_cv, class_dispersion = _class_dispersion(risk_scores)

    return BookSnapshot(
        policy_count=policy_count,
        total_tiv=total_tiv,
        total_premium=total_premium,
        mean_premium=(total_premium / policy_count) if policy_count else 0.0,
        cv_premium=round(cv_premium, 4),
        cv_tiv=round(cv_tiv, 4),
        homogeneity=round(homogeneity, 4),
        size_score=round(size_score, 4),
        predictability=round(min(1.0, predictability), 4),
        tier=selection_tier_for(predictability, cfg),
        intra_class_cv=intra_class_cv,
        class_dispersion=class_dispersion,
    )


def assess_selection(
    candidate: SelectionCandidate,
    book: BookSnapshot,
    config: SelectionStandardsConfig | None = None,
) -> SelectionAssessment:
    """Gate a candidate risk against the current book posture.

    A small or heterogeneous book keeps selection standards strict, so only
    preferred/standard risks are admitted and substandard risks are referred or
    declined. A large homogeneous book relaxes the gate and lets substandard
    risks in on loading. Selection expense is also priced: strict evidence
    gathering must not eat a disproportionate share of the written premium.
    """
    cfg = config or SelectionStandardsConfig()
    tier = book.tier
    candidate_rank = _RISK_RANK[candidate.risk_class]
    tier_rank = _TIER_MAX_RANK[tier]

    cost_per_risk = cfg.expense_per_risk(tier)
    expense_usd = cost_per_risk * max(book.policy_count, 1)
    expense_ratio = expense_usd / book.total_premium if book.total_premium > 0 else 0.0
    candidate_expense = cost_per_risk
    candidate_expense_ratio = candidate_expense / candidate.premium if candidate.premium > 0 else 0.0

    rationale: list[str] = []
    warnings: list[str] = []

    if book.policy_count < cfg.min_volume_for_law_of_averages:
        warnings.append(f"Book has only {book.policy_count} policies — too few for the law of averages to make losses predictable; keep selection standards strict until volume grows.")
    if book.homogeneity < 0.5:
        warnings.append(f"Book is heterogeneous (homogeneity {book.homogeneity:.0%}, premium CV {book.cv_premium:.2f}) — mixed classes impair loss predictability.")
    if book.intra_class_cv > cfg.max_intra_class_cv:
        warnings.append(
            f"Intra-class dispersion is {book.intra_class_cv:.2f} (per class: "
            f"{', '.join(f'{k}={v:.2f}' for k, v in book.class_dispersion.items())}) — "
            "good and poor risks are pooled in the same class; weak risks are riding on "
            "the class average rate."
        )
    if expense_ratio > cfg.max_selection_expense_ratio:
        warnings.append(f"Selection expense is {expense_ratio:.1%} of book premium (${expense_usd:,.0f} on {book.policy_count} risks) — strict evidence requirements are eroding margin.")

    if candidate_rank > tier_rank:
        action, rationale = _reject_for_tier(candidate, tier)
    elif candidate.risk_class == RiskClass.SUBSTANDARD and tier == SelectionTier.BALANCED:
        action = UWDecision.CONDITIONAL_ACCEPT
        rationale = [
            "Balanced book can absorb a substandard risk only with loading and evidence requirements — conditional acceptance.",
        ]
    elif candidate.risk_score >= 0.85:
        action = UWDecision.REFER
        rationale.append(f"Risk score {candidate.risk_score:.2f} exceeds the {tier.value}-standards acceptance band even though the class is admissible.")
    else:
        action = UWDecision.ACCEPT
        rationale.append(f"Candidate {candidate.risk_class.value} fits {tier.value} selection standards (book predictability {book.predictability:.0%}).")

    substandard_loading_pct = 0.0
    if candidate.risk_class == RiskClass.SUBSTANDARD and action in (UWDecision.ACCEPT, UWDecision.CONDITIONAL_ACCEPT):
        loading = (candidate.risk_score - 0.5) * 100.0
        substandard_loading_pct = round(min(max(loading, cfg.min_substandard_loading), cfg.max_substandard_loading), 1)

    if candidate.risk_class == RiskClass.SUBSTANDARD and action != UWDecision.DECLINE:
        if substandard_loading_pct > 0:
            rationale.append(f"Substandard risk carries a {substandard_loading_pct:.0f}% premium loading; monitor class loss ratio.")
        else:
            rationale.append("Substandard risk carries a premium loading; monitor class loss ratio.")
        if action == UWDecision.CONDITIONAL_ACCEPT:
            rationale.append("Require evidence (APS / loss-run) and substandard rate before binding.")

    if candidate.premium > 0 and candidate_expense_ratio > cfg.max_candidate_expense_ratio:
        warnings.append(f"Selection cost (${candidate_expense:,.0f}) is {candidate_expense_ratio:.1%} of the candidate premium (${candidate.premium:,.0f}) — evidence cost may exceed the margin.")

    return SelectionAssessment(
        book=book,
        candidate=candidate,
        action=action,
        predictability=book.predictability,
        selection_expense_usd=round(expense_usd, 2),
        selection_expense_ratio=round(expense_ratio, 4),
        candidate_expense_usd=round(candidate_expense, 2),
        substandard_loading_pct=substandard_loading_pct,
        rationale=rationale,
        warnings=warnings,
    )


def _reject_for_tier(candidate: SelectionCandidate, tier: SelectionTier) -> tuple[UWDecision, list[str]]:
    if tier == SelectionTier.STRICT:
        if candidate.risk_score >= 0.7:
            return UWDecision.DECLINE, [
                f"Strict selection standards admit only preferred/standard risks; "
                f"substandard class with risk score {candidate.risk_score:.2f} is beyond the "
                "book's ability to absorb — decline rather than dilute the class."
            ]
        return UWDecision.REFER, ["Strict selection standards admit only preferred/standard risks; substandard candidate requires referral to licensed UW before acceptance."]
    return UWDecision.CONDITIONAL_ACCEPT, [
        "Balanced book can absorb a substandard risk only with loading and evidence requirements — conditional acceptance.",
    ]
