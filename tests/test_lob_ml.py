"""Per-LOB ML training and inference."""

from __future__ import annotations

from insureflow.ml.lob_profiles import lob_loss_fallback, lob_profile, lob_risk_factors, lob_training_seed
from insureflow.ml.lob_registry import get_insurance_model, lob_model_dir
from insureflow.ml.lob_training import build_lob_training_csvs, train_all_lob_models
from insureflow.ml.models import FeatureVector, ModelType


def test_lob_profile_differs_by_category():
    prop = lob_profile("commercial_property")
    cyber = lob_profile("cyber_liability")
    assert prop["category_id"] == "property"
    assert cyber["category_id"] == "liability"
    assert prop["loss_severity_mult"] != cyber["loss_severity_mult"]
    assert prop["uw_focus"] != cyber["uw_focus"]


def test_lob_training_seed_stable():
    assert lob_training_seed("commercial_property") == lob_training_seed("commercial_property")
    assert lob_training_seed("cyber_liability") != lob_training_seed("commercial_property")


def test_lob_loss_fallback_uses_uw_focus():
    fv = FeatureVector(tiv=5_000_000, loss_ratio=0.8, prior_claims_count=2, years_in_business=10)
    _, _, loss_prop = lob_loss_fallback("commercial_property", fv)
    _, _, loss_cyber = lob_loss_fallback("cyber_liability", fv)
    assert loss_prop != loss_cyber


def test_lob_risk_factors_include_line_context():
    fv = FeatureVector(tiv=60_000_000, loss_ratio=1.1, prior_claims_count=4, credit_score=580)
    factors = lob_risk_factors("commercial_property", fv)
    assert any("COPE" in f or "TIV" in f or "loss ratio" in f.lower() for f in factors)


def test_build_and_train_single_lob(tmp_path):
    report = build_lob_training_csvs(out_dir=tmp_path / "lines", samples_per_model=220, refresh_global=False)
    assert report["line_count"] >= 50

    line = "commercial_property"
    results = train_all_lob_models(data_root=tmp_path / "lines", force=True, insurance_lines=[line])
    assert len(results) == 4
    assert all(r["insurance_line"] == line for r in results)
    assert sum(1 for r in results if r.get("gate_passed")) >= 3

    model = get_insurance_model(ModelType.LOSS_PREDICTION, line)
    assert model is not None
    pred = model.predict(FeatureVector(tiv=2_000_000, loss_ratio=0.4, product_line=line))
    assert "expected_loss" in pred
    assert lob_model_dir(line, ModelType.LOSS_PREDICTION).exists()
