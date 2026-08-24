"""Annuity LOB (LOB 7) — dedicated logic paths per sub-product."""

from __future__ import annotations

from insureflow.life.lobs.annuity.deferred_annuity import PRODUCT_ID as DEFERRED_ANNUITY_PRODUCT_ID
from insureflow.life.lobs.annuity.fixed_annuity import PRODUCT_ID as FIXED_ANNUITY_PRODUCT_ID
from insureflow.life.lobs.annuity.immediate_annuity import PRODUCT_ID as IMMEDIATE_ANNUITY_PRODUCT_ID
from insureflow.life.lobs.annuity.indexed_annuity import PRODUCT_ID as INDEXED_ANNUITY_PRODUCT_ID
from insureflow.life.lobs.annuity.joint_survivor_annuity import PRODUCT_ID as JOINT_SURVIVOR_PRODUCT_ID
from insureflow.life.lobs.annuity.life_annuity import PRODUCT_ID as LIFE_ANNUITY_PRODUCT_ID
from insureflow.life.lobs.annuity.qlac import PRODUCT_ID as QLAC_PRODUCT_ID
from insureflow.life.lobs.annuity.structured_settlement_annuity import (
    PRODUCT_ID as STRUCTURED_SETTLEMENT_PRODUCT_ID,
)
from insureflow.life.lobs.annuity.variable_annuity import PRODUCT_ID as VARIABLE_ANNUITY_PRODUCT_ID

ANNUITY_LOGIC_PATHS: dict[str, str] = {
    "immediate_annuity": "insureflow.life.lobs.annuity.immediate_annuity",
    "deferred_annuity": "insureflow.life.lobs.annuity.deferred_annuity",
    "fixed_annuity": "insureflow.life.lobs.annuity.fixed_annuity",
    "variable_annuity": "insureflow.life.lobs.annuity.variable_annuity",
    "indexed_annuity": "insureflow.life.lobs.annuity.indexed_annuity",
    "life_annuity": "insureflow.life.lobs.annuity.life_annuity",
    "joint_survivor_annuity": "insureflow.life.lobs.annuity.joint_survivor_annuity",
    "qlac": "insureflow.life.lobs.annuity.qlac",
    "structured_settlement_annuity": "insureflow.life.lobs.annuity.structured_settlement_annuity",
}

assert (
    IMMEDIATE_ANNUITY_PRODUCT_ID
    and DEFERRED_ANNUITY_PRODUCT_ID
    and FIXED_ANNUITY_PRODUCT_ID
    and VARIABLE_ANNUITY_PRODUCT_ID
    and INDEXED_ANNUITY_PRODUCT_ID
    and LIFE_ANNUITY_PRODUCT_ID
    and JOINT_SURVIVOR_PRODUCT_ID
    and QLAC_PRODUCT_ID
    and STRUCTURED_SETTLEMENT_PRODUCT_ID
)
