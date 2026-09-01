"""LOB — Individual & Family Health Insurance: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.individual.bronze_silver_plans import PRODUCT_ID as ACA_MARKETPLACE_PRODUCT_ID
from insureflow.health.lobs.individual.off_exchange_major_medical import PRODUCT_ID as OFF_EXCHANGE_PRODUCT_ID

INDIVIDUAL_LOGIC_PATHS = {
    ACA_MARKETPLACE_PRODUCT_ID: "insureflow.health.lobs.individual.bronze_silver_plans",
    OFF_EXCHANGE_PRODUCT_ID: "insureflow.health.lobs.individual.off_exchange_major_medical",
}
