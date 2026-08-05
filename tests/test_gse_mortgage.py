"""Gold-standard Fannie/Freddie/HMDA mortgage mappers."""

from __future__ import annotations

from pathlib import Path

from insureflow.ml.features import MORTGAGE_FEATURE_NAMES
from insureflow.ml.gse_mortgage import (
    discover_gse_files,
    load_gold_standard_mortgage,
    map_fannie_loan_performance,
    map_hmda_lar,
)
from insureflow.ml.public_datasets import build_from_public_downloads

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "mortgage" / "gse_sample"


def test_discover_and_map_fannie_sample() -> None:
    found = discover_gse_files(SAMPLE)
    assert found["fannie_acq"]
    rows = map_fannie_loan_performance(found["fannie_acq"], found["fannie_perf"], max_rows=100)
    assert len(rows) >= 5
    defaults = sum(1 for r in rows if r["target"] >= 0.5)
    goods = sum(1 for r in rows if r["target"] < 0.5)
    assert defaults >= 1 and goods >= 1
    for name in MORTGAGE_FEATURE_NAMES:
        assert name in rows[0]


def test_map_hmda_sample() -> None:
    found = discover_gse_files(SAMPLE)
    rows = map_hmda_lar(found["hmda"], max_rows=100)
    assert len(rows) >= 4
    assert any(r["target"] >= 0.5 for r in rows)
    assert any(r["target"] < 0.5 for r in rows)


def test_load_prefers_fannie(tmp_path) -> None:
    rows, label = load_gold_standard_mortgage(SAMPLE)
    assert label == "fannie_mae_loan_performance"
    assert len(rows) >= 5


def test_public_ingest_uses_gse_when_present(tmp_path) -> None:
    external = tmp_path / "external_data"
    mort = external / "mortgage"
    mort.mkdir(parents=True)
    # Copy sample tree
    import shutil

    shutil.copytree(SAMPLE / "fannie", mort / "fannie")
    out = tmp_path / "ml_data"
    report = build_from_public_downloads(external_root=external, out_dir=out)
    assert "fannie" in report["models"]["mortgage_default_risk"]["source"]
    assert report["models"]["mortgage_default_risk"]["rows"] >= 5
    assert (out / "mortgage_default_risk.csv").exists()
