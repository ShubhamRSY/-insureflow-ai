"""LOB — Disability Income Insurance: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.disability.long_term_disability import PRODUCT_ID as LTD_PRODUCT_ID
from insureflow.health.lobs.disability.permanent_partial_disability import PRODUCT_ID as PPD_PRODUCT_ID
from insureflow.health.lobs.disability.permanent_total_disability import PRODUCT_ID as PTD_PRODUCT_ID
from insureflow.health.lobs.disability.short_term_disability import PRODUCT_ID as STD_PRODUCT_ID

DISABILITY_LOGIC_PATHS = {
    STD_PRODUCT_ID: "insureflow.health.lobs.disability.short_term_disability",
    LTD_PRODUCT_ID: "insureflow.health.lobs.disability.long_term_disability",
    PTD_PRODUCT_ID: "insureflow.health.lobs.disability.permanent_total_disability",
    PPD_PRODUCT_ID: "insureflow.health.lobs.disability.permanent_partial_disability",
}
