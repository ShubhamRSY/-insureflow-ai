"""Production business KPI aggregation + labeled-scenario bootstrap."""

from __future__ import annotations

from pathlib import Path

from insureflow.analytics.business_kpis import (
    BusinessKPIService,
    CatchRateTracker,
    DecisionRoutingTracker,
    _compute_roi,
    bootstrap_business_kpis,
)


def test_roi_formula_net_profit_over_investment() -> None:
    empty = _compute_roi(0, 0, platform_usd_annual=0, llm_usd_annual=0)
    assert empty["sample_size"] == 0
    assert empty["value"] is None
    assert empty["status"] == "not_measured"
    assert empty["cost_of_investment_usd"] == 0
    assert empty["net_profit_usd"] == 0

    desk_annual = 799.0 * 12
    measured = _compute_roi(12, 10.0, platform_usd_annual=desk_annual, llm_usd_annual=0)
    hours_raw = (7200.0 - 10.0) / 3600.0
    usd_per_file = round(hours_raw * 175.0, 2)
    total_return = round(usd_per_file * 1000, 2)
    net = round(total_return - desk_annual, 2)
    expected_pct = round((net / desk_annual) * 100.0, 1)

    assert measured["status"] == "production_ready"
    assert measured["unit"] == "percent"
    assert measured["hours_saved_per_file"] == round(hours_raw, 3)
    assert measured["total_return_usd"] == total_return
    assert measured["cost_of_investment_usd"] == desk_annual
    assert measured["net_profit_usd"] == net
    assert measured["value"] == expected_pct
    assert measured["pass"] is True
    assert "Net Profit" in measured["what_to_say"]


def test_roi_undefined_when_investment_is_zero() -> None:
    measured = _compute_roi(12, 10.0, platform_usd_annual=0, llm_usd_annual=0)
    assert measured["cost_of_investment_usd"] == 0
    assert measured["value"] is None
    assert measured["status"] == "lab_partial"
    assert measured["pass"] is False
    assert measured["planning_at_desk"]["roi_percent"] is not None
    assert measured["planning_at_desk"]["cost_of_investment_usd"] == 799.0 * 12


def test_decision_routing_and_catch_stats(tmp_path: Path) -> None:
    decisions = DecisionRoutingTracker(persist_path=tmp_path / "dec.jsonl")
    catches = CatchRateTracker(persist_path=tmp_path / "catch.jsonl")
    svc = BusinessKPIService(decision_tracker=decisions, catch_tracker=catches)

    svc.record_pipeline_result(bundle_id="a", decision="accept", org_id="t")
    svc.record_pipeline_result(bundle_id="b", decision="refer", org_id="t", human_review_required=True)
    svc.record_pipeline_result(bundle_id="c", decision="decline", org_id="t")
    svc.catches.record("b", "missing_doc", caught=True, expected=True, org_id="t")
    svc.catches.record("x", "conflict", caught=False, expected=True, org_id="t")

    routing = decisions.stats("t")
    assert routing["sample_size"] == 3
    assert routing["straight_through"] == 1
    assert routing["referred"] == 1
    assert routing["declined"] == 1

    catch = catches.stats("t")
    assert catch["sample_size"] == 2
    assert catch["catch_rate"] == 0.5


def test_bootstrap_produces_measurable_kpis() -> None:
    import uuid

    org = f"pytest-kpi-{uuid.uuid4().hex[:8]}"
    report = bootstrap_business_kpis(org_id=org)
    assert report["bootstrap"]["scenarios_run"] == 14
    # Allow up to 2 scenarios to fail due to transient network errors (CAT oracle, etc.)
    assert report["bootstrap"]["scenarios_passed"] >= 12
    kpis = report["kpis"]
    assert kpis["cycle_time"]["sample_size"] >= 12
    assert kpis["cycle_time"]["value"] > 0
    assert kpis["stp_vs_referred"]["sample_size"] >= 12
    assert kpis["missing_doc_conflict_catch"]["sample_size"] >= 1
    assert kpis["missing_doc_conflict_catch"]["value"] >= 0.9
    assert kpis["override_rate"]["sample_size"] >= 12
    assert kpis["roi"]["sample_size"] >= 12
    assert kpis["roi"]["hours_saved_per_file"] > 1.5
    assert kpis["roi"]["total_return_usd"] > 0
    assert kpis["roi"]["formula"].startswith("ROI =")
    # Bind / LR remain empty without production outcomes
    assert kpis["bind_rate_after_accept"]["sample_size"] == 0
    assert kpis["loss_ratio"]["sample_size"] == 0
