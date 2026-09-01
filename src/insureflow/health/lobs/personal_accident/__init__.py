"""LOB — Accidental Death & Dismemberment / Accident Indemnity: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.personal_accident.add_accident_indemnity import PRODUCT_ID as ADD_PRODUCT_ID
from insureflow.health.lobs.personal_accident.standalone_add import PRODUCT_ID as STANDALONE_ADD_PRODUCT_ID

PERSONAL_ACCIDENT_LOGIC_PATHS = {
    ADD_PRODUCT_ID: "insureflow.health.lobs.personal_accident.add_accident_indemnity",
    STANDALONE_ADD_PRODUCT_ID: "insureflow.health.lobs.personal_accident.standalone_add",
}
