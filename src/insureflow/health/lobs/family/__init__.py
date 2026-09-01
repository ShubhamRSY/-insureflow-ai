"""LOB — Family Health Plan: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.family.family_health_plan import PRODUCT_ID as FAMILY_HEALTH_PLAN_PRODUCT_ID

FAMILY_LOGIC_PATHS = {
    FAMILY_HEALTH_PLAN_PRODUCT_ID: "insureflow.health.lobs.family.family_health_plan",
}
