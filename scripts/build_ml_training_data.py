#!/usr/bin/env python3
"""Build real labeled ml_data/*.csv for all classical ML models.

Usage:
  PYTHONPATH=src python scripts/build_ml_training_data.py
  PYTHONPATH=src python scripts/build_ml_training_data.py --out ml_data
  PYTHONPATH=src python scripts/train_ml.py --build-data --no-synthetic
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build labeled training CSVs from real claims + audits.")
    parser.add_argument("--out", default="ml_data", help="Output directory for CSVs")
    parser.add_argument("--claims", default=None, help="Path to Wisconsin (or similar) claims CSV")
    parser.add_argument("--audit-root", default=None, help="Audit logs root (default: ./audit_logs)")
    args = parser.parse_args()

    from insureflow.ml.seed_datasets import build_all_training_csvs

    report = build_all_training_csvs(
        out_dir=Path(args.out),
        claims_csv=Path(args.claims) if args.claims else None,
        audit_root=Path(args.audit_root) if args.audit_root else None,
    )
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
