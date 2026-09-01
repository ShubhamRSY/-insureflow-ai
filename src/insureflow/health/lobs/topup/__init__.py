"""LOB — Supplemental / Gap Health Coverage: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.topup.supplemental_gap import PRODUCT_ID as SUPPLEMENTAL_GAP_PRODUCT_ID

TOPUP_LOGIC_PATHS = {
    SUPPLEMENTAL_GAP_PRODUCT_ID: "insureflow.health.lobs.topup.supplemental_gap",
}
