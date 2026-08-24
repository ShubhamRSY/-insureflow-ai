"""LOB 1 — Term Life Insurance: dedicated per-product logic paths.

Each product in this package owns its own underwriting rules, rating math,
and state-rule table. There is deliberately no shared term engine: a Level
Term submission is reviewed differently from Group or Credit Life, and the
code mirrors that.
"""

from __future__ import annotations

from insureflow.life.lobs.term_life.convertible_term import PRODUCT_ID as CONVERTIBLE_TERM_PRODUCT_ID
from insureflow.life.lobs.term_life.credit_life import PRODUCT_ID as CREDIT_LIFE_PRODUCT_ID
from insureflow.life.lobs.term_life.decreasing_term import PRODUCT_ID as DECREASING_TERM_PRODUCT_ID
from insureflow.life.lobs.term_life.group_term import PRODUCT_ID as GROUP_TERM_PRODUCT_ID
from insureflow.life.lobs.term_life.increasing_term import PRODUCT_ID as INCREASING_TERM_PRODUCT_ID
from insureflow.life.lobs.term_life.level_term import PRODUCT_ID as LEVEL_TERM_PRODUCT_ID
from insureflow.life.lobs.term_life.mortgage_life import PRODUCT_ID as MORTGAGE_LIFE_PRODUCT_ID
from insureflow.life.lobs.term_life.renewable_term import PRODUCT_ID as RENEWABLE_TERM_PRODUCT_ID
from insureflow.life.lobs.term_life.rop_term import PRODUCT_ID as ROP_TERM_PRODUCT_ID

TERM_LIFE_LOGIC_PATHS = {
    LEVEL_TERM_PRODUCT_ID: "insureflow.life.lobs.term_life.level_term",
    DECREASING_TERM_PRODUCT_ID: "insureflow.life.lobs.term_life.decreasing_term",
    MORTGAGE_LIFE_PRODUCT_ID: "insureflow.life.lobs.term_life.mortgage_life",
    INCREASING_TERM_PRODUCT_ID: "insureflow.life.lobs.term_life.increasing_term",
    RENEWABLE_TERM_PRODUCT_ID: "insureflow.life.lobs.term_life.renewable_term",
    CONVERTIBLE_TERM_PRODUCT_ID: "insureflow.life.lobs.term_life.convertible_term",
    ROP_TERM_PRODUCT_ID: "insureflow.life.lobs.term_life.rop_term",
    GROUP_TERM_PRODUCT_ID: "insureflow.life.lobs.term_life.group_term",
    CREDIT_LIFE_PRODUCT_ID: "insureflow.life.lobs.term_life.credit_life",
}
