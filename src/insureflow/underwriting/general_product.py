"""General / non-life product families. Every catalog leaf now has a filed rate manual — the whole general hub is live."""

from __future__ import annotations

# Filed + rated products in the general/non-life hub. Every leaf in general_lobs
# is now live via a filed rate manual.
LIVE_GENERAL_PRODUCT_IDS: frozenset[str] = frozenset(
    {
        "professional_indemnity_gi",
        "public_liability_gi",
        "product_liability_gi",
        "cyber_data_breach",
        "cyber_ransomware",
        "marine_cargo",
        "marine_hull",
        "fire_residential",
        "fire_commercial",
        "travel_domestic",
        "travel_international",
        "home_structure",
        "home_contents",
        "home_comprehensive",
        "car_tp",
        "car_comprehensive",
        "tw_tp",
        "tw_comprehensive",
        "cv_tp",
        "cv_comprehensive",
        "crop_yield",
        "crop_weather",
        "livestock_cattle",
        "pet_insurance",
        "wedding_insurance",
        "concert_event_insurance",
        "title_insurance_gi",
        "mortgage_insurance_gi",
        "insurer_psu",
        "insurer_private",
        "reinsurance_treaty",
    }
)


def is_filed_general_product(product_id: str | None) -> bool:
    if not product_id:
        return False
    key = str(product_id).strip().lower().replace("-", "_").replace(" ", "_")
    return key in LIVE_GENERAL_PRODUCT_IDS
