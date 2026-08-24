"""Money-Back LOB (LOB 6) — dedicated logic paths per sub-product."""

from __future__ import annotations

from insureflow.life.lobs.money_back.children_money_back import PRODUCT_ID as CHILDREN_MB_PRODUCT_ID
from insureflow.life.lobs.money_back.traditional_money_back import PRODUCT_ID as TRADITIONAL_MB_PRODUCT_ID
from insureflow.life.lobs.money_back.with_profit_money_back import PRODUCT_ID as WITH_PROFIT_MB_PRODUCT_ID

MONEY_BACK_LOGIC_PATHS: dict[str, str] = {
    "traditional_money_back": "insureflow.life.lobs.money_back.traditional_money_back",
    "with_profit_money_back": "insureflow.life.lobs.money_back.with_profit_money_back",
    "children_money_back": "insureflow.life.lobs.money_back.children_money_back",
}

assert TRADITIONAL_MB_PRODUCT_ID and WITH_PROFIT_MB_PRODUCT_ID and CHILDREN_MB_PRODUCT_ID
