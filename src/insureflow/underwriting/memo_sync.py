"""Keep underwriting memo narrative / recommendation in sync with ``memo.decision``."""

from __future__ import annotations

from insureflow.decisions import DecisionOutcome, decision_rank, normalize_decision, to_vertical
from insureflow.models.agents import Finding, Recommendation, RiskSeverity, UnderwritingMemo, UWDecision


def build_memo_summary(decision: UWDecision | str, score: float, findings: list[Finding], *, extra: str = "") -> str:
    """Build the executive-summary narrative from the *current* decision."""
    sev_counts: dict[str, int] = {}
    for f in findings:
        key = f.severity.value if hasattr(f.severity, "value") else str(f.severity or "moderate")
        sev_counts[key] = sev_counts.get(key, 0) + 1
    critical = sev_counts.get("critical", 0)
    high = sev_counts.get("high", 0)
    total = len(findings)
    action = normalize_decision(decision).value.upper()
    pct = int(round(float(score or 0.0) * 100))
    narrative = f"Underwriting recommendation is {action} based on {total} findings across risk, loss history, compliance, and fraud analysis. Aggregate risk score is {pct}/100."
    if critical or high:
        narrative += f" {critical + high} finding(s) require elevated attention."
    if extra:
        narrative = f"{narrative} {extra.strip()}"
    return narrative


def _to_uw_decision(value: UWDecision | str | None) -> UWDecision | None:
    if value is None:
        return None
    if isinstance(value, UWDecision):
        return value
    mapped = to_vertical(normalize_decision(value), "insurance")
    try:
        return UWDecision(mapped)
    except ValueError:
        return UWDecision.REFER


def worst_decision(*decisions: UWDecision | str | None) -> UWDecision:
    """Return the most adverse decision (decline beats refer beats conditional beats accept)."""
    best = DecisionOutcome.ACCEPT
    for d in decisions:
        if d is None:
            continue
        outcome = normalize_decision(d)
        if decision_rank(outcome) < decision_rank(best):
            best = outcome
    return _to_uw_decision(to_vertical(best, "insurance")) or UWDecision.REFER


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[tuple[str, str]] = set()
    out: list[Finding] = []
    for f in findings:
        key = (f.title.strip().lower(), (f.description or "")[:120].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def enforce_decision_consistency(memo: UnderwritingMemo) -> UnderwritingMemo:
    """Hard gates so the headline decision never contradicts findings.

    Fixes the credibility failure mode: ACCEPT with critical "decline recommended"
    findings, high severity, or elevated risk score.
    """
    from insureflow.models.agents import RiskSeverity, UWDecision

    decisions: list[UWDecision | str | None] = [memo.decision]
    if memo.recommendation and memo.recommendation.action:
        decisions.append(memo.recommendation.action)

    critical_titles: list[str] = []
    for f in memo.key_findings or []:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity or "")
        title = (f.title or "").strip()
        title_l = title.lower()
        # Selection / agent gates that publish an explicit action on the finding
        if f.category == "selection_standards" and f.source_value:
            decisions.append(str(f.source_value))
        if sev == "critical":
            critical_titles.append(title or "critical finding")
            # "refer to licensed UW" criticals stay refer; decline language → decline
            if "decline" in title_l or "declined" in title_l or "declination" in title_l:
                decisions.append(UWDecision.DECLINE)
            elif "refer" in title_l:
                decisions.append(UWDecision.REFER)
            else:
                decisions.append(UWDecision.DECLINE)

    score = float(memo.overall_risk_score or 0.0)
    sev = memo.overall_risk_severity
    sev_val = sev.value if hasattr(sev, "value") else str(sev or "")
    if sev_val == "critical" or score >= 0.85:
        decisions.append(UWDecision.DECLINE)
    elif sev_val == "high" or score >= 0.70:
        decisions.append(UWDecision.REFER)

    # Missing required docs / open human checkpoints → never clean ACCEPT
    if memo.human_review_required and normalize_decision(memo.decision) == DecisionOutcome.ACCEPT:
        decisions.append(UWDecision.REFER)

    prior = normalize_decision(memo.decision)
    memo.decision = worst_decision(*decisions)
    after = normalize_decision(memo.decision)

    if after != prior and critical_titles:
        memo.human_review_reasons = list(memo.human_review_reasons or [])
        for t in critical_titles[:5]:
            if t not in memo.human_review_reasons:
                memo.human_review_reasons.append(t)

    # Refresh severity from findings so UI matches the gate
    if memo.key_findings:
        rank = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
        worst = max(
            (rank.get(f.severity.value if hasattr(f.severity, "value") else str(f.severity), 0) for f in memo.key_findings),
            default=0,
        )
        inv = {1: RiskSeverity.LOW, 2: RiskSeverity.MODERATE, 3: RiskSeverity.HIGH, 4: RiskSeverity.CRITICAL}
        if worst:
            memo.overall_risk_severity = inv[worst]

    return resync_memo_narrative(memo)


def resync_memo_narrative(memo: UnderwritingMemo, *, extra_summary: str = "") -> UnderwritingMemo:
    """Rebuild summary + recommendation.action to match ``memo.decision`` after overrides."""
    memo.key_findings = dedupe_findings(list(memo.key_findings or []))
    decision = _to_uw_decision(memo.decision) or UWDecision.REFER
    memo.decision = decision

    memo.summary = build_memo_summary(
        decision,
        float(memo.overall_risk_score or 0.0),
        list(memo.key_findings or []),
        extra=extra_summary,
    )

    action = decision.value
    rationale = memo.summary
    conditions = list(memo.conditions or [])
    if memo.recommendation:
        memo.recommendation.action = action
        memo.recommendation.rationale = rationale
        if not memo.recommendation.conditions:
            memo.recommendation.conditions = conditions
    else:
        memo.recommendation = Recommendation(action=action, rationale=rationale, conditions=conditions)

    memo.human_review_required = decision in (
        UWDecision.REFER,
        UWDecision.DECLINE,
        UWDecision.CONDITIONAL_ACCEPT,
    )
    if memo.human_review_required and not memo.human_review_reasons:
        memo.human_review_reasons = [f.title for f in memo.key_findings if f.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)]
    return memo
