"""Commercial specialty lines — D&O, Trade Credit, E&O, Key Person.

These are not rated on building TIV + COPE. Exposure is limit / AR / face amount,
with line-specific UW heuristics for Accept / Refer / Decline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import COMMERCIAL_SPECIALTY_LINES, InsuranceLine, QuoteResult, RateComponent
from insureflow.underwriting.personal_lines import _blob

# Loss cost style rates per $100 of exposure (limit / AR / face)
SPECIALTY_LOSS_COSTS: dict[InsuranceLine, float] = {
    InsuranceLine.DIRECTORS_AND_OFFICERS: 0.45,
    InsuranceLine.TRADE_CREDIT: 0.22,
    InsuranceLine.ERRORS_AND_OMISSIONS: 0.55,
    InsuranceLine.KEY_PERSON: 0.12,
}

SPECIALTY_LCM: dict[InsuranceLine, float] = {
    InsuranceLine.DIRECTORS_AND_OFFICERS: 2.35,
    InsuranceLine.TRADE_CREDIT: 2.15,
    InsuranceLine.ERRORS_AND_OMISSIONS: 2.40,
    InsuranceLine.KEY_PERSON: 1.70,
}

SPECIALTY_MINIMUMS: dict[InsuranceLine, float] = {
    InsuranceLine.DIRECTORS_AND_OFFICERS: 2_500.0,
    InsuranceLine.TRADE_CREDIT: 1_500.0,
    InsuranceLine.ERRORS_AND_OMISSIONS: 2_000.0,
    InsuranceLine.KEY_PERSON: 500.0,
}

# Default exposure when package has no explicit limit / AR / face
_DEFAULT_EXPOSURE: dict[InsuranceLine, float] = {
    InsuranceLine.DIRECTORS_AND_OFFICERS: 1_000_000.0,
    InsuranceLine.TRADE_CREDIT: 500_000.0,
    InsuranceLine.ERRORS_AND_OMISSIONS: 1_000_000.0,
    InsuranceLine.KEY_PERSON: 500_000.0,
}


def is_specialty_line(line: InsuranceLine) -> bool:
    return line in COMMERCIAL_SPECIALTY_LINES


def _money_from_blob(blob: str, *labels: str) -> float:
    for label in labels:
        m = re.search(rf"{re.escape(label)}\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)", blob, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return 0.0


def estimate_specialty_exposure(bundle: SubmissionBundle, line: InsuranceLine) -> tuple[float, str, bool]:
    """Return (exposure, basis, used_default)."""
    blob = _blob(bundle)
    if bundle.structured:
        for cov in bundle.structured.coverages or []:
            if (cov.limit_amount or 0) > 0:
                return float(cov.limit_amount), "coverage_limit", False
        fin = bundle.structured.financial
        if fin and line == InsuranceLine.TRADE_CREDIT:
            revenue = fin.annual_revenue
            if revenue is not None and revenue > 0:
                # Proxy AR book as a fraction of revenue when no AR aging is present
                return float(revenue) * 0.15, "revenue_proxy_ar", False
        if fin and line == InsuranceLine.DIRECTORS_AND_OFFICERS:
            assets = fin.total_asset_value
            if assets is not None and assets > 0:
                return min(float(assets) * 0.1, 5_000_000.0), "asset_proxy_limit", False

    if line == InsuranceLine.DIRECTORS_AND_OFFICERS:
        v = _money_from_blob(blob, "aggregate limit", "policy limit", "d&o limit", "limit of liability")
        if v > 0:
            return v, "stated_limit", False
    elif line == InsuranceLine.TRADE_CREDIT:
        v = _money_from_blob(blob, "total receivables", "accounts receivable", "credit limit", "insured turnover", "ar balance")
        if v > 0:
            return v, "receivables", False
    elif line == InsuranceLine.ERRORS_AND_OMISSIONS:
        v = _money_from_blob(blob, "aggregate limit", "policy limit", "e&o limit", "per claim limit", "limit of liability")
        if v > 0:
            return v, "stated_limit", False
    elif line == InsuranceLine.KEY_PERSON:
        v = _money_from_blob(blob, "face amount", "coverage amount", "sum assured", "death benefit", "key person limit")
        if v > 0:
            return v, "face_amount", False

    default = _DEFAULT_EXPOSURE.get(line, 1_000_000.0)
    return default, "default_exposure", True


def rate_specialty_line(
    bundle: SubmissionBundle,
    line: InsuranceLine,
    *,
    state: str = "",
    schedule_mod_pct: float = 0.0,
    market_mod_pct: float = 0.0,
) -> QuoteResult:
    """Limit / AR / face-amount rating — skips COPE and building TIV."""
    exposure, basis, used_default = estimate_specialty_exposure(bundle, line)
    loss_cost = SPECIALTY_LOSS_COSTS.get(line, 0.40)
    lcm = SPECIALTY_LCM.get(line, 2.2)
    min_prem = SPECIALTY_MINIMUMS.get(line, 1_000.0)

    base = (exposure / 100.0) * loss_cost * lcm
    adjusted = base * (1 + market_mod_pct / 100.0) * (1 + schedule_mod_pct / 100.0)
    adjusted = max(round(adjusted + 75.0, 2), min_prem)

    components = [
        RateComponent(name="specialty_loss_cost", amount=loss_cost, basis=f"per_100_{basis}", modifier_pct=0.0),
        RateComponent(name="loss_cost_multiplier", amount=lcm, basis="expense_profit", modifier_pct=0.0),
        RateComponent(name="exposure", amount=exposure, basis=basis, modifier_pct=0.0),
    ]
    if market_mod_pct:
        components.append(RateComponent(name="market_cycle_adjustment", amount=market_mod_pct, basis="market", modifier_pct=market_mod_pct))
    if schedule_mod_pct:
        components.append(RateComponent(name="uw_schedule_modification", amount=0, basis="uw_discretion", modifier_pct=schedule_mod_pct))

    reasons: list[str] = []
    if used_default:
        reasons.append(f"No explicit exposure found — rated on default {basis.replace('_', ' ')} ${exposure:,.0f}")

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=line,
        base_premium=round(base, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / (exposure / 100.0), 4) if exposure else 0.0,
        eligible=True,
        ineligibility_reasons=reasons,
        metadata={
            "insurance_line": line.value,
            "specialty": True,
            "exposure": exposure,
            "exposure_basis": basis,
            "used_default_exposure": used_default,
            "tiv": exposure,
            "cope_grade": "n/a",
            "cope_score": None,
            "cope_mod_pct": 0.0,
            "market_mod_pct": market_mod_pct,
            "personal_lines": False,
            "state": state,
        },
    )


@dataclass
class SpecialtyUnderwriteResult:
    decision: UWDecision
    findings: list[Finding] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    referral_flags: list[str] = field(default_factory=list)
    story: str = ""
    premium_mod_pct: float = 0.0
    scenario_codes: list[str] = field(default_factory=list)
    checklist_summary: dict[str, Any] = field(default_factory=dict)


def underwrite_specialty(bundle: SubmissionBundle, line: InsuranceLine) -> SpecialtyUnderwriteResult:
    """Delegate specialty UW to the commercial checklist + scenario engine."""
    from insureflow.underwriting.commercial_checklists import UWActionType, evaluate_commercial_checklist
    from insureflow.underwriting.memo_sync import worst_decision

    checklist = evaluate_commercial_checklist(bundle, line)
    blob = _blob(bundle).lower()
    findings = list(checklist.findings)
    reasons = [f.title for f in findings]
    flags: list[str] = [s.code for s in checklist.scenarios]
    decision = checklist.decision

    # Legacy hard gates that remain useful alongside the checklist
    if line == InsuranceLine.DIRECTORS_AND_OFFICERS:
        if any(k in blob for k in ("bankruptcy", "going concern", "insolvent")):
            findings.append(
                Finding(
                    title="Financial distress",
                    description="Going-concern / insolvency language — decline or refer to CUO.",
                    severity=RiskSeverity.CRITICAL,
                    category="specialty_uw",
                )
            )
            reasons.append("Financial distress")
            flags.append("Financial distress")
            decision = UWDecision.DECLINE
        elif "prior acts" not in blob and "continuity date" not in blob and "claims made" in blob:
            findings.append(
                Finding(
                    title="Prior acts / continuity unclear",
                    description="Claims-made D&O without clear prior-acts warranty — refer.",
                    severity=RiskSeverity.HIGH,
                    category="specialty_uw",
                )
            )
            reasons.append("Prior acts / continuity unclear")
            flags.append("Prior acts / continuity unclear")
            decision = worst_decision(decision, UWDecision.REFER)

    for action in checklist.actions:
        if action.action_type == UWActionType.REFER and action.detail:
            flags.append(action.detail)
        elif action.action_type == UWActionType.REQUIRE_MITIGATION and action.detail:
            flags.append(action.detail)
        elif action.action_type == UWActionType.ADD_EXCLUSION and action.detail:
            flags.append(action.detail)
        elif action.action_type == UWActionType.CAP_COVERAGE and action.detail:
            flags.append(action.detail)
        elif action.action_type == UWActionType.REQUIRE_DOC and action.detail:
            flags.append(action.detail)

    if checklist.story:
        reasons.append(checklist.story)

    return SpecialtyUnderwriteResult(
        decision=decision,
        findings=findings,
        reasons=reasons,
        referral_flags=flags,
        story=checklist.story,
        premium_mod_pct=checklist.premium_mod_pct,
        scenario_codes=[s.code for s in checklist.scenarios],
        checklist_summary=checklist.to_summary_dict(),
    )


def specialty_guideline_keywords(line: InsuranceLine) -> list[str]:
    return {
        InsuranceLine.DIRECTORS_AND_OFFICERS: ["d&o", "directors", "officers", "management liability", "securities"],
        InsuranceLine.TRADE_CREDIT: ["trade credit", "receivables", "buyer credit", "concentration"],
        InsuranceLine.ERRORS_AND_OMISSIONS: ["e&o", "errors and omissions", "professional liability"],
        InsuranceLine.KEY_PERSON: ["key person", "key-person", "keyman", "face amount"],
    }.get(line, [])
