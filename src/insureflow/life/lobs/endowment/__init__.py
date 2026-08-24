"""Endowment LOB (LOB 4) — dedicated logic paths per sub-product."""

from __future__ import annotations

from insureflow.life.lobs.endowment.full_endowment import PRODUCT_ID as FULL_ENDOWMENT_PRODUCT_ID
from insureflow.life.lobs.endowment.guaranteed_fixed_endowment import (
    PRODUCT_ID as FIXED_ENDOWMENT_PRODUCT_ID,
)
from insureflow.life.lobs.endowment.pure_endowment import PRODUCT_ID as PURE_ENDOWMENT_PRODUCT_ID

ENDOWMENT_LOGIC_PATHS: dict[str, str] = {
    "pure_endowment": "insureflow.life.lobs.endowment.pure_endowment",
    "full_endowment": "insureflow.life.lobs.endowment.full_endowment",
    "guaranteed_fixed_endowment": "insureflow.life.lobs.endowment.guaranteed_fixed_endowment",
}

assert FULL_ENDOWMENT_PRODUCT_ID and FIXED_ENDOWMENT_PRODUCT_ID and PURE_ENDOWMENT_PRODUCT_ID
