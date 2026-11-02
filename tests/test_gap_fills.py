"""Gaps the smash reproduced: non-finite premiums, leaked-model gate, split tax and free-look tables."""

from __future__ import annotations

import math

from insureflow.commercial.lobs import CommercialProductContext, run_product_logic
from insureflow.commercial.lobs.state_law import SURPLUS_LINES_TAX
from insureflow.life.lobs.state_law import LIFE_FREE_LOOK_DAYS
from insureflow.ml.export_training import _insurance_target
from insureflow.ml.lob_registry import LOBModelRegistry
from insureflow.ml.loss_prediction import LossPredictionModel
from insureflow.ml.models import ModelStatus, ModelType
from insureflow.ml.training import passes_quality_gate
from insureflow.models.agents import Recommendation, UnderwritingMemo, UWDecision
from insureflow.models.submissions import (
    FinancialData,
    LocationData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
    UnstructuredSubmission,
)
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.models import InsuranceLine
from insureflow.regulatory.state_rules import StateRegulatoryEngine
from insureflow.underwriting.surplus_lines import classify_surplus_lines


def _memo() -> UnderwritingMemo:
    return UnderwritingMemo(
        bundle_id="gap",
        decision=UWDecision.ACCEPT,
        summary="gap",
        recommendation=Recommendation(action="accept", rationale="gap"),
    )


def _property(bldg: float) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="gap",
        structured=StructuredSubmission(
            submission_id="gap",
            named_insured=NamedInsured(legal_name="Gap Co"),
            locations=[LocationData(address="1", city="X", state="IL", zip_code="60601", building_value=bldg, contents_value=bldg)],
            financial=FinancialData(annual_revenue=5_000_000, payroll=1_000_000),
            risk_profile=RiskProfile(naics_code="336111"),
        ),
    )


def test_infinite_and_nan_property_are_not_eligible():
    engine = InsuranceRatingEngine()
    for bldg in (math.inf, math.nan, 1e18):
        quote = engine.quote(_property(bldg), _memo(), line=InsuranceLine.COMMERCIAL_PROPERTY, commercial_product_id="property_bi")
        assert quote.eligible is False
        assert quote.adjusted_premium == 0.0
        assert math.isfinite(quote.base_premium)


def test_infinite_bop_premium_is_not_eligible():
    bundle = _property(math.inf)
    ctx = CommercialProductContext(
        bundle=bundle,
        memo=_memo(),
        line=InsuranceLine.BOP,
        state_code="IL",
        product_id="bop",
    )
    quote = run_product_logic(ctx)
    assert quote is not None
    assert quote.eligible is False
    assert quote.adjusted_premium == 0.0


def test_quality_gate_rejects_nan_and_perfect_leakage():
    nan_r2, _ = passes_quality_gate(ModelType.LOSS_PREDICTION, {"val_r2": float("nan")}, 500)
    leaked, _ = passes_quality_gate(ModelType.LOSS_PREDICTION, {"val_r2": 0.999}, 500)
    ok, _ = passes_quality_gate(ModelType.LOSS_PREDICTION, {"val_r2": 0.4}, 500)
    nan_auc, _ = passes_quality_gate(ModelType.FRAUD_DETECTION, {"val_roc_auc": float("nan")}, 500)
    assert nan_r2 is False
    assert leaked is False
    assert ok is True
    assert nan_auc is False


def test_surplus_tax_api_matches_commercial_table():
    engine = StateRegulatoryEngine()
    for state, rate in SURPLUS_LINES_TAX.items():
        rule = engine.get_rule(state)
        assert rule is not None
        assert rule.surplus_lines_tax_rate == rate
    explicit = SubmissionBundle(
        bundle_id="sl",
        unstructured=[UnstructuredSubmission(submission_id="u", raw_text="surplus lines non-admitted placement")],
    )
    classified = classify_surplus_lines(explicit, line=InsuranceLine.ERRORS_AND_OMISSIONS, state="FL", product_id="errors_omissions")
    assert classified.status == "surplus_lines"
    assert classified.sl_tax_rate == SURPLUS_LINES_TAX["FL"]


def test_life_free_look_follows_statute_table():
    engine = StateRegulatoryEngine()
    for state, days in (("AK", 20), ("CO", 15), ("FL", 14), ("RI", 20), ("WY", 30)):
        rule = engine.get_line_rule(state, "life")
        assert rule is not None
        assert rule.data["free_look_period_days"] == days
        assert days == LIFE_FREE_LOOK_DAYS[state]


def test_loss_export_target_is_ratio_times_premium():
    target = _insurance_target(
        {"tiv": 1_000_000, "quote": {"adjusted_premium": 10_000}},
        "loss_prediction",
        {"structured": {"financial": {"loss_run": {"total_incurred": 5_000, "earned_premium": 10_000}}}},
    )
    assert target == 5_000


def test_ungated_lob_model_does_not_block_a_clean_fallback():
    registry = LOBModelRegistry()
    bad = LossPredictionModel()
    bad.model = object()
    bad.status = ModelStatus.CHAMPION
    bad.gate_passed = False
    registry._cache[("commercial_property", ModelType.LOSS_PREDICTION)] = bad
    got = registry.get(ModelType.LOSS_PREDICTION, "commercial_property")
    assert got is not bad
    assert got is not None
    assert got.is_trained is False or got.gate_passed is True
