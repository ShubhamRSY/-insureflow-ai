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

The model is closed with an experience-rating feedback loop: each class's
realized loss ratio (incurred losses vs earned premium, blended toward the
expected loss ratio by limited-fluctuation credibility) is compared with what
rating assumed. Worse-than-expected experience tightens selection thresholds
and scales substandard loadings upward; better-than-expected experience relaxes
them. The loop trusts a class only as its volume converges on the law of large
numbers, so a thin book's volatile loss ratio cannot swing standards.
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
    # Experience-rating feedback loop
    expected_loss_ratio_by_class: dict[str, float] = Field(
        default_factory=lambda: {
            RiskClass.PREFERRED.value: 0.45,
            RiskClass.STANDARD.value: 0.60,
            RiskClass.SUBSTANDARD.value: 0.70,
        }
    )
    credibility_full_policies: float = 30.0  # N policies → full credibility (Z = sqrt(N/30))
    min_observed_policies_for_feedback: int = 5
    experience_threshold_sensitivity: float = 0.5  # penalty 1.0±0.2 → ±0.10 threshold shift
    min_producer_credibility_for_tip: float = 0.5  # producer book must be ≥ this credible to tip a marginal exposure
    producer_accept_upgrade_max_score: float = 0.85  # better-producer admission cap for a referred substandard risk

    def expense_per_risk(self, tier: SelectionTier) -> float:
        return {
            SelectionTier.STRICT: self.strict_expense_per_risk,
            SelectionTier.BALANCED: self.balanced_expense_per_risk,
            SelectionTier.BROAD: self.broad_expense_per_risk,
        }[tier]


class ClassExperience(BaseModel):
    """Realized vs expected loss experience for a single underwriting class."""

    class_name: str
    policy_count: int = 0
    earned_premium: float = 0.0
    incurred_loss: float = 0.0
    loss_ratio: float = 0.0
    expected_loss_ratio: float = 0.0
    credibility: float = 0.0  # 0 = too few risks to trust, 1 = fully credible
    penalty_factor: float = 1.0  # > 1 = worse than rating assumed


class BookExperience(BaseModel):
    """Book-wide realized vs expected loss experience (the feedback loop).

    ``penalty_factor`` is the premium-weighted blend of the per-class penalty
    factors (each already credibility-scaled), so a thin class's noisy loss
    ratio cannot distort the book posture.
    """

    policy_count: int = 0
    earned_premium: float = 0.0
    incurred_loss: float = 0.0
    loss_ratio: float = 0.0
    expected_loss_ratio: float = 0.0
    credibility: float = 0.0
    penalty_factor: float = 1.0
    status: str = "unknown"  # unknown | better | expected | worse
    classes: dict[str, ClassExperience] = Field(default_factory=dict)


class ProducerExperience(BaseModel):
    """Realized vs expected loss experience for one producing agent/broker.

    The doctrine's financial function notes the producer is judged on volume
    while the underwriter is judged on quality, so the insurer monitors each
    producer's book: a producer whose submissions consistently run
    above-average claims is a relationship risk. ``penalty_factor`` is the
    credibility-blended deviation of the producer's realized loss ratio from the
    premium-weighted expectation of the classes they submitted.
    """

    producer_name: str
    policy_count: int = 0
    earned_premium: float = 0.0
    incurred_loss: float = 0.0
    loss_ratio: float = 0.0
    expected_loss_ratio: float = 0.0
    credibility: float = 0.0
    penalty_factor: float = 1.0
    status: str = "unknown"  # unknown | better | expected | worse


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
    experience: BookExperience | None = None  # realized-vs-expected feedback in effect
    producer_experience: ProducerExperience | None = None  # the submitting agent's realized-vs-expected book
    producer_tipped: bool = False  # producer track record changed the decision or the loading
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


def _credibility(policy_count: float, config: SelectionStandardsConfig) -> float:
    """Limited-fluctuation credibility: full at ``credibility_full_policies`` risks."""
    if policy_count <= 0:
        return 0.0
    return min(1.0, math.sqrt(policy_count / config.credibility_full_policies))


def _penalty(credibility: float, loss_ratio: float, expected_loss_ratio: float) -> float:
    """Penalty factor blending realized experience toward expectation by credibility."""
    if credibility <= 0 or expected_loss_ratio <= 0:
        return 1.0
    return min(max(1.0 + credibility * (loss_ratio / expected_loss_ratio - 1.0), 0.6), 1.6)


