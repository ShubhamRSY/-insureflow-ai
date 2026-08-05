#!/usr/bin/env python3
"""Ingest downloaded public datasets → ml_data/*.csv and optionally retrain.

Usage:
  PYTHONPATH=src python scripts/ingest_public_datasets.py
  PYTHONPATH=src python scripts/ingest_public_datasets.py --train
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Map public datasets into ml_data and train.")
    parser.add_argument("--external", default="external_data", help="Downloaded data root")
    parser.add_argument("--out", default="ml_data", help="Output CSV directory")
    parser.add_argument("--train", action="store_true", help="Retrain all models after ingest")
    args = parser.parse_args()

    from insureflow.ml.public_datasets import build_from_public_downloads

    report = build_from_public_downloads(
        external_root=Path(args.external),
        out_dir=Path(args.out),
    )
    print(json.dumps(report, indent=2))

    if not args.train:
        return 0 if report.get("ok") else 1

    from insureflow.ml.models import ModelType
    from insureflow.ml.registry import get_ml_registry
    from insureflow.ml.training import QUALITY_GATES, passes_quality_gate, train_all_models

    results = train_all_models(force=True, allow_synthetic=False, data_root=Path(args.out))
    reg = get_ml_registry()
    print("\n=== GATE CHECK (public data) ===")
    service = {
        "loss_prediction": "Insurance",
        "fraud_detection": "Insurance",
        "premium_optimizer": "Insurance",
        "churn_prediction": "Insurance",
        "mortgage_default_risk": "Mortgage",
        "lending_default_risk": "Lending",
    }
    all_pass = True
    for r in results:
        mt = r.model_type if isinstance(r.model_type, ModelType) else ModelType(r.model_type)
        m = reg.get(mt)
        n = int(report["models"].get(mt.value, {}).get("rows", 0))
        passed, reason = passes_quality_gate(mt, r.metrics or {}, n)
        gate = QUALITY_GATES[mt]
        if "val_roc_auc" in gate:
            metric = f"AUC={((r.metrics or {}).get('val_roc_auc') or 0):.3f}"
        else:
            metric = f"R2={((r.metrics or {}).get('val_r2') or 0):.3f}"
        print(
            f"  {service[mt.value]:<10} {mt.value:<22} {metric:<12} "
            f"gate={'PASS' if passed else 'FAIL'} stored={m.gate_passed if m else None} :: {reason}"
        )
        all_pass = all_pass and passed
    print(f"\n  trained={len(results)} all_gates_pass={all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
