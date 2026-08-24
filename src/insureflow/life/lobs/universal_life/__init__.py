"""Universal Life LOB (LOB 3) — dedicated logic paths per sub-product."""

from __future__ import annotations

from insureflow.life.lobs.universal_life.current_assumption_universal_life import (
    PRODUCT_ID as CAUL_PRODUCT_ID,
)
from insureflow.life.lobs.universal_life.guaranteed_universal_life import (
    PRODUCT_ID as GUL_PRODUCT_ID,
)
from insureflow.life.lobs.universal_life.indexed_universal_life import (
    PRODUCT_ID as IUL_PRODUCT_ID,
)
from insureflow.life.lobs.universal_life.variable_universal_life import (
    PRODUCT_ID as VUL_PRODUCT_ID,
)

UNIVERSAL_LIFE_LOGIC_PATHS: dict[str, str] = {
    "guaranteed_universal_life": "insureflow.life.lobs.universal_life.guaranteed_universal_life",
    "indexed_universal_life": "insureflow.life.lobs.universal_life.indexed_universal_life",
    "variable_universal_life": "insureflow.life.lobs.universal_life.variable_universal_life",
    "current_assumption_universal_life": "insureflow.life.lobs.universal_life.current_assumption_universal_life",
}

assert GUL_PRODUCT_ID and IUL_PRODUCT_ID and VUL_PRODUCT_ID and CAUL_PRODUCT_ID