def compute_book_experience(
    premiums: Sequence[float],
    incurred_losses: Sequence[float],
    risk_scores: Sequence[float],
    config: SelectionStandardsConfig | None = None,
) -> BookExperience:
    """Compare realized loss experience against rating's expectation per class.

    Only policies whose losses have actually been reported belong in this call
    (``PortfolioPolicy.loss_data_available``); an empty or sub-threshold book
    returns an ``unknown`` experience with credibility 0 and penalty 1.0 so the
    loop is inert until there is data to trust.
    """
    cfg = config or SelectionStandardsConfig()

    buckets: dict[str, list[float]] = {}
    for premium, loss, score in zip(premiums, incurred_losses, risk_scores):
        class_name = class_for_score(score).value
        bucket = buckets.setdefault(class_name, [0.0, 0.0, 0.0])
        bucket[0] += float(premium)
        bucket[1] += float(loss)
        bucket[2] += 1.0

    if not buckets:
        return BookExperience(policy_count=0, status="unknown")

    classes: dict[str, ClassExperience] = {}
    credible_penalties: list[tuple[float, float]] = []  # (penalty_factor, premium)
    observed_premium = 0.0
    observed_loss = 0.0
    observed_count = 0
    expected_premium = 0.0

    for class_name, (premium, loss, count) in sorted(buckets.items()):
        expected = cfg.expected_loss_ratio_by_class.get(class_name, 0.6)
        loss_ratio = loss / premium if premium > 0 else 0.0
        cred = _credibility(count, cfg) if count >= cfg.min_observed_policies_for_feedback else 0.0
        penalty = _penalty(cred, loss_ratio, expected)
        classes[class_name] = ClassExperience(
            class_name=class_name,
            policy_count=int(count),
            earned_premium=round(premium, 2),
            incurred_loss=round(loss, 2),
            loss_ratio=round(loss_ratio, 4),
            expected_loss_ratio=expected,
            credibility=round(cred, 4),
            penalty_factor=round(penalty, 4),
        )
        observed_premium += premium
        observed_loss += loss
        observed_count += int(count)
        expected_premium += expected * premium
        if cred > 0:
            credible_penalties.append((penalty, premium))

    book_penalty = 1.0
    if credible_penalties:
        total_weight = sum(w for _, w in credible_penalties)
        book_penalty = sum(p * w for p, w in credible_penalties) / total_weight if total_weight else 1.0

    book_credibility = _credibility(observed_count, cfg)
    if not credible_penalties:
        status = "unknown"
    elif book_penalty >= 1.05:
        status = "worse"
    elif book_penalty <= 0.95:
        status = "better"
    else:
        status = "expected"

    return BookExperience(
        policy_count=observed_count,
        earned_premium=round(observed_premium, 2),
        incurred_loss=round(observed_loss, 2),
        loss_ratio=round(observed_loss / observed_premium, 4) if observed_premium else 0.0,
        expected_loss_ratio=round(expected_premium / observed_premium, 4) if observed_premium else 0.0,
        credibility=round(book_credibility, 4),
        penalty_factor=round(book_penalty, 4),
        status=status,
        classes=classes,
    )


