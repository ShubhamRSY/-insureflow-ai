"""Build LOB ML training from the carrier book of underwriting outcomes (audit_logs).

Prefers real pipeline exports over WI/synthetic priors so models reflect the desk's book.
"""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from insureflow.ml.export_training import export_from_audit_logs, _insurance_row, _insurance_target, _iter_insurance_dir
from insureflow.ml.features import DEFAULT_FEATURE_NAMES, get_model_feature_names
from insureflow.ml.lob_training import (
    DEFAULT_LOB_DATA_ROOT,
    LOB_SAMPLES_PER_MODEL,
    _lob_csv_path,
    _rows_from_global_base,
    _write_lob_csv,
    build_lob_training_csvs,
    train_all_lob_models,
)
from insureflow.ml.seed_datasets import DEFAULT_OUT_DIR

logger = logging.getLogger(__name__)


def _line_from_record(summary: dict[str, Any], bundle: dict[str, Any]) -> str:
    for key in (
        summary.get("insurance_line"),
        summary.get("resolved_line"),
        summary.get("product_line"),
        summary.get("commercial_product_id"),
        (summary.get("quote") or {}).get("insurance_line"),
        (summary.get("quote") or {}).get("line"),
        ((summary.get("quote") or {}).get("metadata") or {}).get("insurance_line"),
        ((summary.get("quote") or {}).get("metadata") or {}).get("product_id"),
    ):
        if key:
            return str(key).strip().lower().replace("-", "_")

    # Infer from rating engine when older audits omit insurance_line
    engine = str((summary.get("quote") or {}).get("rating_engine") or ((summary.get("quote") or {}).get("metadata") or {}).get("rating_engine") or "")
    engine_map = {
        "cyber_manual": "cyber_liability",
        "commercial_auto_manual": "commercial_auto",
        "ncci_class_emod": "workers_comp",
        "package_section_rating": "business_owners_policy",
        "builders_risk_manual": "builders_risk",
        "crime_fidelity_manual": "crime",
        "surety_rate_manual": "surety_bonds",
        "inland_marine_manual": "inland_marine",
        "iso_gl_sales": "general_liability",
        "carrier_leaf_filing": str(((summary.get("quote") or {}).get("metadata") or {}).get("product_id") or "commercial_property"),
    }
    if engine in engine_map:
        return engine_map[engine]

    structured = bundle.get("structured") or {}
    coverages = structured.get("coverages") or []
    if coverages and isinstance(coverages[0], dict) and coverages[0].get("line"):
        return str(coverages[0]["line"]).strip().lower().replace("-", "_")
    return "commercial_property"


def export_book_by_lob(
    audit_root: Path | str | None = None,
    *,
    out_dir: Path | str | None = None,
    model_types: tuple[str, ...] = ("loss_prediction", "premium_optimizer"),
) -> dict[str, Any]:
    """Export audit_logs into ml_data/book/lines/<insurance_line>/<model>.csv."""
    root = Path(audit_root or Path.cwd() / "audit_logs")
    dest_root = Path(out_dir or Path.cwd() / "ml_data" / "book" / "lines")
    dest_root.mkdir(parents=True, exist_ok=True)

    by_line: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    scanned = 0
    used = 0

    for path in sorted(root.rglob("pipeline_summary.json")):
        scanned += 1
        record = _iter_insurance_dir(path.parent)
        if record is None:
            continue
        line = _line_from_record(record["summary"], record["bundle"])
        for mt in model_types:
            target = _insurance_target(record["summary"], mt, record["bundle"])
            if target is None:
                continue
            feature_names = get_model_feature_names(mt)
            row = _insurance_row(record["summary"], record["bundle"], feature_names, target)
            by_line[line][mt].append(row)
            used += 1

    written: dict[str, Any] = {}
    for line, models in by_line.items():
        written[line] = {}
        for mt, rows in models.items():
            path = dest_root / line / f"{mt}.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            fieldnames = get_model_feature_names(mt) + ["target"]
            with path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: row.get(k, 0.0) for k in fieldnames})
            written[line][mt] = {"rows": len(rows), "path": str(path)}

    return {
        "ok": True,
        "scanned_summaries": scanned,
        "rows_used": used,
        "lines": len(written),
        "out_dir": str(dest_root),
        "by_line": written,
    }


