"""LOB — Group / Corporate Health Insurance: dedicated per-product logic paths."""

from __future__ import annotations

from insureflow.health.lobs.group.large_group import PRODUCT_ID as LARGE_GROUP_PRODUCT_ID
from insureflow.health.lobs.group.small_group import PRODUCT_ID as SMALL_GROUP_PRODUCT_ID

GROUP_LOGIC_PATHS = {
    SMALL_GROUP_PRODUCT_ID: "insureflow.health.lobs.group.small_group",
    LARGE_GROUP_PRODUCT_ID: "insureflow.health.lobs.group.large_group",
}
