"""LOB rating and shadow eval tests."""

from __future__ import annotations

from insureflow.evaluations.pipeline_shadow import run_shadow_eval
from insureflow.underwriting.lob_rating import _credibility_mod


def test_credibility_mod_blends_toward_experience():
    blended, z = _credibility_mod(4, 1.25, k=8.0)
    assert 1.0 < blended < 1.25
    assert 0 < z < 1


def test_shadow_eval_passes_reasonable_submission():
    summary = {
        "bundle_id": "ins-test",
        "insurance_line": "commercial_property",
        "tiv": 2_000_000,
        "ai_decision": "accept",
        "document_checklist": {"completeness_pct": 85, "missing": []},
        "reconciliation_discrepancies": 0,
        "quote": {"adjusted_premium": 12000, "eligible": True},
    }
    result = run_shadow_eval(summary=summary, quote=summary["quote"], memo={"decision": "accept"})
    assert "overall_score" in result
    assert result["tasks"]["decision_alignment"]["passed"] is True
