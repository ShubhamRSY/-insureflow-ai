"""General / non-life product families. No India motor/home/travel filing yet — catalog."""

from __future__ import annotations

# Empty until a carrier general/non-life filing is imported.
LIVE_GENERAL_PRODUCT_IDS: frozenset[str] = frozenset()


def is_filed_general_product(product_id: str | None) -> bool:
    if not product_id:
        return False
    key = str(product_id).strip().lower().replace("-", "_").replace(" ", "_")
    return key in LIVE_GENERAL_PRODUCT_IDS