def compute_producer_experience(
    producers: Sequence[str],
    premiums: Sequence[float],
    incurred_losses: Sequence[float],
    risk_scores: Sequence[float],
    config: SelectionStandardsConfig | None = None,
) -> dict[str, ProducerExperience]:
    """Realized vs expected loss experience per producing agent/broker.

    Each policy's expectation is the expected loss ratio of the class it was
    underwritten into (``expected_loss_ratio_by_class``), premium-weighted across
    the producer's book. Only policies whose losses have actually been reported
    belong here; a producer with no reported experience is absent from the
    result, and one below ``min_observed_policies_for_feedback`` is not trusted.
    """
    cfg = config or SelectionStandardsConfig()

    buckets: dict[str, list[float]] = {}
    for producer, premium, loss, score in zip(producers, premiums, incurred_losses, risk_scores):
        if not producer:
            continue
        bucket = buckets.setdefault(producer, [0.0, 0.0, 0.0, 0.0])
        expected = cfg.expected_loss_ratio_by_class.get(class_for_score(score).value, 0.6)
        bucket[0] += float(premium)
        bucket[1] += float(loss)
        bucket[2] += 1.0
        bucket[3] += expected * float(premium)

    experiences: dict[str, ProducerExperience] = {}
    for producer, (premium, loss, count, expected_premium) in sorted(buckets.items()):
        expected = expected_premium / premium if premium > 0 else 0.0
        loss_ratio = loss / premium if premium > 0 else 0.0
        cred = _credibility(count, cfg) if count >= cfg.min_observed_policies_for_feedback else 0.0
        penalty = _penalty(cred, loss_ratio, expected)
        if cred <= 0:
            status = "unknown"
        elif penalty >= 1.05:
            status = "worse"
        elif penalty <= 0.95:
            status = "better"
        else:
            status = "expected"
        experiences[producer] = ProducerExperience(
            producer_name=producer,
            policy_count=int(count),
            earned_premium=round(premium, 2),
            incurred_loss=round(loss, 2),
            loss_ratio=round(loss_ratio, 4),
            expected_loss_ratio=round(expected, 4),
            credibility=round(cred, 4),
            penalty_factor=round(penalty, 4),
            status=status,
        )
    return experiences


