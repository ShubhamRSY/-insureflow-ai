"""Import a carrier's filed rates (JSON or CSV) into the live rate book."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from insureflow.rating.leaf_filings import _LIVE_BOOK, clear_carrier_book_cache


def import_filings(
    *,
    filings: dict[str, Any],
    book_path: Path | None = None,
    carrier: str = "",
    book_id: str = "",
    effective_date: str = "",
) -> dict[str, Any]:
    path = book_path or _LIVE_BOOK
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if not isinstance(existing, dict):
            existing = {}
    merged = dict(existing.get("filings") or {})
    for pid, row in filings.items():
        key = str(pid).strip().lower()
        if not key:
            continue
        cur = dict(merged.get(key) or {"product_id": key})
        cur.update(row)
        cur["product_id"] = key
        cur["source"] = cur.get("source") or "carrier_import"
        merged[key] = cur

    book = {
        **existing,
        "book_id": book_id or existing.get("book_id") or f"carrier-{path.stem}",
        "carrier": carrier or existing.get("carrier") or "customer",
        "version": str(existing.get("version") or "imported"),
        "effective_date": effective_date or existing.get("effective_date") or datetime.now(tz=timezone.utc).date().isoformat(),
        "posture": "carrier_imported",
        "product_count": len(merged),
        "filings": merged,
        "imported_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, indent=2), encoding="utf-8")
    clear_carrier_book_cache()
    return {"ok": True, "path": str(path), "filings": len(merged), "posture": "carrier_imported", "book_id": book["book_id"]}


def filings_from_csv_text(text: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(text))
    out: dict[str, Any] = {}
    for row in reader:
        pid = (row.get("product_id") or "").strip().lower()
        if not pid:
            continue
        cur: dict[str, Any] = {"product_id": pid}
        if row.get("loss_cost"):
            cur["loss_cost"] = float(row["loss_cost"])
        if row.get("lcm"):
            cur["lcm"] = float(row["lcm"])
        if row.get("minimum_premium"):
            cur["minimum_premium"] = float(row["minimum_premium"])
        if row.get("exposure_basis"):
            cur["exposure_basis"] = row["exposure_basis"].strip()
        if row.get("filing_id"):
            cur["filing_id"] = row["filing_id"].strip()
            cur["serff_tracking"] = row["filing_id"].strip()
        if row.get("effective_date"):
            cur["effective_date"] = row["effective_date"].strip()
        if row.get("name"):
            cur["name"] = row["name"].strip()
        out[pid] = cur
    return out


def filings_from_json_obj(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("filings"), dict):
        return {str(k).lower(): dict(v) for k, v in data["filings"].items()}
    if isinstance(data, dict):
        return {str(k).lower(): (dict(v) if isinstance(v, dict) else {"product_id": str(k)}) for k, v in data.items()}
    if isinstance(data, list):
        out: dict[str, Any] = {}
        for row in data:
            if not isinstance(row, dict):
                continue
            pid = str(row.get("product_id") or "").strip().lower()
            if pid:
                out[pid] = dict(row)
        return out
    raise ValueError("Unrecognized rate book JSON — expected {filings: {...}} or a product map")


def current_book_status() -> dict[str, Any]:
    from insureflow.billing.plan import current_plan, is_customer_rate_book
    from insureflow.rating.leaf_filings import carrier_book_status

    status = carrier_book_status()
    plan = current_plan()
    customer = is_customer_rate_book(status)
    return {
        **status,
        "plan_id": plan.plan_id,
        "is_customer_book": customer,
        "demo_book_allowed": plan.allow_demo_rate_book,
        "carrier_book_required": plan.require_carrier_book,
        "ready_for_plan": (not plan.require_carrier_book) or customer,
    }
