"""ULIP LOB (LOB 5) — dedicated logic paths per sub-product."""

from __future__ import annotations

from insureflow.life.lobs.ulip.child_ulip import PRODUCT_ID as CHILD_ULIP_PRODUCT_ID
from insureflow.life.lobs.ulip.pension_ulip import PRODUCT_ID as PENSION_ULIP_PRODUCT_ID
from insureflow.life.lobs.ulip.regular_premium_ulip import PRODUCT_ID as RP_ULIP_PRODUCT_ID
from insureflow.life.lobs.ulip.single_premium_ulip import PRODUCT_ID as SP_ULIP_PRODUCT_ID
from insureflow.life.lobs.ulip.ulip_type_i import PRODUCT_ID as TYPE_I_PRODUCT_ID
from insureflow.life.lobs.ulip.ulip_type_ii import PRODUCT_ID as TYPE_II_PRODUCT_ID

ULIP_LOGIC_PATHS: dict[str, str] = {
    "single_premium_ulip": "insureflow.life.lobs.ulip.single_premium_ulip",
    "regular_premium_ulip": "insureflow.life.lobs.ulip.regular_premium_ulip",
    "ulip_type_i": "insureflow.life.lobs.ulip.ulip_type_i",
    "ulip_type_ii": "insureflow.life.lobs.ulip.ulip_type_ii",
    "pension_ulip": "insureflow.life.lobs.ulip.pension_ulip",
    "child_ulip": "insureflow.life.lobs.ulip.child_ulip",
}

assert SP_ULIP_PRODUCT_ID and RP_ULIP_PRODUCT_ID and TYPE_I_PRODUCT_ID and TYPE_II_PRODUCT_ID and PENSION_ULIP_PRODUCT_ID and CHILD_ULIP_PRODUCT_ID
