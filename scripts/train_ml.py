#!/usr/bin/env python3
"""Train ML models from real labeled data (ml_data/<model_type>.csv).

Synthetic bootstrap is OFF by default — pass --allow-synthetic only for demos/tests.

Usage:
  PYTHONPATH=src python scripts/train_ml.py --status
  PYTHONPATH=src python scripts/train_ml.py --build-data   # build CSVs then train
  PYTHONPATH=src python scripts/train_ml.py                # train all from real CSVs
  PYTHONPATH=src python scripts/train_ml.py --only loss_prediction
  PYTHONPATH=src python scripts/train_ml.py --allow-synthetic  # demo fallback
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

MODEL_LABELS = {
    "loss_prediction": "Insurance expected loss (frequency × severity)",
    "fraud_detection": "Insurance fraud anomaly score",
    "premium_optimizer": "Insurance premium recommendation",
    "churn_prediction": "Insurance non-renewal risk",
    "mortgage_default_risk": "Mortgage default / delinquency risk",
    "lending_default_risk": "Lending default risk (business + consumer)",
}


def _print_status() -> None:
    from insureflow.ml.training import get_training_status

    status = get_training_status()
    for m in status["models"]:
        mt = m["model_type"]
        label = MODEL_LABELS.get(mt, "")
        gate = m.get("gate_passed")
        gate_s = "" if gate is None else f" gate={'PASS' if gate else 'FAIL'}"
        print(f"  {mt:<22} {label:<45} v{m['version']:<8} trained={m['is_trained']} status={m['status']}{gate_s}")
        if m.get("metrics"):
            top = {k: round(v, 4) for k, v in list(m["metrics"].items())[:4]}
            print(f"    metrics: {top}")
    print(f"\n  data_root: {status.get('data_root')}")
    for mt, ds in (status.get("datasets") or {}).items():
        if ds.get("csv_path"):
            print(f"    real data: {mt} -> {ds['csv_path']}")
    if status.get("history"):
        print("\n  training history (tail):")
        for h in status["history"][-5]:
            print(f"    {h['model_type']} v{h['version']} @ {h.get('trained_at', '?')[:19]} :: {h['metrics']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train Rytera ML models from real labeled CSVs.")
    parser.add_argument("--status", action="store_true", help="Print model + dataset status and exit")
    parser.add_argument("--only", choices=sorted(MODEL_LABELS), help="Train only this model type")
    parser.add_argument("--csv", help="Explicit training CSV path (with --only)")
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Allow synthetic bootstrap when a real CSV is missing (demo/tests only)",
    )
    parser.add_argument(
        "--no-synthetic",
        action="store_true",
        default=True,
        help=argparse.SUPPRESS,  # kept for backward compat; real-data is now the default
    )
    parser.add_argument("--build-data", action="store_true", help="Build/refresh ml_data/*.csv before training")
    parser.add_argument("--export", action="store_true", help="Build ml_data/*.csv from audit logs before training")
    parser.add_argument("--data-root", default=None, help="Directory containing ml_data-style CSVs")
    args = parser.parse_args()

    from insureflow.ml.models import ModelType

    if args.status:
        _print_status()
        return 0

    allow_synthetic = bool(args.allow_synthetic)

    if args.build_data:
        from insureflow.ml.seed_datasets import build_all_training_csvs

        report = build_all_training_csvs(out_dir=Path(args.data_root) if args.data_root else Path("ml_data"))
        print("  built training CSVs:")
        for mt, info in (report.get("models") or {}).items():
            print(f"    {mt:<22} rows={info.get('rows')} source={info.get('source')} diverse={info.get('diverse')}")
        if not report.get("ok"):
            print("  WARNING: some datasets are not diverse enough — training may fail quality gates")

    if args.export and not args.build_data:
        from insureflow.ml.export_training import export_from_audit_logs

        for mt in MODEL_LABELS:
            result = export_from_audit_logs(model_type=mt)
            print(f"  export {mt:<22} ok={result['ok']} rows={result['rows']} -> {result.get('path')}")

    if args.only:
        mt = ModelType(args.only)
        from insureflow.ml.training import retrain_model

        try:
            result = retrain_model(
                mt,
                csv_path=args.csv,
                allow_synthetic=allow_synthetic,
            )
        except FileNotFoundError as exc:
            print(f"  FAILED: {exc}")
            print("  Hint: run with --build-data to create labeled CSVs from real claims/audits")
            return 1
        if result is None:
            print(f"  FAILED: {args.only}")
            return 1
        print(f"  trained {args.only} v{result.model_version}: {result.metrics}")
        return 0

    from insureflow.ml.training import train_all_models

    if not allow_synthetic:
        # Ensure CSVs exist before refusing synthetic
        from insureflow.ml.seed_datasets import ensure_training_csvs

        ensure_training_csvs(Path(args.data_root) if args.data_root else Path("ml_data"))

    results = train_all_models(
        force=True,
        data_root=Path(args.data_root) if args.data_root else None,
        allow_synthetic=allow_synthetic,
    )
    if not results:
        print("  No models trained. Provide ml_data/*.csv or pass --allow-synthetic / --build-data")
        return 1
    for r in results:
        print(f"  trained {r.model_type.value} v{r.model_version}: {r.metrics}")
    print(f"\n  {len(results)} model(s) trained (synthetic={'on' if allow_synthetic else 'off'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
