"""Health plan network structures — PPO / HMO / EPO / POS.

Network type governs provider choice, referral requirements, and
out-of-network cost sharing. It carries a cost factor for rating: HMO-style
networks (tight panels, referrals, no out-of-network coverage) cost less to
administer than broad PPO access.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.models.policy import HealthNetworkType, HealthPlanFeatures

# Representative network cost relativities vs the filed manual rate.
_NETWORK_RATING_FACTOR: dict[HealthNetworkType, float] = {
    HealthNetworkType.HMO: 0.92,
    HealthNetworkType.EPO: 0.95,
    HealthNetworkType.POS: 1.02,
    HealthNetworkType.PPO: 1.05,
    HealthNetworkType.INDEMNITY: 1.12,
    HealthNetworkType.NONE: 1.0,
    HealthNetworkType.UNKNOWN: 1.0,
}


def _detect_network(blob: str) -> tuple[HealthNetworkType, str]:
    lowered = blob.lower()
    if "ppo" in lowered:
        return HealthNetworkType.PPO, "Preferred provider organization"
    if "hmo" in lowered:
        return HealthNetworkType.HMO, "Health maintenance organization"
    if "epo" in lowered:
        return HealthNetworkType.EPO, "Exclusive provider organization"
    if "pos" in lowered:
        return HealthNetworkType.POS, "Point-of-service plan"
    if any(m in lowered for m in ("indemnity plan", "fee-for-service", "ffs")):
        return HealthNetworkType.INDEMNITY, "Traditional indemnity / fee-for-service"
    return HealthNetworkType.UNKNOWN, "Network type not declared"


def assess_network(blob: str) -> HealthPlanFeatures:
    """Detect the network structure and derive cost-sharing + rating features."""
    network, detail = _detect_network(blob)
    lowered = blob.lower()

    referral = None
    if any(m in lowered for m in ("referral required", "gatekeeper", "primary care physician referral")):
        referral = True
    elif any(m in lowered for m in ("no referral", "self-referral allowed")):
        referral = False

    oon = None
    if any(m in lowered for m in ("out of network coverage", "out-of-network covered", "out-of-network coverage provided")):
        oon = True
    elif any(m in lowered for m in ("no out of network", "no out-of-network", "out of network not covered", "out-of-network excluded")):
        oon = False

    feature = HealthPlanFeatures(
        network_type=network,
        in_network=network is not HealthNetworkType.UNKNOWN,
        primary_care_referral_required=referral,
        out_of_network_coverage=oon,
        rating_factor=_NETWORK_RATING_FACTOR.get(network, 1.0),
        detail=detail,
    )

    # Managed-care cost sharing: coinsurance / copayment lines.
    for label in ("in-network coinsurance", "in network coinsurance"):
        idx = lowered.find(label)
        if idx >= 0:
            seg = lowered[idx : idx + 12]
            m = re.search(r"(\d{1,3})\s*%", seg)
            if m:
                feature.in_network_coinsurance = float(m.group(1)) / 100.0
    for label in ("out-of-network coinsurance", "out of network coinsurance"):
        idx = lowered.find(label)
        if idx >= 0:
            seg = lowered[idx : idx + 12]
            m = re.search(r"(\d{1,3})\s*%", seg)
            if m:
                feature.out_of_network_coinsurance = float(m.group(1)) / 100.0

    return feature


def network_rating_factor(features: HealthPlanFeatures | None) -> float:
    if features is None:
        return 1.0
    return features.rating_factor


def network_assessment_from_bundle(bundle: Any) -> dict[str, Any]:
    """Network features extracted from a health submission's documents."""
    pieces: list[str] = []
    if bundle is not None and getattr(bundle, "structured", None) is not None:
        pieces.append(bundle.structured.risk_profile.business_description or "")
    for doc in (getattr(bundle, "unstructured", None) or []) + (getattr(bundle, "supplemental", None) or []):
        pieces.append(doc.raw_text)
    features = assess_network(" ".join(pieces))
    return {
        "network_type": features.network_type.value,
        "in_network": features.in_network,
        "referral_required": features.primary_care_referral_required,
        "out_of_network_coverage": features.out_of_network_coverage,
        "in_network_coinsurance": features.in_network_coinsurance,
        "out_of_network_coinsurance": features.out_of_network_coinsurance,
        "rating_factor": features.rating_factor,
        "detail": features.detail,
    }
