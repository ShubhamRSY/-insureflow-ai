#!/usr/bin/env python3
"""Import carrier filed rates from CSV into carrier_book.live.json.

CSV columns (header required):
  product_id,loss_cost,lcm,minimum_premium,exposure_basis,filing_id,effective_date

Example:
  PYTHONPATH=src python scripts/ops/import_carrier_filings.py --csv my_filings.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_BOOK = ROOT / "data" / "rating" / "carrier_book.live.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="CSV of filed rates")
    parser.add_argument("--book", default=str(DEFAULT_BOOK), help="Target carrier book JSON")
    args = parser.parse_args()

    book_path = Path(args.book)
    book = json.loads(book_path.read_text()) if book_path.exists() else {"filings": {}, "book_id": "imported"}
    filings = dict(book.get("filings") or {})

    with Path(args.csv).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        n = 0
        for row in reader:
            pid = (row.get("product_id") or "").strip().lower()
            if not pid:
                continue
            cur = dict(filings.get(pid) or {"product_id": pid})
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
            cur["source"] = "carrier_csv_import"
            filings[pid] = cur
            n += 1

    book["filings"] = filings
    book["product_count"] = len(filings)
    book["posture"] = "carrier_imported"
    book["version"] = str(book.get("version") or "imported")
    book_path.parent.mkdir(parents=True, exist_ok=True)
    book_path.write_text(json.dumps(book, indent=2))
    print(f"Updated {n} filings → {book_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
