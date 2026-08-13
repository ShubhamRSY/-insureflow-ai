"""Health product families. No filed health rate manual yet — all catalog."""

from __future__ import annotations

# Empty until a carrier health filing is imported. Hub + checklists still work.
LIVE_HEALTH_PRODUCT_IDS: frozenset[str] = frozenset()


def is_filed_health_product(product_id: str | None) -> bool:
    if not product_id:
        return False
    key = str(product_id).strip().lower().replace("-", "_").replace(" ", "_")
    return key in LIVE_HEALTH_PRODUCT_IDS
