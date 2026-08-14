"""Health product families. Filed health rate manual is live — all 37 leaves underwritable and rateable."""

from __future__ import annotations

# Every health hub leaf has a product handler in health_uw.py and a filed rate
# entry in general_health_rate_manual.json, so the whole hub is live.
LIVE_HEALTH_PRODUCT_IDS: frozenset[str] = frozenset(
    {
        "critical_illness_multistage",
        "critical_illness_rider",
        "critical_illness_standalone",
        "disability_income",
        "disability_ppd",
        "disability_ptd",
        "disability_ttd",
        "disease_specific",
        "family_floater_multiyear",
        "family_floater_parent",
        "family_floater_restore",
        "family_floater_standard",
        "group_association",
        "group_employer_mediclaim",
        "group_government_psu",
        "group_pa_health_combo",
        "hospital_cash",
        "individual_basic",
        "individual_comprehensive",
        "maternity_inclusive",
        "maternity_newborn_standalone",
        "mediclaim_basic",
        "opd_cover",
        "opd_only",
        "overseas_health",
        "pa_add",
        "pa_family",
        "pa_group",
        "pa_individual",
        "senior_no_medical",
        "senior_preexisting",
        "senior_standard",
        "senior_topup",
        "super_topup_plan",
        "topup_plan",
        "ulip_health",
        "wellness_savings",
    }
)


def is_filed_health_product(product_id: str | None) -> bool:
    if not product_id:
        return False
    key = str(product_id).strip().lower().replace("-", "_").replace(" ", "_")
    return key in LIVE_HEALTH_PRODUCT_IDS
