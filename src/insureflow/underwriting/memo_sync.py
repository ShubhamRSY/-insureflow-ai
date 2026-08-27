"""Keep underwriting memo narrative / recommendation in sync with ``memo.decision``."""

from __future__ import annotations

from insureflow.decisions import DecisionOutcome, decision_rank, normalize_decision, to_vertical
from insureflow.models.agents import Finding, Recommendation, RiskSeverity, UnderwritingMemo, UWDecision


def build_memo_summary(decision: UWDecision | str, score: float, findings: list[Finding], *, extra: str = "") -> str:
    """Build a UW-facing executive summary: decision, drivers, next actions."""
    action = normalize_decision(decision).value.upper().replace("_", " ")
    pct = int(round(float(score or 0.0) * 100))

    ranked = sorted(
        findings or [],
        key=lambda f: {"critical": 0, "high": 1, "moderate": 2, "low": 3}.get(
            (f.severity.value if hasattr(f.severity, "value") else str(f.severity or "moderate")).lower(),
            2,
        ),
    )
    critical = [f for f in ranked if (f.severity.value if hasattr(f.severity, "value") else str(f.severity)).lower() == "critical"]
    high = [f for f in ranked if (f.severity.value if hasattr(f.severity, "value") else str(f.severity)).lower() == "high"]
    drivers = (critical + high)[:5] or ranked[:3]

    next_steps: list[str] = []
    decision_norm = normalize_decision(decision)
    if decision_norm == DecisionOutcome.DECLINE:
        headline = f"DECISION: {action} — do not bind; issue declination / broker notice."
        next_steps = [
            "Document decline rationale for the producer",
            "Confirm no outstanding quote authority remains open",
        ]
    elif decision_norm == DecisionOutcome.REFER:
        headline = f"DECISION: {action} — licensed UW review required before bind."
        next_steps = [
            "Clear critical / high findings below before releasing terms",
            "Request any missing package items from the broker if listed",
        ]
    elif decision_norm == DecisionOutcome.CONDITIONAL_ACCEPT:
        headline = f"DECISION: {action} — bind only after stated conditions are met."
        next_steps = [
            "Publish conditions to the broker and track fulfillment",
            "Re-check residual risk after conditions clear",
        ]
    else:
        headline = f"DECISION: {action} — within appetite; proceed to quote / bind workflow."
        next_steps = [
            "Confirm final premium and forms with producer",
            "Complete any remaining checklist items before bind",
        ]

    # Proactive steps derived from top findings
    for f in drivers[:4]:
        title = (f.title or "").strip()
        title_l = title.lower()
        if not title:
            continue
        if "loss run" in title_l or "claims" in title_l:
            step = "Obtain a usable 5-year loss run (not empty / unparsed)"
        elif "missing" in title_l or "document" in title_l or "incomplete" in title_l:
            step = f"Collect outstanding package item: {title}"
        elif "limit" in title_l or "coverage" in title_l:
            step = f"Resolve coverage / limit issue: {title}"
        elif "oracle" in title_l or "clue" in title_l or "a-plus" in title_l:
            step = "Confirm the external record (CLUE / A-PLUS / bureau) was checked, or document why it was unavailable"
        elif "verification" in title_l:
            step = f"Verify against source paperwork: {title}"
        elif "mib" in title_l:
            step = "Order an MIB report — a signed authorization alone is not a search"
        elif "sanctions" in title_l or "ofac" in title_l:
            step = "Obtain the applicant's full legal name and re-run sanctions screening"
        elif "unverified figure" in title_l or "could not be verified" in title_l.lower():
            step = "Match the flagged figure to supporting paperwork before relying on it"
        elif "decline" in title_l:
            step = f"Address hard stop: {title}"
        else:
            step = f"Review: {title}"
        if step not in next_steps:
            next_steps.append(step)

    lines = [
        headline,
        "",
        f"Risk score: {pct}/100 · {len(findings)} findings ({len(critical)} critical, {len(high)} high)",
        "",
        "Why this decision",
    ]
    if drivers:
        for f in drivers:
            sev = (f.severity.value if hasattr(f.severity, "value") else str(f.severity or "moderate")).upper()
            title = (f.title or "Finding").strip()
            detail = (f.description or "").strip()
            # CRITICAL/HIGH findings drive the decision — never cut them off
            # mid-sentence. Lower-severity findings still get a generous cap,
            # truncated on a word boundary rather than mid-word.
            if detail and sev not in ("CRITICAL", "HIGH") and len(detail) > 220:
                detail = detail[:220].rsplit(" ", 1)[0].rstrip() + "…"
            bullet = f"• [{sev}] {title}"
            if detail:
                bullet += f" — {detail}"
            lines.append(bullet)
    else:
        lines.append("• No elevated findings recorded.")

    lines.extend(["", "What to do next"])
    for i, step in enumerate(next_steps[:6], 1):
        lines.append(f"{i}. {step}")

    if extra and extra.strip():
        lines.extend(["", extra.strip()])

    return "\n".join(lines)


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

    Critical findings without explicit decline language escalate to REFER, not
    automatic DECLINE — data-quality / portfolio concentration criticals still
    need human review but must not fail clean accept-path scenarios.
    """
    from insureflow.models.agents import RiskSeverity, UWDecision

    decisions: list[UWDecision | str | None] = [memo.decision]
    if memo.recommendation and memo.recommendation.action:
        decisions.append(memo.recommendation.action)

    critical_titles: list[str] = []
    explicit_decline = False
    for f in memo.key_findings or []:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity or "")
        title = (f.title or "").strip()
        title_l = title.lower()
        src = str(f.source_value or "").strip().lower()
        # Selection / agent gates that publish an explicit action on the finding
        if f.category == "selection_standards" and src:
            decisions.append(src)
            if src in {"decline", "declined"}:
                explicit_decline = True
        if sev == "critical":
            critical_titles.append(title or "critical finding")
            # Only decline when the finding itself recommends decline
            if "decline" in title_l or "declined" in title_l or "declination" in title_l or src in {"decline", "declined"}:
                decisions.append(UWDecision.DECLINE)
                explicit_decline = True
            else:
                decisions.append(UWDecision.REFER)

    score = float(memo.overall_risk_score or 0.0)
    sev = memo.overall_risk_severity
    sev_val = sev.value if hasattr(sev, "value") else str(sev or "")
    # Extreme score → decline; elevated severity / score → refer (unless already declining)
    if score >= 0.85 or (sev_val == "critical" and explicit_decline):
        decisions.append(UWDecision.DECLINE)
    elif sev_val in {"critical", "high"} or score >= 0.70:
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

    # Collapse duplicate review reasons so the decision panel stays readable
    if memo.human_review_reasons:
        seen: set[str] = set()
        deduped: list[str] = []
        for r in memo.human_review_reasons:
            key = str(r).strip().lower()
            if key and key not in seen:
                seen.add(key)
                deduped.append(r)
        memo.human_review_reasons = deduped

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
