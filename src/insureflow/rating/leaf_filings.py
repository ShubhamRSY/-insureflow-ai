"""Per-product leaf filings loaded from the carrier rate book.

Every commercial catalog product_id has a unique filing (loss cost, LCM, min,
exposure basis). Dedicated manuals (WC NCCI, cyber, auto, packages, etc.) still
win when they apply; leaf filings cover the remaining catalog leaves so UW math
is product-specific rather than a shared parent proxy.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from insureflow.insurance.commercial_lobs import COMMERCIAL_LINES, get_commercial_line
from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.underwriting.personal_lines import _blob, parse_insurance_line

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_BOOK = _REPO_ROOT / "data" / "rating" / "carrier_book.json"
_LIVE_BOOK = _REPO_ROOT / "data" / "rating" / "carrier_book.live.json"


def _resolve_book_path(path: str | None = None) -> Path:
    """Prefer explicit path → CARRIER_BOOK_PATH → carrier_book.live.json → carrier_book.json."""
    import os

    if path:
        return Path(path)
    env_path = (os.getenv("CARRIER_BOOK_PATH") or "").strip()
    if env_path:
        return Path(env_path)
    if _LIVE_BOOK.exists():
        return _LIVE_BOOK
    return _DEFAULT_BOOK


@lru_cache(maxsize=8)
def load_carrier_book(path: str | None = None) -> dict[str, Any]:
    book_path = _resolve_book_path(path)
    if not book_path.exists():
        logger.warning("Carrier book missing at %s — leaf filings unavailable", book_path)
        return {"filings": {}, "book_id": "missing", "path": str(book_path)}
    with book_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return {"filings": {}, "book_id": "invalid", "path": str(book_path)}
    data["_loaded_from"] = str(book_path)
    return cast(dict[str, Any], data)


def clear_carrier_book_cache() -> None:
    load_carrier_book.cache_clear()


def get_leaf_filing(product_id: str | None) -> dict[str, Any] | None:
    if not product_id:
        return None
    book = load_carrier_book()
    filings = book.get("filings") or {}
    key = str(product_id).strip().lower()
    if key in filings:
        return dict(filings[key])
    # Try catalog resolution
    line = get_commercial_line(key)
    if line and line["id"] in filings:
        return dict(filings[line["id"]])
    return None


def list_leaf_filings() -> list[dict[str, Any]]:
    book = load_carrier_book()
    return list((book.get("filings") or {}).values())


def carrier_book_status() -> dict[str, Any]:
    book = load_carrier_book()
    filings = book.get("filings") or {}
    catalog_ids = {str(line["id"]) for line in COMMERCIAL_LINES}
    covered = catalog_ids & set(filings.keys())
    return {
        "book_id": book.get("book_id"),
        "carrier": book.get("carrier"),
        "version": book.get("version"),
        "effective_date": book.get("effective_date"),
        "posture": book.get("posture", "pilot"),
        "catalog_products": len(catalog_ids),
        "filings": len(filings),
        "coverage_pct": round(100.0 * len(covered) / max(len(catalog_ids), 1), 1),
        "missing_product_ids": sorted(catalog_ids - set(filings.keys())),
        "path": book.get("_loaded_from") or str(_resolve_book_path()),
        "replace_with": "Set CARRIER_BOOK_PATH to your SERFF/filed JSON or overwrite data/rating/carrier_book.live.json",
    }


def _exposure_for_basis(bundle: SubmissionBundle, basis: str, filing: dict[str, Any]) -> tuple[float, str]:
    """Return (exposure_amount, unit_label) for the filing basis."""
    from insureflow.rating.commercial_actuarial import (
        _employees,
        _limit,
        _money,
        _payroll,
        _tiv,
        _vehicle_count,
    )

    blob = _blob(bundle)
    basis = (basis or "tiv").lower()

    if basis in ("payroll", "remuneration"):
        return _payroll(bundle), "payroll"
    if basis in ("power_units", "vehicles", "units"):
        return float(_vehicle_count(bundle)), "power_units"
    if basis in ("limit", "policy_limit"):
        return _limit(bundle, 1_000_000.0), "limit"
    if basis in ("completed_value", "builders"):
        v = _tiv(bundle) or _money(blob, "completed value", "contract value", "project value")
        return max(v, 500_000.0), "completed_value"
    if basis in ("scheduled_values", "cargo", "marine"):
        v = _tiv(bundle) or _money(blob, "scheduled values", "cargo value", "insured values")
        return max(v, 100_000.0), "scheduled_values"
    if basis in ("bond_penalty", "bond_amount"):
        v = _money(blob, "bond amount", "bond penalty", "penal sum", "contract value") or _tiv(bundle)
        return max(v, 100_000.0), "bond_penalty"
    if basis in ("employees_x_limit", "fidelity"):
        emp = float(_employees(bundle))
        lim = _limit(bundle, 250_000.0)
        return emp * (lim / 100.0), "employees_x_limit"
    if basis in ("employees",):
        return float(_employees(bundle)), "employees"
    if basis in ("receivables", "ar"):
        v = _money(blob, "accounts receivable", "receivables", "ar balance") or _tiv(bundle)
        if bundle.structured and bundle.structured.financial:
            v = max(v, float(getattr(bundle.structured.financial, "accounts_receivable", 0) or 0))
            v = max(v, float(getattr(bundle.structured.financial, "annual_revenue", 0) or 0) * 0.15)
        return max(v, 250_000.0), "receivables"
    if basis in ("benefit_amount", "face_amount"):
        v = _money(blob, "benefit amount", "face amount", "key person amount", "coverage amount") or _limit(bundle)
        return max(v, 500_000.0), "benefit_amount"
    if basis in ("contract_value",):
        v = _money(blob, "contract value", "project value", "exposure") or _tiv(bundle)
        return max(v, 250_000.0), "contract_value"
    # default TIV
    return max(_tiv(bundle), 500_000.0), "tiv"


def _line_enum(filing: dict[str, Any]) -> InsuranceLine:
    for key in (filing.get("insurance_line"), filing.get("parent_manual"), filing.get("product_id")):
        parsed = parse_insurance_line(str(key or ""))
        if parsed is not None:
            return parsed
    return InsuranceLine.COMMERCIAL_PROPERTY


def rate_leaf_filing(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    product_id: str,
    *,
    state: str = "",
    schedule_mod_pct: float = 0.0,
    market_mod_pct: float = 0.0,
) -> QuoteResult | None:
    """Rate a commercial catalog leaf from the carrier book filing."""
    filing = get_leaf_filing(product_id)
    if not filing:
        return None

    basis = str(filing.get("exposure_basis") or "tiv")
    exposure, unit = _exposure_for_basis(bundle, basis, filing)
    loss_cost = float(filing.get("loss_cost") or 0.4)
    lcm = float(filing.get("lcm") or 2.0)
    minimum = float(filing.get("minimum_premium") or 500.0)

    state_u = (state or "").upper()
    state_rel = float((filing.get("state_relativities") or {}).get(state_u, 1.0))

    # Compute base by exposure basis
    if basis in ("power_units", "vehicles", "units", "employees"):
        base = exposure * loss_cost * lcm * state_rel
    elif basis in ("bond_penalty",):
        # loss_cost is percent of bond
        base = exposure * (loss_cost / 100.0) * state_rel
    elif basis in ("payroll", "remuneration"):
        base = (exposure / 100.0) * loss_cost * state_rel
    elif basis in ("employees_x_limit",):
        base = exposure * loss_cost * lcm * state_rel / 100.0
    else:
        # per $100 of TIV / limit / values
        base = (exposure / 100.0) * loss_cost * lcm * state_rel

    # Apply schedule credits from filing + UW schedule
    schedule_credits = filing.get("schedule_credits") or {}
    blob = _blob(bundle).lower()
    schedule_pct = 0.0
    applied: list[str] = []
    for name, pct in schedule_credits.items():
        token = name.replace("_", " ")
        if token in blob or name in blob:
            schedule_pct += float(pct) * 100.0
            applied.append(name)
    schedule_pct += float(schedule_mod_pct or 0.0)

    adjusted = base * (1 + market_mod_pct / 100.0) * (1 + schedule_pct / 100.0)
    adjusted = max(round(adjusted, 2), minimum)

    line = _line_enum(filing)
    components = [
        RateComponent("leaf_loss_cost", loss_cost, f"filing_{filing.get('filing_id', product_id)}"),
        RateComponent("leaf_lcm", lcm, "expense_profit"),
        RateComponent("state_relativity", state_rel, "state"),
        RateComponent("exposure", round(exposure, 2), unit),
    ]
    if schedule_pct:
        components.append(RateComponent("schedule", schedule_pct, "uw_schedule", schedule_pct))

    book = load_carrier_book()
    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=line,
        base_premium=round(base, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / max(exposure / 100.0, 1.0), 4) if exposure else 0.0,
        eligible=True,
        metadata={
            "rating_engine": "carrier_leaf_filing",
            "product_id": filing.get("product_id"),
            "filing_id": filing.get("filing_id"),
            "parent_manual": filing.get("parent_manual"),
            "exposure_basis": unit,
            "exposure": exposure,
            "loss_cost": loss_cost,
            "lcm": lcm,
            "state_relativity": state_rel,
            "schedule_credits_applied": applied,
            "carrier_book_id": book.get("book_id"),
            "carrier": book.get("carrier"),
            "rate_book_posture": book.get("posture"),
            "serff_tracking": filing.get("serff_tracking") or filing.get("filing_id"),
            "insurance_line": line.value,
            "source": filing.get("source"),
        },
    )


# Products that keep dedicated actuarial manuals (not leaf-only).
DEDICATED_MANUAL_PRODUCTS = frozenset(
    {
        "workers_comp",
        "employers_liability",
        "cyber_liability",
        "tech_eo_cyber",
        "commercial_auto",
        "fleet",
        "hnoa",
        "garage_liability",
        "non_trucking_liability",
        "inland_marine",
        "motor_truck_cargo",
        "crime",
        "builders_risk",
        "surety_bonds",
        "bop",
        "business_owners_policy",
        "cpp",
        "commercial_package",
    }
)


def should_use_leaf_filing(product_id: str | None, line: InsuranceLine | None = None) -> bool:
    """Leaf filings apply for catalog products without a dedicated manual branch.

    A customer SERFF import wins over hardcoded dedicated manuals (WC, cyber, auto, …).
    The InsureFlow pilot book does not — dedicated actuarial tables still apply there.
    """
    if not product_id:
        return False
    pid = product_id.strip().lower()
    filing = get_leaf_filing(pid)
    if filing is None:
        line_obj = get_commercial_line(pid)
        if line_obj:
            pid = str(line_obj["id"])
            filing = get_leaf_filing(pid)
    if not filing:
        return False
    from insureflow.billing.plan import is_customer_rate_book

    if is_customer_rate_book(carrier_book_status()):
        return True
    if pid in DEDICATED_MANUAL_PRODUCTS:
        return False
    line_obj = get_commercial_line(pid)
    if line_obj and line_obj["id"] in DEDICATED_MANUAL_PRODUCTS:
        return False
    return True
