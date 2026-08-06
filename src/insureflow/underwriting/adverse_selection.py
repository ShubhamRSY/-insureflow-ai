"""Adverse-selection underwriting screen — the purpose of underwriting doctrine.

Adverse selection is the structural fact that the individuals and businesses
with the greatest probability of loss are the ones most likely to purchase
insurance: flood-plain owners are far more interested in buying flood cover
than anyone else, and the applicant who has just paid a large claim is more
eager to buy a new policy than the applicant who has not. The insurer is not
interested in selling to applicants who expect frequent, severe losses, so the
underwriter's core job is to detect when an applicant is *disproportionately
motivated to buy* and to screen those applicants out or rate them up.

This module implements a deterministic screen for the applicant-side signals of
that disproportionate motivation:

* ``hazard_zone_demand`` — the exposure sits in a named hazard zone (flood
  plain, wildfire zone, coast) and the applicant asks for the exact cover that
  zone threatens (the doctrine's flood-plain example).
* ``excluded_zone_demand`` — the hazard is in a zone the carrier's appetite has
  already declined (coastal FL / TX, HI, CA wildfire), so the demand escalates
  from "verify and rate" to "decline or refer".
* ``loss_motivated_seeking`` — the applicant applies for a new policy with a
  prior claim history, especially shortly after a loss.
* ``bare_cat_cover`` — the applicant asks only for the high-loss, high-variance
  catastrophe perils rather than a broad program, i.e. buying the cover they
  expect to use.

Signal contributions are additive (capped at 1.0) so the screen's score rises
with how many loss-seeking patterns coincide.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from insureflow.models.submissions import ClaimRecord, SubmissionBundle
from insureflow.oracles.cat_model_client import CATExposureResult, CATModelResult

# Peril → CAT coverage keywords (matched against coverage type + endorsements).
_PERIL_COVERAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "flood": ("flood", "fema", "sfha"),
    "earthquake": ("earthquake", "quake", "seismic"),
    "wind": ("wind", "hurricane", "tornado", "cyclone", "storm"),
    "wildfire": ("wildfire", "brushfire", "ember"),
}


# Appetite-declined hazard zones (guideline APT-003): state/zip predicates.
def _in_excluded_zone(exposure: CATExposureResult) -> bool:
    zip_digits = "".join(ch for ch in (exposure.zip_code or "") if ch.isdigit())[:5]
    try:
        zip_int = int(zip_digits) if zip_digits else 0
    except ValueError:
        zip_int = 0
    state = (exposure.state or "").upper()
    if state == "FL" and 32000 <= zip_int <= 34999:
        return True
    if state == "TX" and 77500 <= zip_int <= 78500:
        return True
    if state == "HI":
        return True
    if state == "CA" and exposure.in_wildfire_zone:
        return True
    return False


def _hazards_for_exposure(exposure: CATExposureResult) -> set[str]:
    hazards: set[str] = set()
    if exposure.in_flood_plain or exposure.flood_risk_score >= 0.4:
        hazards.add("flood")
    if exposure.in_wildfire_zone or exposure.wildfire_risk_score >= 0.4:
        hazards.add("wildfire")
    if exposure.in_coastal_zone or exposure.hurricane_risk_score >= 0.4:
        hazards.add("wind")
    return hazards


def _cat_perils_in_coverages(bundle: SubmissionBundle) -> set[str]:
    perils: set[str] = set()
    coverages = (bundle.structured.coverages or []) if bundle.structured else []
    for coverage in coverages:
        blob = f"{coverage.coverage_type} {coverage.endorsements}".lower()
        for peril, keywords in _PERIL_COVERAGE_KEYWORDS.items():
            if any(k in blob for k in keywords):
                perils.add(peril)
    return perils


def _all_coverages_cat(bundle: SubmissionBundle) -> bool:
    coverages = (bundle.structured.coverages or []) if bundle.structured else []
    if not coverages:
        return False
    for coverage in coverages:
        blob = f"{coverage.coverage_type} {coverage.endorsements}".lower()
        if not any(k in blob for peril_keywords in _PERIL_COVERAGE_KEYWORDS.values() for k in peril_keywords):
            return False
    return True


def _claim_count(bundle: SubmissionBundle) -> tuple[int, list[ClaimRecord]]:
    structured = bundle.structured
    if structured is None:
        return 0, []
    risk_profile = structured.risk_profile
    financial = structured.financial
    if risk_profile is None and financial is None:
        return 0, []

    best: list[ClaimRecord] = list(risk_profile.prior_claims or []) if risk_profile is not None else []
    loss_run_claims = list(financial.loss_run.claims or []) if financial is not None and financial.loss_run is not None else []
    if len(loss_run_claims) > len(best):
        best = loss_run_claims
    prior_losses = len(financial.prior_losses or []) if financial is not None else 0
    return max(len(best), prior_losses), best


def _recent_loss_evidence(claims: list[ClaimRecord], effective_date: date | None, window_days: int) -> list[str]:
    if not claims or effective_date is None:
        return []
    latest = max(claims, key=lambda c: c.date_of_loss).date_of_loss
    days = (effective_date - latest).days
    if 0 <= days <= window_days:
        return [f"Latest claim {latest.isoformat()} is {days} days before the coverage effective date {effective_date.isoformat()}"]
    return []


class AdverseSelectionSignalType(str, Enum):
    HAZARD_ZONE_DEMAND = "hazard_zone_demand"
    EXCLUDED_ZONE_DEMAND = "excluded_zone_demand"
    LOSS_MOTIVATED_SEEKING = "loss_motivated_seeking"
    BARE_CAT_COVER = "bare_cat_cover"


class AdverseSelectionConfig(BaseModel):
    """Tunable thresholds for the adverse-selection screen."""

    prior_claims_floor: int = 1
    recent_loss_days: int = 730
    hazard_zone_demand_score: float = 0.60
    excluded_zone_demand_score: float = 0.40
    loss_motivated_score: float = 0.50
    bare_cat_score: float = 0.30
    high_threshold: float = 0.60


class AdverseSelectionSignal(BaseModel):
    signal_type: AdverseSelectionSignalType
    detail: str
    contribution: float
    evidence: list[str] = Field(default_factory=list)


class AdverseSelectionAssessment(BaseModel):
    """The adverse-selection posture of a single applicant.

    ``adverse_selection_score`` is the additive (capped at 1.0) sum of the
    detected loss-seeking signals. ``status`` is ``low`` when nothing points at
    disproportionate motivation, ``flagged`` when at least one signal fires
    below the high threshold, and ``high`` above it.
    """

    applicant_name: str = ""
    signals: list[AdverseSelectionSignal] = Field(default_factory=list)
    adverse_selection_score: float = 0.0
    status: str = "low"

    @property
    def signal_types(self) -> list[str]:
        return [s.signal_type.value for s in self.signals]


def assess_adverse_selection(
    bundle: SubmissionBundle,
    cat_result: CATModelResult | None = None,
    config: AdverseSelectionConfig | None = None,
) -> AdverseSelectionAssessment:
    """Screen a submission for disproportionate loss-seeking motivation.

    CAT exposures are supplied as ``cat_result`` (the agent obtains them from
    the catastrophe model client); the pure function never queries it itself so
    tests can inject exposures directly.
    """
    cfg = config or AdverseSelectionConfig()
    structured = bundle.structured
    applicant = (structured.named_insured.legal_name if structured and structured.named_insured else "") or ""

    signals: list[AdverseSelectionSignal] = []
    requested_perils = _cat_perils_in_coverages(bundle)

    # 1. Hazard-zone demand — the flood-plain example.
    if cat_result is not None:
        for exposure in cat_result.exposures:
            hazards = _hazards_for_exposure(exposure)
            demanded = hazards & requested_perils
            if demanded:
                perils = ", ".join(sorted(demanded))
                signals.append(
                    AdverseSelectionSignal(
                        signal_type=AdverseSelectionSignalType.HAZARD_ZONE_DEMAND,
                        detail=(
                            f"{exposure.city}, {exposure.state} sits in a {perils} hazard zone "
                            "and the applicant requests that exact cover — the applicant in the "
                            "zone is the one most interested in buying the zone's insurance."
                        ),
                        contribution=cfg.hazard_zone_demand_score,
                        evidence=[
                            f"Combined CAT score: {exposure.combined_cat_score:.0%}",
                            f"Coastal: {exposure.in_coastal_zone}, wildfire zone: {exposure.in_wildfire_zone}, flood plain: {exposure.in_flood_plain}",
                        ],
                    )
                )
                break

    # 2. Excluded-zone demand — escalation where carrier appetite already declined.
    if cat_result is not None:
        for exposure in cat_result.exposures:
            hazards = _hazards_for_exposure(exposure)
            demanded = hazards & requested_perils
            if demanded and _in_excluded_zone(exposure):
                perils = ", ".join(sorted(demanded))
                signals.append(
                    AdverseSelectionSignal(
                        signal_type=AdverseSelectionSignalType.EXCLUDED_ZONE_DEMAND,
                        detail=(f"{exposure.city}, {exposure.state} is in a zone the carrier's appetite has declined (guideline APT-003) and the applicant seeks {perils} cover there."),
                        contribution=cfg.excluded_zone_demand_score,
                    )
                )
                break

    # 3. Loss-motivated seeking — a claim history behind a fresh application.
    claim_count, claims = _claim_count(bundle)
    if claim_count >= cfg.prior_claims_floor:
        effective_date = structured.policy_period.effective_date if structured and structured.policy_period else None
        evidence = [f"{claim_count} prior claim(s) on record while applying for a new policy"]
        evidence += _recent_loss_evidence(claims, effective_date, cfg.recent_loss_days)
        signals.append(
            AdverseSelectionSignal(
                signal_type=AdverseSelectionSignalType.LOSS_MOTIVATED_SEEKING,
                detail=(f"The applicant carries {claim_count} prior claim(s) yet is applying for a new policy — a loss history is exactly what motivates coverage seeking."),
                contribution=cfg.loss_motivated_score,
                evidence=evidence,
            )
        )

    # 4. Bare catastrophic cover — only the high-loss perils requested.
    if requested_perils and _all_coverages_cat(bundle):
        signals.append(
            AdverseSelectionSignal(
                signal_type=AdverseSelectionSignalType.BARE_CAT_COVER,
                detail=(f"The applicant requests only catastrophe cover ({', '.join(sorted(requested_perils))}) — buying just the perils they expect to use."),
                contribution=cfg.bare_cat_score,
            )
        )

    score = min(1.0, sum(s.contribution for s in signals))
    if signals and score >= cfg.high_threshold:
        status = "high"
    elif signals:
        status = "flagged"
    else:
        status = "low"

    return AdverseSelectionAssessment(
        applicant_name=applicant,
        signals=signals,
        adverse_selection_score=round(score, 4),
        status=status,
    )
