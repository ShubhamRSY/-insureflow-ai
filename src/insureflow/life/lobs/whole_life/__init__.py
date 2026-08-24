"""LOB 2 — Whole Life Insurance: dedicated per-product logic paths.

Each sub-product (ordinary, limited-pay, single-premium, par, non-par,
modified, graded/GI) owns its own actuarial treatment, underwriting rules,
and state-rule table. Shared code here is dispatch only.
"""

from __future__ import annotations

from insureflow.life.lobs.whole_life.graded import PRODUCT_ID as GRADED_PRODUCT_ID
from insureflow.life.lobs.whole_life.limited_pay import PRODUCT_ID as LIMITED_PAY_PRODUCT_ID
from insureflow.life.lobs.whole_life.modified import PRODUCT_ID as MODIFIED_PRODUCT_ID
from insureflow.life.lobs.whole_life.non_participating import PRODUCT_ID as NON_PARTICIPATING_PRODUCT_ID
from insureflow.life.lobs.whole_life.ordinary_whole import PRODUCT_ID as TRADITIONAL_PRODUCT_ID
from insureflow.life.lobs.whole_life.participating import PRODUCT_ID as PARTICIPATING_PRODUCT_ID
from insureflow.life.lobs.whole_life.single_premium import PRODUCT_ID as SINGLE_PREMIUM_PRODUCT_ID

WHOLE_LIFE_LOGIC_PATHS = {
    TRADITIONAL_PRODUCT_ID: "insureflow.life.lobs.whole_life.ordinary_whole",
    LIMITED_PAY_PRODUCT_ID: "insureflow.life.lobs.whole_life.limited_pay",
    SINGLE_PREMIUM_PRODUCT_ID: "insureflow.life.lobs.whole_life.single_premium",
    PARTICIPATING_PRODUCT_ID: "insureflow.life.lobs.whole_life.participating",
    NON_PARTICIPATING_PRODUCT_ID: "insureflow.life.lobs.whole_life.non_participating",
    MODIFIED_PRODUCT_ID: "insureflow.life.lobs.whole_life.modified",
    GRADED_PRODUCT_ID: "insureflow.life.lobs.whole_life.graded",
}
