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
        "short_term_limited_duration",
        "hdhp_hsa_qualified",
        "catastrophic_plan",
        "family_health_plan",
        "family_hdhp_hsa_qualified",
        "family_extended_dependents",
        "critical_illness_standalone",
        "disease_specific_critical_illness",
        "critical_illness_rider",
        "critical_illness_multistage",
        "medicare_supplement",
        "medicare_advantage",
        "medigap_high_deductible_plan_g",
        "medicare_advantage_snp",
        "small_group_health",
        "large_group_health",
        "association_health_plan",
        "public_sector_group_health",
        "level_funded_group_health",
        "supplemental_gap_coverage",
        "hospital_indemnity",
        "add_accident_indemnity",
        "standalone_add",
        "short_term_disability",
        "long_term_disability",
        "disability_ptd",
        "disability_ppd",
    }
)


def is_filed_health_product(product_id: str | None) -> bool:
    if not product_id:
        return False
    key = str(product_id).strip().lower().replace("-", "_").replace(" ", "_")
    return key in LIVE_HEALTH_PRODUCT_IDS
