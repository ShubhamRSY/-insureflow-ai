"""LOB — Group / Corporate Health Insurance: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.group.association_health_plan import PRODUCT_ID as ASSOCIATION_HEALTH_PLAN_PRODUCT_ID
from insureflow.health.lobs.group.large_group import PRODUCT_ID as LARGE_GROUP_PRODUCT_ID
from insureflow.health.lobs.group.level_funded_group_health import PRODUCT_ID as LEVEL_FUNDED_GROUP_PRODUCT_ID
from insureflow.health.lobs.group.public_sector_group_health import PRODUCT_ID as PUBLIC_SECTOR_GROUP_PRODUCT_ID
from insureflow.health.lobs.group.small_group import PRODUCT_ID as SMALL_GROUP_PRODUCT_ID

GROUP_LOGIC_PATHS = {
    SMALL_GROUP_PRODUCT_ID: "insureflow.health.lobs.group.small_group",
    LARGE_GROUP_PRODUCT_ID: "insureflow.health.lobs.group.large_group",
    ASSOCIATION_HEALTH_PLAN_PRODUCT_ID: "insureflow.health.lobs.group.association_health_plan",
    PUBLIC_SECTOR_GROUP_PRODUCT_ID: "insureflow.health.lobs.group.public_sector_group_health",
    LEVEL_FUNDED_GROUP_PRODUCT_ID: "insureflow.health.lobs.group.level_funded_group_health",
}
