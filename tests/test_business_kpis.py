"""Production business KPI aggregation + labeled-scenario bootstrap."""

from __future__ import annotations

from pathlib import Path

from insureflow.analytics.business_kpis import BusinessKPIService, CatchRateTracker, DecisionRoutingTracker, bootstrap_business_kpis


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
    assert report["bootstrap"]["scenarios_passed"] == 14
    kpis = report["kpis"]
    assert kpis["cycle_time"]["sample_size"] >= 14
    assert kpis["cycle_time"]["value"] > 0
    assert kpis["stp_vs_referred"]["sample_size"] >= 14
    assert kpis["missing_doc_conflict_catch"]["sample_size"] >= 1
    assert kpis["missing_doc_conflict_catch"]["value"] >= 0.9
    assert kpis["override_rate"]["sample_size"] >= 14
    # Bind / LR remain empty without production outcomes
    assert kpis["bind_rate_after_accept"]["sample_size"] == 0
    assert kpis["loss_ratio"]["sample_size"] == 0