def build_lob_training_from_book(
    *,
    audit_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    samples_per_model: int = LOB_SAMPLES_PER_MODEL,
    book_weight: float = 0.65,
) -> dict[str, Any]:
    """Build LOB CSVs with majority weight on book (audit) outcomes, rest synthetic prior."""
    import numpy as np

    book_report = export_book_by_lob(audit_root)
    try:
        demo_seed = seed_book_from_commercial_demos(out_dir=book_report["out_dir"], samples_per_model=samples_per_model)
        book_report["demo_seed"] = {"lines": demo_seed.get("lines"), "by_line": list((demo_seed.get("by_line") or {}).keys())}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Demo book seed skipped: %s", exc)
        demo_seed = {}
    root = Path(out_dir or DEFAULT_LOB_DATA_ROOT)
    book_root = Path(book_report["out_dir"])
    # Also refresh global export for blend base
    for mt in ("loss_prediction", "premium_optimizer", "fraud_detection", "churn_prediction"):
        try:
            export_from_audit_logs(model_type=mt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Global book export %s failed: %s", mt, exc)

    # Start from synthetic/profile LOB builder then overwrite with book-heavy blend
    base = build_lob_training_csvs(out_dir=root, samples_per_model=samples_per_model, refresh_global=False)

    blended_lines = 0
    for line_dir in book_root.iterdir() if book_root.exists() else []:
        if not line_dir.is_dir():
            continue
        insurance_line = line_dir.name
        for mt_csv in line_dir.glob("*.csv"):
            mt = mt_csv.stem
            book_rows: list[dict[str, Any]] = []
            with mt_csv.open(newline="", encoding="utf-8") as fh:
                book_rows = list(csv.DictReader(fh))
            if len(book_rows) < 8:
                continue
            n_book = min(int(samples_per_model * book_weight), len(book_rows) * 8)
            # Upsample book rows
            rows: list[dict[str, Any]] = []
            rng = np.random.RandomState(abs(hash(insurance_line + mt)) % (2**31))
            for i in range(n_book):
                src = book_rows[i % len(book_rows)]
                row = {k: float(src.get(k, 0.0) or 0.0) for k in DEFAULT_FEATURE_NAMES}
                # light noise so GBM generalizes
                for k in list(row.keys()):
                    if row[k] != 0:
                        row[k] *= 1.0 + float(rng.normal(0, 0.03))
                row["target"] = float(src.get("target", 0.0) or 0.0)
                rows.append(row)
            # Fill remainder with profile synthetic
            need = max(samples_per_model - len(rows), 0)
            if need:
                global_csv = DEFAULT_OUT_DIR / f"{mt}.csv"
                rows.extend(
                    _rows_from_global_base(global_csv, insurance_line, mt, n_target=need)
                )
            path = _lob_csv_path(root, insurance_line, mt)
            _write_lob_csv(path, rows[:samples_per_model])
            blended_lines += 1

    base["book_export"] = book_report
    base["book_blended_files"] = blended_lines
    base["book_weight"] = book_weight
    base["mode"] = "book_first"
    return base


def seed_book_from_commercial_demos(
    *,
    out_dir: Path | str | None = None,
    samples_per_model: int = LOB_SAMPLES_PER_MODEL,
) -> dict[str, Any]:
    """Run commercial demo pipelines and write book LOB CSVs from live outcomes."""
    from insureflow.api import main as api_main
    from insureflow.insurance.pipeline import InsurancePipeline
    from insureflow.ml.features import get_model_feature_names

    loaders = {
        "cyber_liability": api_main._load_novapay_cyber_submission,
        "commercial_auto": api_main._load_ridgehaul_auto_submission,
        "workers_comp": api_main._load_summit_wc_submission,
        "general_liability": api_main._load_oaksteel_gl_submission,
        "business_owners_policy": api_main._load_corner_bop_submission,
        "builders_risk": api_main._load_harbor_builders_submission,
        "crime": api_main._load_ledger_crime_submission,
        "surety_bonds": api_main._load_apex_surety_submission,
    }
    dest_root = Path(out_dir or Path.cwd() / "ml_data" / "book" / "lines")
    by_line: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    for line_key, loader in loaders.items():
        req = loader()
        docs = []
        for d in req.documents or []:
            docs.append(d.model_dump() if hasattr(d, "model_dump") else d)
        pipe = InsurancePipeline(org_id="book-seed", use_llm=False)
        summary = pipe.run(
            documents=docs,
            insurance_line=req.insurance_line,
            commercial_product_id=getattr(req, "commercial_product_id", None),
        )
        # Minimal bundle dict for feature extraction
        bundle = {
            "structured": {
                "financial": {"annual_revenue": 5_000_000, "payroll": 2_000_000},
                "locations": [{"building_value": 2_000_000, "contents_value": 500_000}],
                "risk_profile": {"prior_claims": []},
                "coverages": [],
                "schedule_of_values": [],
            }
        }
        line = _line_from_record(summary, bundle) or line_key
        for mt in ("loss_prediction", "premium_optimizer"):
            target = _insurance_target(summary, mt, bundle)
            if target is None:
                prem = float((summary.get("quote") or {}).get("adjusted_premium") or 0)
                target = prem * 0.65 if mt == "loss_prediction" else prem
            feature_names = get_model_feature_names(mt)
            row = _insurance_row(summary, bundle, feature_names, float(target))
            # Upsample so LOB training has enough rows
            for i in range(max(40, samples_per_model // 8)):
                clone = dict(row)
                clone["tiv"] = float(clone.get("tiv") or 1_000_000) * (0.9 + (i % 10) * 0.02)
                clone["target"] = float(target) * (0.9 + (i % 10) * 0.02)
                by_line[line][mt].append(clone)

    written = {}
    for line, models in by_line.items():
        written[line] = {}
        for mt, rows in models.items():
            path = dest_root / line / f"{mt}.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            fieldnames = get_model_feature_names(mt) + ["target"]
            with path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: row.get(k, 0.0) for k in fieldnames})
            written[line][mt] = {"rows": len(rows), "path": str(path)}

    return {"ok": True, "lines": len(written), "by_line": written, "out_dir": str(dest_root)}


def train_lob_models_from_book(
    *,
    audit_root: Path | str | None = None,
    force: bool = True,
    seed_demos: bool = True,
) -> dict[str, Any]:
    report = build_lob_training_from_book(audit_root=audit_root)
    # Optionally train only lines that have book CSVs for speed; default all production lines
    results = train_all_lob_models(force=force)
    passed = sum(1 for r in results if r.get("gate_passed"))
    return {
        "build": report,
        "trained": len(results),
        "gate_passed": passed,
        "pass_rate": round(100.0 * passed / max(len(results), 1), 1),
        "results_sample": results[:12],
        "seed_demos": seed_demos,
    }
