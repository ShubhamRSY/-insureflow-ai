"""LOB — Critical Illness Insurance: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.critical_illness.critical_illness_standalone import PRODUCT_ID as CI_STANDALONE_PRODUCT_ID
from insureflow.health.lobs.critical_illness.disease_specific import PRODUCT_ID as DISEASE_SPECIFIC_PRODUCT_ID

CRITICAL_ILLNESS_LOGIC_PATHS = {
    CI_STANDALONE_PRODUCT_ID: "insureflow.health.lobs.critical_illness.critical_illness_standalone",
    DISEASE_SPECIFIC_PRODUCT_ID: "insureflow.health.lobs.critical_illness.disease_specific",
}
