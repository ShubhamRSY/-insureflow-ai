"""Dedicated paths for commercial products that already have an actuarial manual.

One module, many product ids: each id calls the existing rater
(ISO CGL, umbrella, cyber/auto/marine/crime/builders/surety, BOP/CPP).
No second premium formula. Products with no manual stay on leaf filings.
"""

from __future__ import annotations

from insureflow.commercial.lobs.base import CommercialProductContext
from insureflow.rating.commercial_actuarial import (
    rate_extended_commercial,
    rate_general_liability_iso,
    rate_package_policy,
    rate_umbrella,
)
from insureflow.rating.models import InsuranceLine, QuoteResult

LOGIC_PATH = "insureflow.commercial.lobs.extended"

# product id -> (rater key, line the manual expects)
ROUTES: dict[str, tuple[str, InsuranceLine]] = {
    "general_liability": ("gl", InsuranceLine.GENERAL_LIABILITY),
    "product_liability": ("gl", InsuranceLine.GENERAL_LIABILITY),
    "umbrella": ("umbrella", InsuranceLine.UMBRELLA),
    "cyber_liability": ("extended", InsuranceLine.CYBER),
    "tech_eo_cyber": ("extended", InsuranceLine.CYBER),
    "commercial_auto": ("extended", InsuranceLine.COMMERCIAL_AUTO),
    "fleet": ("extended", InsuranceLine.COMMERCIAL_AUTO),
    "hnoa": ("extended", InsuranceLine.COMMERCIAL_AUTO),
    "garage_liability": ("extended", InsuranceLine.COMMERCIAL_AUTO),
    "non_trucking_liability": ("extended", InsuranceLine.COMMERCIAL_AUTO),
    "inland_marine": ("extended", InsuranceLine.INLAND_MARINE),
    "motor_truck_cargo": ("extended", InsuranceLine.INLAND_MARINE),
    "crime": ("extended", InsuranceLine.CRIME),
    "builders_risk": ("extended", InsuranceLine.BUILDERS_RISK),
    "surety_bonds": ("extended", InsuranceLine.SURETY),
    "bop": ("package", InsuranceLine.BOP),
    "cpp": ("package", InsuranceLine.COMMERCIAL_PACKAGE),
}

PRODUCT_IDS = frozenset(ROUTES)


def build_quote(ctx: CommercialProductContext) -> QuoteResult:
    kind, line = ROUTES[ctx.product_id.strip().lower().replace("-", "_").replace(" ", "_")]
    kwargs = {
        "state": ctx.issue_state,
        "schedule_mod_pct": ctx.schedule_mod_pct,
        "market_mod_pct": ctx.market_mod_pct,
    }
    if kind == "gl":
        result = rate_general_liability_iso(ctx.bundle, ctx.memo, **kwargs)
    elif kind == "umbrella":
        result = rate_umbrella(ctx.bundle, ctx.memo, **kwargs)
    elif kind == "package":
        result = rate_package_policy(ctx.bundle, ctx.memo, line, **kwargs)
    else:
        rated = rate_extended_commercial(ctx.bundle, ctx.memo, line, **kwargs)
        result = rated or QuoteResult(
            bundle_id=ctx.bundle.bundle_id,
            line=line,
            eligible=False,
            ineligibility_reasons=[f"No actuarial manual branch for {ctx.product_id}"],
        )
    meta = dict(result.metadata or {})
    meta["lob_logic_path"] = LOGIC_PATH
    meta["product_id"] = ctx.product_id
    meta["product_family"] = kind
    result.metadata = meta
    return result
