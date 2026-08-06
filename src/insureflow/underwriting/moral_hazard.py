"""Moral-hazard / character screen — the doctrine of the underwriter as a judge of people.

The underwriter must be a skillful judge of the applicant in every instance:
if the applicant's morals are open to question the underwriter will decline the
insurance, no matter how sound the property or how healthy the life. Character
signals are distinct from loss-frequency/severity and from hard fraud evidence;
they describe how honestly and carefully the applicant behaves as a counter-
party. An applicant who misrepresents, shops immediately after a loss, files a
claim days after inception, was cancelled by a prior carrier, or is under
financial distress is disproportionately likely to behave badly after binding.

This module implements a deterministic screen for those character signals:

* ``intentional_misrepresentation`` — the loss run itself notes the applicant
  did not disclose a claim, or a claim's cause reads as intentional/fraudulent
  arson. Any of these marks the applicant's morals as open to question and
  drives the screen to ``critical`` (declination).
* ``non_disclosed_losses`` — claims in the loss run that never appear in the
  structured submission. The applicant may have hidden losses.
* ``prior_cancellation`` — the applicant was cancelled or non-renewed by a
  prior carrier, a documented history of bad faith or mismanagement.
* ``financial_distress`` — bankruptcy, liens, judgments, foreclosure and other
  markers that raise the temptation to burn or inflate a loss.
* ``suspicious_claim_timing`` — claims filed soon after the coverage effective
  date (staged-loss pattern) or on the eve of the application.
* ``suspicious_claim_cause`` — causes like arson/incendiary/staged loss.
* ``entity_churn`` — reincorporation, dissolution, frequent name changes or
  successor entities that obscure the applicant's true track record.

Signal contributions are additive (capped at 1.0). Status is ``critical`` when
any signal is critical, ``high`` when a high-severity signal fires or the
score reaches the high threshold, ``flagged`` below it, and ``low`` when no
signal fires at all.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from insureflow.models.agents import RiskSeverity
from insureflow.models.submissions import ClaimRecord, SubmissionBundle

# Claim-cause/notes markers that read as intentional or staged losses.
_SUSPICIOUS_CAUSE_KEYWORDS = (
    "arson",
    "incendiary",
    "suspicious",
    "intentional",
    "staged",
    "self-inflicted",
    "self inflicted",
    "fraudulent",
)

# Document markers that an applicant's candor has already failed the test.
_INTENTIONAL_MISREPRESENTATION_MARKERS = (
    "not disclosed",
    "misrepresent",
    "intentionally omitted",
    "falsified",
    "concealed",
)

# Document markers of a prior carrier relationship ended for cause.
_CANCELLATION_MARKERS = (
    "cancelled",
    "canceled",
    "non-renewed",
    "nonrenewed",
    "non renewed",
    "declined for cause",
    "prior carrier",
    "dropped by",
    "terminated by the carrier",
    "cancellation for cause",
)

# Financial-distress markers that elevate the incentive to manufacture a loss.
_BANKRUPTCY_MARKERS = ("bankrupt", "chapter 11", "chapter 7", "chapter 13", "insolven")
_DISTRESS_MARKERS = (
    "lien",
    "judgment",
    "foreclosure",
    "collections",
    "wage garnishment",
    "garnishment",
    "bad debt",
    "receivership",
    "defaulted on",
)

# Entity churn / track-record-obscuring markers.
_ENTITY_CHURN_MARKERS = (
    "reorganized",
    "reorganization",
    "formerly known as",
    "successor in interest",
    "newly incorporated",
    "amended and restated",
    "dissolved",
    "wound up",
    "new entity",
    "name change",
    "restructured",
)


class MoralHazardSignalType(str, Enum):
    INTENTIONAL_MISREPRESENTATION = "intentional_misrepresentation"
    NON_DISCLOSED_LOSSES = "non_disclosed_losses"
    PRIOR_CANCELLATION = "prior_cancellation"
    FINANCIAL_DISTRESS = "financial_distress"
    SUSPICIOUS_CLAIM_TIMING = "suspicious_claim_timing"
    SUSPICIOUS_CLAIM_CAUSE = "suspicious_claim_cause"
    ENTITY_CHURN = "entity_churn"


class MoralHazardConfig(BaseModel):
    """Tunable thresholds for the moral-hazard / character screen."""

    intentional_misrepresentation_contribution: float = 1.0
    non_disclosed_contribution: float = 0.70
    prior_cancellation_contribution: float = 0.65
    bankruptcy_contribution: float = 0.65
    financial_distress_contribution: float = 0.40
    suspicious_timing_contribution: float = 0.45
    suspicious_timing_high_days: int = 30
    suspicious_timing_days: int = 120
    suspicious_cause_contribution: float = 1.0
    entity_churn_contribution: float = 0.35
    high_threshold: float = 0.60


class MoralHazardSignal(BaseModel):
    signal_type: MoralHazardSignalType
    detail: str
    contribution: float
    severity: RiskSeverity = RiskSeverity.MODERATE
    evidence: list[str] = Field(default_factory=list)


class MoralHazardAssessment(BaseModel):
    """The character posture of a single applicant.

    ``moral_hazard_score`` is the additive (capped at 1.0) sum of the detected
    character signals. ``status`` is ``critical`` when any signal is critical
    (morals open to question — decline), ``high`` when a high signal fires or
    the score reaches the high threshold, ``flagged`` below it, and ``low``
    when nothing points at a character concern.
    """

    applicant_name: str = ""
    signals: list[MoralHazardSignal] = Field(default_factory=list)
    moral_hazard_score: float = 0.0
    status: str = "low"

    @property
    def signal_types(self) -> list[str]:
        return [s.signal_type.value for s in self.signals]


def _document_text(bundle: SubmissionBundle) -> list[str]:
    texts: list[str] = []
    if bundle.structured:
        if bundle.structured.raw_xml:
            texts.append(bundle.structured.raw_xml)
        if bundle.structured.raw_json:
            texts.append(bundle.structured.raw_json)
    for doc in (bundle.unstructured or []) + (bundle.supplemental or []):
        texts.append(doc.raw_text)
    return texts


def _claims(bundle: SubmissionBundle) -> list[ClaimRecord]:
    structured = bundle.structured
    if structured is None:
        return []
    claims: list[ClaimRecord] = []
    if structured.financial and structured.financial.loss_run:
        claims.extend(structured.financial.loss_run.claims or [])
    if structured.risk_profile:
        claims.extend(structured.risk_profile.prior_claims or [])
    return claims


def _effective_date(bundle: SubmissionBundle) -> date | None:
    if bundle.structured and bundle.structured.policy_period:
        return bundle.structured.policy_period.effective_date
    return None


def _match_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [m for m in markers if m in lowered]


def _non_disclosed_claims(bundle: SubmissionBundle) -> list[ClaimRecord]:
    structured = bundle.structured
    if structured is None or structured.financial is None or structured.financial.loss_run is None:
        return []
    structured_ids = {c.get("claim_id", "") for c in (structured.financial.prior_losses or [])}
    return [c for c in structured.financial.loss_run.claims if c.claim_id not in structured_ids]


def _claim_blob(claim: ClaimRecord) -> str:
    return f"{claim.cause} {claim.description} {claim.notes}".lower()


def assess_moral_hazard(
    bundle: SubmissionBundle,
    config: MoralHazardConfig | None = None,
) -> MoralHazardAssessment:
    """Screen a submission for character / moral-hazard signals.

    The screen is a pure function of the submission: it reads only the data
    already present on the bundle, so tests can inject any combination of
    claims, documents, and entity markers directly.
    """
    cfg = config or MoralHazardConfig()
    structured = bundle.structured
    applicant = (structured.named_insured.legal_name if structured and structured.named_insured else "") or ""

    signals: list[MoralHazardSignal] = []

    # 1. Intentional misrepresentation — the applicant's own candor has failed.
    for claim in _claims(bundle):
        blob = _claim_blob(claim)
        if any(m in blob for m in _INTENTIONAL_MISREPRESENTATION_MARKERS):
            signals.append(
                MoralHazardSignal(
                    signal_type=MoralHazardSignalType.INTENTIONAL_MISREPRESENTATION,
                    detail=f"Loss-run notes for {claim.claim_id} indicate the applicant misrepresented or concealed information — candor is the foundation of the insurance contract.",
                    contribution=cfg.intentional_misrepresentation_contribution,
                    severity=RiskSeverity.CRITICAL,
                    evidence=[claim.cause, claim.notes, claim.description],
                )
            )
            break

    # 2. Non-disclosed losses — claims hidden from the structured submission.
    non_disclosed = _non_disclosed_claims(bundle)
    if non_disclosed:
        signals.append(
            MoralHazardSignal(
                signal_type=MoralHazardSignalType.NON_DISCLOSED_LOSSES,
                detail=f"{len(non_disclosed)} claim(s) appear in the loss run but not in the disclosed submission — the applicant may have hidden losses.",
                contribution=cfg.non_disclosed_contribution,
                severity=RiskSeverity.HIGH,
                evidence=[f"{c.claim_id}: ${c.incurred_amount:,.0f} ({c.date_of_loss})" for c in non_disclosed],
            )
        )

    # 3. Prior carrier cancellation / non-renewal — a history ended for cause.
    cancellation_hits: list[str] = []
    for text in _document_text(bundle):
        cancellation_hits.extend(_match_markers(text, _CANCELLATION_MARKERS))
    if cancellation_hits:
        unique = list(dict.fromkeys(cancellation_hits))
        signals.append(
            MoralHazardSignal(
                signal_type=MoralHazardSignalType.PRIOR_CANCELLATION,
                detail="The submission references a prior carrier cancellation or non-renewal — a documented history of the applicant being declined or terminated.",
                contribution=cfg.prior_cancellation_contribution,
                severity=RiskSeverity.HIGH,
                evidence=[f"marker: {m}" for m in unique],
            )
        )

    # 4. Financial distress — temptation to manufacture or inflate a loss.
    bankruptcy_hits: list[str] = []
    distress_hits: list[str] = []
    for text in _document_text(bundle):
        bankruptcy_hits.extend(_match_markers(text, _BANKRUPTCY_MARKERS))
        distress_hits.extend(_match_markers(text, _DISTRESS_MARKERS))
    credit_rating = ""
    if structured and structured.financial:
        credit_rating = (structured.financial.credit_rating or "").lower()
    if bankruptcy_hits or credit_rating in ("d", "f", "poor", "subprime"):
        evidence = [f"marker: {m}" for m in dict.fromkeys(bankruptcy_hits)]
        if credit_rating:
            evidence.append(f"credit rating: {credit_rating}")
        signals.append(
            MoralHazardSignal(
                signal_type=MoralHazardSignalType.FINANCIAL_DISTRESS,
                detail="The applicant shows signs of financial distress (bankruptcy/insolvency) — a well-documented moral-hazard driver that raises the incentive to burn or inflate a loss.",
                contribution=cfg.bankruptcy_contribution,
                severity=RiskSeverity.HIGH,
                evidence=evidence,
            )
        )
    elif distress_hits:
        signals.append(
            MoralHazardSignal(
                signal_type=MoralHazardSignalType.FINANCIAL_DISTRESS,
                detail="The applicant shows financial-distress markers (liens, judgments, collections) that elevate moral hazard.",
                contribution=cfg.financial_distress_contribution,
                severity=RiskSeverity.MODERATE,
                evidence=[f"marker: {m}" for m in dict.fromkeys(distress_hits)],
            )
        )

    # 5. Suspicious claim timing — claims filed right after inception.
    effective_date = _effective_date(bundle)
    if effective_date is not None:
        recent_claims = [c for c in _claims(bundle) if c.date_of_loss >= effective_date]
        high = [c for c in recent_claims if (c.date_of_loss - effective_date).days <= cfg.suspicious_timing_high_days]
        within = [c for c in recent_claims if (c.date_of_loss - effective_date).days <= cfg.suspicious_timing_days]
        if high:
            evidence = [f"{c.claim_id}: loss {c.date_of_loss} within {cfg.suspicious_timing_high_days} days of inception {effective_date}" for c in high]
            signals.append(
                MoralHazardSignal(
                    signal_type=MoralHazardSignalType.SUSPICIOUS_CLAIM_TIMING,
                    detail=f"{len(high)} claim(s) filed within {cfg.suspicious_timing_high_days} days of the coverage effective date — a staged-loss pattern that questions the applicant's integrity.",
                    contribution=cfg.suspicious_timing_contribution,
                    severity=RiskSeverity.HIGH,
                    evidence=evidence,
                )
            )
        elif within:
            evidence = [f"{c.claim_id}: loss {c.date_of_loss} within {cfg.suspicious_timing_days} days of inception {effective_date}" for c in within]
            signals.append(
                MoralHazardSignal(
                    signal_type=MoralHazardSignalType.SUSPICIOUS_CLAIM_TIMING,
                    detail=f"{len(within)} claim(s) filed shortly after the coverage effective date — claims so soon after inception warrant character scrutiny.",
                    contribution=cfg.suspicious_timing_contribution,
                    severity=RiskSeverity.MODERATE,
                    evidence=evidence,
                )
            )

    # 6. Suspicious claim cause — arson, incendiary, staged loss.
    for claim in _claims(bundle):
        hits = _match_markers(_claim_blob(claim), _SUSPICIOUS_CAUSE_KEYWORDS)
        if hits:
            signals.append(
                MoralHazardSignal(
                    signal_type=MoralHazardSignalType.SUSPICIOUS_CLAIM_CAUSE,
                    detail=(
                        f"Claim {claim.claim_id} carries a cause consistent with an intentional or "
                        f"staged loss ({', '.join(hits)}) — if the morals of the applicant are open "
                        "to question the policy is declined."
                    ),
                    contribution=cfg.suspicious_cause_contribution,
                    severity=RiskSeverity.CRITICAL,
                    evidence=[claim.cause, claim.notes, f"Incurred: ${claim.incurred_amount:,.0f}"],
                )
            )
            break

    # 7. Entity churn — track record obscured by reorganizations.
    churn_hits: list[str] = []
    for text in _document_text(bundle):
        churn_hits.extend(_match_markers(text, _ENTITY_CHURN_MARKERS))
    if churn_hits:
        signals.append(
            MoralHazardSignal(
                signal_type=MoralHazardSignalType.ENTITY_CHURN,
                detail="The applicant's documents show reorganization, dissolution, or successor entities — a churned track record that may be obscuring prior losses or cancellations.",
                contribution=cfg.entity_churn_contribution,
                severity=RiskSeverity.MODERATE,
                evidence=[f"marker: {m}" for m in dict.fromkeys(churn_hits)],
            )
        )

    score = min(1.0, sum(s.contribution for s in signals))
    if any(s.severity == RiskSeverity.CRITICAL for s in signals):
        status = "critical"
    elif any(s.severity == RiskSeverity.HIGH for s in signals) or score >= cfg.high_threshold:
        status = "high"
    elif signals:
        status = "flagged"
    else:
        status = "low"

    return MoralHazardAssessment(
        applicant_name=applicant,
        signals=signals,
        moral_hazard_score=round(score, 4),
        status=status,
    )
