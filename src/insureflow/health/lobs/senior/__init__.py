"""LOB — Senior/Medicare Health Insurance: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.senior.medicare_advantage import PRODUCT_ID as MEDICARE_ADVANTAGE_PRODUCT_ID
from insureflow.health.lobs.senior.medicare_advantage_snp import PRODUCT_ID as MEDICARE_ADVANTAGE_SNP_PRODUCT_ID
from insureflow.health.lobs.senior.medicare_part_d import PRODUCT_ID as MEDICARE_PART_D_PRODUCT_ID
from insureflow.health.lobs.senior.medicare_supplement import PRODUCT_ID as MEDICARE_SUPPLEMENT_PRODUCT_ID
from insureflow.health.lobs.senior.medigap_high_deductible_plan_g import PRODUCT_ID as MEDIGAP_HD_PLAN_G_PRODUCT_ID

SENIOR_LOGIC_PATHS = {
    MEDICARE_SUPPLEMENT_PRODUCT_ID: "insureflow.health.lobs.senior.medicare_supplement",
    MEDICARE_ADVANTAGE_PRODUCT_ID: "insureflow.health.lobs.senior.medicare_advantage",
    MEDIGAP_HD_PLAN_G_PRODUCT_ID: "insureflow.health.lobs.senior.medigap_high_deductible_plan_g",
    MEDICARE_ADVANTAGE_SNP_PRODUCT_ID: "insureflow.health.lobs.senior.medicare_advantage_snp",
    MEDICARE_PART_D_PRODUCT_ID: "insureflow.health.lobs.senior.medicare_part_d",
}
