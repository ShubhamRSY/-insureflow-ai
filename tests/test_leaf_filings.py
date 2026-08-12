"""Leaf filings + full commercial pipeline smoke (in-process)."""

from __future__ import annotations

from insureflow.insurance.commercial_lobs import COMMERCIAL_LINES
from insureflow.models.agents import Recommendation, UnderwritingMemo
from insureflow.models.submissions import (
    FinancialData,
    LocationData,
    NamedInsured,
    RiskProfile,
    StructuredSubmission,
    SubmissionBundle,
)
from insureflow.rating.engine import InsuranceRatingEngine
from insureflow.rating.leaf_filings import carrier_book_status, get_leaf_filing, rate_leaf_filing
from insureflow.rating.models import InsuranceLine


def test_carrier_book_covers_all_catalog_products():
    status = carrier_book_status()
    assert status["filings"] >= 59
    assert status["coverage_pct"] == 100.0
    assert not status["missing_product_ids"]


def test_leaf_filings_have_unique_loss_costs():
    costs = []
    for line in COMMERCIAL_LINES:
        f = get_leaf_filing(line["id"])
        assert f is not None, line["id"]
        costs.append(f["loss_cost"])
    assert len(set(costs)) == len(costs)


def test_sibling_products_price_differently():
    memo = UnderwritingMemo(
        bundle_id="leaf",
        recommendation=Recommendation(suggested_premium_modification=0.0),
    )
    s = StructuredSubmission(
        submission_id="s",
        named_insured=NamedInsured(legal_name="Leaf Co"),
        locations=[LocationData(address="1 Main", city="Austin", state="TX", zip_code="78701", building_value=3_000_000, contents_value=500_000)],
        financial=FinancialData(annual_revenue=8_000_000, payroll=1_500_000),
        risk_profile=RiskProfile(),
    )
    b = SubmissionBundle(bundle_id="leaf", structured=s)
    q_flood = rate_leaf_filing(b, memo, "flood_commercial", state="TX")
    q_quake = rate_leaf_filing(b, memo, "earthquake_commercial", state="TX")
    assert q_flood and q_quake
    assert q_flood.metadata["rating_engine"] == "carrier_leaf_filing"
    assert q_flood.adjusted_premium != q_quake.adjusted_premium


def test_engine_uses_leaf_for_catalog_product():
    memo = UnderwritingMemo(
        bundle_id="eng",
        recommendation=Recommendation(suggested_premium_modification=0.0),
    )
    s = StructuredSubmission(
        submission_id="s",
        named_insured=NamedInsured(legal_name="Eng Co"),
        locations=[LocationData(address="1 Main", city="Austin", state="TX", zip_code="78701", building_value=2_000_000, contents_value=400_000)],
        financial=FinancialData(annual_revenue=5_000_000),
    )
    b = SubmissionBundle(bundle_id="eng", structured=s)
    engine = InsuranceRatingEngine()
    q = engine.quote(b, memo, line=InsuranceLine.GENERAL_LIABILITY, commercial_product_id="product_liability")
    assert q.metadata.get("rating_engine") == "carrier_leaf_filing"
    assert q.metadata.get("product_id") == "product_liability"
    assert q.adjusted_premium > 0
