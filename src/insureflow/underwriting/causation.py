"""Proximate cause analysis — the chain of events from the covered peril to loss.

An unbroken chain of events originating from an insured peril must be the direct
cause of the loss for coverage to apply. If an excluded peril supersedes the
covered cause (intervening/superseding cause), coverage fails.
"""

from __future__ import annotations

from insureflow.models.policy import ProximateCauseResult

# Cause text → peril family mapping.
_PERIL_MAP: dict[str, list[str]] = {
    "fire": ["fire", "smoke", "combustion"],
    "wind": ["wind", "tornado", "hurricane", "cyclone", "typhoon", "storm"],
    "water": ["water", "flood", "leak", "burst pipe", "sprinkler discharge", "rain"],
    "theft": ["theft", "burglary", "robbery", "vandalism", "malicious mischief"],
    "liability": ["bodily injury", "third party", "negligence", "trip and fall", "premises liability"],
    "auto": ["collision", "vehicle", "motor vehicle", "car accident", "overturned"],
    "business_interruption": ["business interruption", "contingent", "civil authority"],
}

# Perils almost always excluded by standard property forms.
_SYSTEMIC_EXCLUSIONS = ("flood", "earthquake", "war", "nuclear", "terrorism", "pollution", "mold")


def _peril_of(cause: str) -> str:
    lowered = (cause or "").lower()
    for peril, markers in _PERIL_MAP.items():
        if any(m in lowered for m in markers):
            return peril
    return "unknown"


def analyze_proximate_cause(
    cause: str,
    description: str = "",
    *,
    policy_perils: list[str] | None = None,
    exclusions: list[str] | None = None,
) -> ProximateCauseResult:
    """Determine whether the proximate cause is a covered peril in an unbroken chain."""
    policy_perils = [p.lower() for p in (policy_perils or [])]
    exclusions = [e.lower() for e in (exclusions or [])]
    peril = _peril_of(cause)
    blob = f"{cause} {description}".lower()

    # Intervening/superseding cause — description names a later excluded event.
    superseding: str = ""
    for exc in exclusions:
        if exc and exc in blob:
            superseding = exc
    for sys in _SYSTEMIC_EXCLUSIONS:
        if sys in blob:
            superseding = superseding or sys

    excluded = superseding != ""
    covered = peril in policy_perils

    # An unbroken chain requires the loss to flow continuously from the covered
    # peril; a superseding excluded event breaks it.
    unbroken = covered and not excluded

    if superseding:
        reasoning = f"Cause '{cause}' maps to peril '{peril}' but description names superseding excluded event '{superseding}' — the chain of causation is broken"
    elif covered:
        reasoning = f"Cause '{cause}' maps to covered peril '{peril}' — unbroken chain from insured peril to loss"
    else:
        reasoning = f"Cause '{cause}' maps to peril '{peril}' which is not in the covered perils ({', '.join(policy_perils) or 'none declared'})"

    decision = "covered" if unbroken else ("not_covered" if (excluded or not covered) else "indeterminate")

    return ProximateCauseResult(
        cause=cause,
        description=description,
        covered_peril=covered,
        excluded_peril=superseding,
        unbroken_chain=unbroken,
        proximate_cause=peril,
        decision=decision,
        reasoning=reasoning,
    )
