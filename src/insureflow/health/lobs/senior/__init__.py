"""LOB — Senior/Medicare Health Insurance: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.senior.medicare_advantage import PRODUCT_ID as MEDICARE_ADVANTAGE_PRODUCT_ID
from insureflow.health.lobs.senior.medicare_supplement import PRODUCT_ID as MEDICARE_SUPPLEMENT_PRODUCT_ID

SENIOR_LOGIC_PATHS = {
    MEDICARE_SUPPLEMENT_PRODUCT_ID: "insureflow.health.lobs.senior.medicare_supplement",
    MEDICARE_ADVANTAGE_PRODUCT_ID: "insureflow.health.lobs.senior.medicare_advantage",
}
