"""Commercial LOB logic paths — explicit per-product code.

Architecture decision (mirrors ``insureflow.life.lobs`` /
``insureflow.health.lobs``): every live commercial product owns a
dedicated logic path in code, with state law applied INSIDE each path.

Property is the one exception in HOW it's wired (see ``property_bi.py``'s
docstring) but is still registered here so the catalog stamps it with the
same ``logic_path`` provenance the other five get.

Adding more commercial products later = create
``insureflow.commercial.lobs.<product>`` modules following this pattern
and register them in PRODUCT_LOGIC_PATHS.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable

from insureflow.commercial.lobs import directors_officers as _directors_officers
from insureflow.commercial.lobs import errors_omissions as _errors_omissions
from insureflow.commercial.lobs import extended as _extended
from insureflow.commercial.lobs import gates as _gates
from insureflow.commercial.lobs import key_person as _key_person
from insureflow.commercial.lobs import property_bi as _property_bi
from insureflow.commercial.lobs import trade_credit as _trade_credit
from insureflow.commercial.lobs import workers_comp as _workers_comp
from insureflow.commercial.lobs.base import CommercialProductContext as CommercialProductContext
from insureflow.commercial.lobs.base import LobOutcome as LobOutcome
from insureflow.rating.models import QuoteResult

# Explicit registry: product id -> module path owning its logic.
PRODUCT_LOGIC_PATHS: dict[str, str] = {
    _property_bi.PRODUCT_ID: _property_bi.LOGIC_PATH,
    _workers_comp.PRODUCT_ID: _workers_comp.LOGIC_PATH,
    _directors_officers.PRODUCT_ID: _directors_officers.LOGIC_PATH,
    _trade_credit.PRODUCT_ID: _trade_credit.LOGIC_PATH,
    _errors_omissions.PRODUCT_ID: _errors_omissions.LOGIC_PATH,
    _key_person.PRODUCT_ID: _key_person.LOGIC_PATH,
    **{pid: _extended.LOGIC_PATH for pid in _extended.PRODUCT_IDS},
    # Catalog rating_line already points at a manual we own. Same formula.
    "architects_engineers": _errors_omissions.LOGIC_PATH,
    "miscellaneous_professional": _errors_omissions.LOGIC_PATH,
    "epli": _errors_omissions.LOGIC_PATH,
    "fiduciary_liability": _directors_officers.LOGIC_PATH,
    "employers_liability": _workers_comp.LOGIC_PATH,
    **{pid: _gates.LOGIC_PATH for pid in _gates.PRODUCT_IDS},
}

# Sibling product → the manual it is actually priced on.
RATED_ON: dict[str, str] = {
    "product_liability": "general_liability",
    "architects_engineers": "errors_omissions",
    "miscellaneous_professional": "errors_omissions",
    "epli": "errors_omissions",
    "fiduciary_liability": "directors_officers",
    "employers_liability": "workers_comp",
}


def normalize_id(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


@lru_cache(maxsize=None)
def _load_builder(module_path: str) -> Callable[[CommercialProductContext], QuoteResult] | None:
    try:
        module = __import__(module_path, fromlist=["build_quote"])
        return getattr(module, "build_quote", None)
    except (ImportError, AttributeError):
        return None


def run_product_logic(ctx: CommercialProductContext) -> QuoteResult | None:
    """Execute the owning product path; None when no dedicated path exists
    (or the registered path — property — doesn't expose a full ``build_quote``
    dispatch, by design; see ``property_bi.py``).
    """
    resolved = normalize_id(ctx.product_id)
    if resolved not in PRODUCT_LOGIC_PATHS:
        return None
    builder = _load_builder(PRODUCT_LOGIC_PATHS[resolved])
    if builder is None:
        return None
    quote = builder(ctx)
    if quote is not None:
        from insureflow.rating.models import refuse_non_finite_premium

        quote = refuse_non_finite_premium(quote)
    parent = RATED_ON.get(resolved)
    if parent and quote is not None:
        meta = dict(quote.metadata or {})
        meta["rated_on_product"] = parent
        note = f"Rated on the {parent.replace('_', ' ')} manual — no separate exhibit for {resolved.replace('_', ' ')}"
        conds = list(meta.get("conditions") or [])
        if note not in conds:
            conds.append(note)
        meta["conditions"] = conds
        quote.metadata = meta
    return quote