def apply_experience_to_config(
    config: SelectionStandardsConfig,
    experience: BookExperience,
) -> SelectionStandardsConfig:
    """Return an adjusted config reflecting realized book loss experience.

    Worse-than-expected experience (penalty > 1) tightens selection by raising
    the predictability thresholds needed to reach the relaxed tiers; better
    experience lowers them. The shift is credibility-scaled inside
    ``compute_book_experience`` and capped so tier ordering is preserved. With
    no trustworthy data the config is returned unchanged.
    """
    if experience.credibility <= 0 or experience.penalty_factor == 1.0:
        return config
    shift = (experience.penalty_factor - 1.0) * config.experience_threshold_sensitivity
    strict_threshold = min(max(config.strict_threshold + shift, 0.05), config.balanced_threshold - 0.05)
    balanced_threshold = min(max(config.balanced_threshold + shift, config.strict_threshold + 0.05), 0.95)
    return config.model_copy(
        update={
            "strict_threshold": round(strict_threshold, 4),
            "balanced_threshold": round(balanced_threshold, 4),
        }
    )


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
    experience: BookExperience | None = None,
    producer_experience: ProducerExperience | None = None,
) -> SelectionAssessment:
    """Gate a candidate risk against the current book posture.

    A small or heterogeneous book keeps selection standards strict, so only
    preferred/standard risks are admitted and substandard risks are referred or
    declined. A large homogeneous book relaxes the gate and lets substandard
    risks in on loading. Selection expense is also priced: strict evidence
    gathering must not eat a disproportionate share of the written premium.

    When realized loss experience is supplied (the feedback loop), the
    candidate's class penalty factor scales its substandard loading: a class
    that has actually lost more than rating assumed is admitted only on a
    heavier loading, and a worse-than-expected class is flagged for tightening.

    When the submitting producer's realized-vs-expected loss experience is
    supplied, it closes the financial function's underwriter/agent balance: a
    credible producer with a better-than-expected book can tip a referred
    substandard exposure to conditional admission (and credits its loading); a
    producer whose book runs worse than expected tips an otherwise-admitted
    substandard exposure back to referral. This is the doctrine's rule that an
    agent's past performance may determine the acceptance of a marginally
    acceptable exposure.
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

    # The financial function: an underwriter is judged on quality while the
    # producing agent is paid on volume, and doctrine says the agent's past
    # performance may determine the acceptance of a marginally acceptable
    # (substandard) exposure. A credible producer with a better-than-expected
    # book can tip a referral to admission; one running worse than expected tips
    # an admitted substandard risk back to referral. The producer penalty is
    # already credibility-blended, so the tip only fires once enough of the
    # producer's book has been reported to trust.
    producer = producer_experience
    producer_tipped = False
    is_substandard = candidate.risk_class == RiskClass.SUBSTANDARD
    if producer is not None and is_substandard and producer.status in ("better", "worse") and producer.credibility >= cfg.min_producer_credibility_for_tip:
        if producer.status == "better":
            if action == UWDecision.REFER and candidate.risk_score < cfg.producer_accept_upgrade_max_score:
                action = UWDecision.CONDITIONAL_ACCEPT
                rationale.append(
                    f"Producer {producer.producer_name}'s book is losing {producer.loss_ratio:.0%} "
                    f"vs expected {producer.expected_loss_ratio:.0%} (credibility {producer.credibility:.0%}, "
                    f"{producer.policy_count} policies) — the producing agent's past performance tips this "
                    "marginally acceptable exposure to conditional admission."
                )
                producer_tipped = True
                if tier == SelectionTier.STRICT:
                    warnings.append(
                        "Producer track record overrode the strict-tier referral: this small book cannot yet "
                        "rely on the law of averages, and the substandard risk is being admitted on the "
                        "producing agent's experience rather than on book predictability — monitor closely."
                    )
        elif action in (UWDecision.ACCEPT, UWDecision.CONDITIONAL_ACCEPT):
            action = UWDecision.REFER
            rationale.append(
                f"Producer {producer.producer_name}'s book is losing {producer.loss_ratio:.0%} "
                f"vs expected {producer.expected_loss_ratio:.0%} (credibility {producer.credibility:.0%}, "
                f"{producer.policy_count} policies) — the producing agent's above-average claims tip this "
                "marginally acceptable exposure to referral rather than admission."
            )
            producer_tipped = True

    substandard_loading_pct = 0.0
    class_experience = None
    if experience is not None:
        class_experience = experience.classes.get(candidate.risk_class.value)
    if candidate.risk_class == RiskClass.SUBSTANDARD and action in (UWDecision.ACCEPT, UWDecision.CONDITIONAL_ACCEPT):
        loading = (candidate.risk_score - 0.5) * 100.0
        if class_experience is not None and class_experience.penalty_factor != 1.0:
            loading *= class_experience.penalty_factor
            rationale.append(
                f"Class {class_experience.class_name} realized loss ratio {class_experience.loss_ratio:.0%} "
                f"vs expected {class_experience.expected_loss_ratio:.0%} (credibility "
                f"{class_experience.credibility:.0%}) scales the base loading by "
                f"{class_experience.penalty_factor:.2f}."
            )
        if producer is not None and producer.status == "better" and producer.credibility >= cfg.min_producer_credibility_for_tip and producer.penalty_factor != 1.0:
            loading *= producer.penalty_factor
            rationale.append(
                f"Producer {producer.producer_name}'s better-than-expected book (loss ratio "
                f"{producer.loss_ratio:.0%} vs expected {producer.expected_loss_ratio:.0%}) credits the "
                f"loading by {producer.penalty_factor:.2f}."
            )
            producer_tipped = True
        substandard_loading_pct = round(min(max(loading, cfg.min_substandard_loading), cfg.max_substandard_loading), 1)

    if class_experience is not None and class_experience.penalty_factor > 1.0:
        warnings.append(
            f"Class {class_experience.class_name} is running {class_experience.loss_ratio:.0%} loss ratio "
            f"vs expected {class_experience.expected_loss_ratio:.0%} (penalty "
            f"{class_experience.penalty_factor:.2f}) — realized experience is worse than rating assumed; "
            "tighten selection and reprice the class."
        )

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
        experience=experience,
        producer_experience=producer,
        producer_tipped=producer_tipped,
        rationale=rationale,
        warnings=warnings,
    )


def _reject_for_tier(candidate: SelectionCandidate, tier: SelectionTier) -> tuple[UWDecision, list[str]]:
    if tier == SelectionTier.STRICT:
        # Keep a buffer under "clearly beyond absorb" so borderline mid-0.6 scores
        # refer for UW review instead of hard-declining on empty/seed books.
        if candidate.risk_score >= 0.75:
            return UWDecision.DECLINE, [
                f"Strict selection standards admit only preferred/standard risks; "
                f"substandard class with risk score {candidate.risk_score:.2f} is beyond the "
                "book's ability to absorb — decline rather than dilute the class."
            ]
        return UWDecision.REFER, ["Strict selection standards admit only preferred/standard risks; substandard candidate requires referral to licensed UW before acceptance."]
    return UWDecision.CONDITIONAL_ACCEPT, [
        "Balanced book can absorb a substandard risk only with loading and evidence requirements — conditional acceptance.",
    ]
