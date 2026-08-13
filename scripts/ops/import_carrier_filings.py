#!/usr/bin/env python3
"""Import carrier filed rates from CSV or JSON into carrier_book.live.json.

CSV columns (header required):
  product_id,loss_cost,lcm,minimum_premium,exposure_basis,filing_id,effective_date,name

Example:
  PYTHONPATH=src python scripts/ops/import_carrier_filings.py --csv my_filings.csv
  PYTHONPATH=src python scripts/ops/import_carrier_filings.py --json my_serff.json --carrier "Meridian Mutual"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from insureflow.rating.book_import import filings_from_csv_text, filings_from_json_obj, import_filings  # noqa: E402

DEFAULT_BOOK = ROOT / "data" / "rating" / "carrier_book.live.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="CSV of filed rates")
    parser.add_argument("--json", dest="json_path", help="JSON rate book or filings map")
    parser.add_argument("--book", default=str(DEFAULT_BOOK), help="Target carrier book JSON")
    parser.add_argument("--carrier", default="", help="Carrier name")
    parser.add_argument("--book-id", default="", help="Book identifier")
    args = parser.parse_args()

    if not args.csv and not args.json_path:
        parser.error("Provide --csv or --json")

    if args.csv:
        filings = filings_from_csv_text(Path(args.csv).read_text(encoding="utf-8"))
    else:
        filings = filings_from_json_obj(json.loads(Path(args.json_path).read_text(encoding="utf-8")))

    result = import_filings(
        filings=filings,
        book_path=Path(args.book),
        carrier=args.carrier,
        book_id=args.book_id,
    )
    print(f"Updated {result['filings']} filings → {result['path']} ({result['posture']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
