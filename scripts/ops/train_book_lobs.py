#!/usr/bin/env python3
"""Seed + train LOB models from commercial book outcomes."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from insureflow.ml.book_training import build_lob_training_from_book, seed_book_from_commercial_demos  # noqa: E402
from insureflow.ml.lob_training import train_all_lob_models  # noqa: E402


def main() -> int:
    seed = seed_book_from_commercial_demos(samples_per_model=160)
    print("seeded demo book lines:", seed.get("lines"), list((seed.get("by_line") or {}).keys()))
    report = build_lob_training_from_book(samples_per_model=160)
    print("blended files:", report.get("book_blended_files"), "demo_seed", report.get("demo_seed"))
    lines = list((seed.get("by_line") or {}).keys()) or [
        "cyber_liability",
        "workers_comp",
        "commercial_auto",
        "business_owners_policy",
        "general_liability",
        "builders_risk",
        "crime",
        "surety_bonds",
        "commercial_property",
    ]
    results = train_all_lob_models(force=True, insurance_lines=lines)
    passed = sum(1 for r in results if r.get("gate_passed"))
    print(f"trained {len(results)} passed {passed} ({100 * passed / max(len(results), 1):.0f}%)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
