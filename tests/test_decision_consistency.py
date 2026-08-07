"""Decision consistency: never ACCEPT when findings demand decline/refer."""

from __future__ import annotations

from insureflow.models.agents import Finding, Recommendation, RiskSeverity, UnderwritingMemo, UWDecision
from insureflow.underwriting.memo_sync import enforce_decision_consistency, worst_decision


def test_worst_decision_orders_adverse_first() -> None:
    assert worst_decision(UWDecision.ACCEPT, UWDecision.DECLINE) == UWDecision.DECLINE
    assert worst_decision(UWDecision.ACCEPT, UWDecision.REFER) == UWDecision.REFER
    assert worst_decision(UWDecision.CONDITIONAL_ACCEPT, "decline") == UWDecision.DECLINE


def test_critical_selection_decline_overrides_accept() -> None:
    memo = UnderwritingMemo(
        bundle_id="t1",
        insured_name="Pacific Coast",
        decision=UWDecision.ACCEPT,
        overall_risk_score=0.75,
        overall_risk_severity=RiskSeverity.HIGH,
        summary="Would wrongly say ACCEPT",
        key_findings=[
            Finding(
                title="Selection gate: decline recommended",
                description="substandard class with risk score 0.75 is beyond the book's ability to absorb — decline",
                severity=RiskSeverity.CRITICAL,
                category="selection_standards",
                source_value="decline",
            ),
            Finding(
                title="Valuation Mismatch Detected",
                description="SOV vs locations",
                severity=RiskSeverity.HIGH,
                category="fraud",
            ),
        ],
        recommendation=Recommendation(action="accept", rationale="stale"),
        human_review_required=True,
    )
    out = enforce_decision_consistency(memo)
    assert out.decision == UWDecision.DECLINE
    assert out.recommendation is not None
    assert out.recommendation.action == "decline"
    assert "DECLINE" in out.summary
    assert out.human_review_required is True
    assert out.overall_risk_severity == RiskSeverity.CRITICAL


def test_high_score_without_critical_is_refer_not_accept() -> None:
    memo = UnderwritingMemo(
        bundle_id="t2",
        insured_name="Test",
        decision=UWDecision.ACCEPT,
        overall_risk_score=0.75,
        overall_risk_severity=RiskSeverity.HIGH,
        key_findings=[
            Finding(title="Elevated aggregate risk score", description="score 0.75", severity=RiskSeverity.HIGH, category="uw_decision"),
        ],
        recommendation=Recommendation(action="accept", rationale="stale"),
    )
    out = enforce_decision_consistency(memo)
    assert out.decision == UWDecision.REFER
    assert "REFER" in out.summary


def test_critical_without_decline_language_is_refer() -> None:
    """Data-quality criticals need UW eyes — not an automatic DECLINE."""
    memo = UnderwritingMemo(
        bundle_id="t3",
        insured_name="Clean Retail",
        decision=UWDecision.ACCEPT,
        overall_risk_score=0.60,
        overall_risk_severity=RiskSeverity.CRITICAL,
        key_findings=[
            Finding(
                title="Loss run provided but empty — no claims extracted",
                description="Unrecognized format",
                severity=RiskSeverity.CRITICAL,
                category="data_quality",
            ),
            Finding(
                title="HIGH portfolio concentration risk",
                description="score 70%",
                severity=RiskSeverity.CRITICAL,
                category="portfolio_risk",
            ),
        ],
        recommendation=Recommendation(action="accept", rationale="stale"),
    )
    out = enforce_decision_consistency(memo)
    assert out.decision == UWDecision.REFER
