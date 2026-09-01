"""Health product families. All catalog leaves have a dedicated LOB logic
path (insureflow.health.lobs) or a filed rate entry, so the whole hub is live.
"""

from __future__ import annotations

# Every health hub leaf has a dedicated logic path in insureflow.health.lobs
# (see insureflow.health.lobs.PRODUCT_LOGIC_PATHS), so the whole hub is live.
LIVE_HEALTH_PRODUCT_IDS: frozenset[str] = frozenset(
    {
        "aca_marketplace_plan",
        "off_exchange_major_medical",
        "family_health_plan",
        "critical_illness_standalone",
        "disease_specific_critical_illness",
        "medicare_supplement",
        "medicare_advantage",
        "small_group_health",
        "large_group_health",
        "supplemental_gap_coverage",
        "add_accident_indemnity",
        "short_term_disability",
        "long_term_disability",
    }
)


def is_filed_health_product(product_id: str | None) -> bool:
    if not product_id:
        return False
    key = str(product_id).strip().lower().replace("-", "_").replace(" ", "_")
    return key in LIVE_HEALTH_PRODUCT_IDS
