"""LOB — Family Health Plan: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.family.family_extended_dependents import PRODUCT_ID as FAMILY_EXTENDED_DEPENDENTS_PRODUCT_ID
from insureflow.health.lobs.family.family_hdhp_hsa_qualified import PRODUCT_ID as FAMILY_HDHP_PRODUCT_ID
from insureflow.health.lobs.family.family_health_plan import PRODUCT_ID as FAMILY_HEALTH_PLAN_PRODUCT_ID

FAMILY_LOGIC_PATHS = {
    FAMILY_HEALTH_PLAN_PRODUCT_ID: "insureflow.health.lobs.family.family_health_plan",
    FAMILY_HDHP_PRODUCT_ID: "insureflow.health.lobs.family.family_hdhp_hsa_qualified",
    FAMILY_EXTENDED_DEPENDENTS_PRODUCT_ID: "insureflow.health.lobs.family.family_extended_dependents",
}
