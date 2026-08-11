#!/usr/bin/env python3
"""Run realistic multi-condition insurance submission scenarios.

Usage:
  PYTHONPATH=src python scripts/pilot/run_realworld_scenarios.py
  PYTHONPATH=src python scripts/pilot/run_realworld_scenarios.py --only coastal_fl_appetite_decline
  PYTHONPATH=src python scripts/pilot/run_realworld_scenarios.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from insureflow.testing.realworld_scenarios import (  # noqa: E402
    build_all_scenarios,
    run_all_scenarios,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Real-world insurance condition matrix")
    parser.add_argument("--only", help="Run a single scenario id")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--condition", help="Filter by condition: decline|refer|accept_path|missing_data|conditional")
    args = parser.parse_args()

    def filt(s):  # type: ignore[no-untyped-def]
        if args.only and s.id != args.only:
            return False
        if args.condition and s.condition != args.condition:
            return False
        return True

    print(f"Running {sum(1 for s in build_all_scenarios() if filt(s))} real-world scenarios…\n")
    rows = run_all_scenarios(filter_fn=filt)

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        width = max(len(r["id"]) for r in rows) if rows else 10
        for r in rows:
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"[{mark}] {r['id']:<{width}}  decision={r['decision']!s:<20} appetite={r['appetite_passed']} review={r['human_review']}")
            for f in r["failures"]:
                print(f"       → {f}")
        passed = sum(1 for r in rows if r["passed"])
        print(f"\n{passed}/{len(rows)} scenarios passed")

    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
