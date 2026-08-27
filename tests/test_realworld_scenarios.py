"""All-condition real-world insurance submission matrix."""

from __future__ import annotations

import pytest

from insureflow.testing.realworld_scenarios import build_all_scenarios, evaluate_result, run_scenario


@pytest.mark.parametrize("scenario", build_all_scenarios(), ids=lambda s: s.id)
def test_realworld_scenario(scenario) -> None:
    result = run_scenario(scenario)
    failures = evaluate_result(scenario, result)
    assert not failures, f"{scenario.id} ({scenario.title}): decision={result.get('ai_decision')} appetite={result.get('appetite_filter_passed')} failures={failures}"


def test_scenario_catalog_covers_core_conditions() -> None:
    conditions = {s.condition for s in build_all_scenarios()}
    assert "decline" in conditions
    assert "refer" in conditions
    assert "accept_path" in conditions
    assert "missing_data" in conditions
    assert len(build_all_scenarios()) >= 12
