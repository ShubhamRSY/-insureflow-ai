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
        if fin and (fin.annual_revenue or 0) > 0 and line == InsuranceLine.TRADE_CREDIT:
            # Proxy AR book as a fraction of revenue when no AR aging is present
            return float(fin.annual_revenue) * 0.15, "revenue_proxy_ar", False
        if fin and (fin.total_asset_value or 0) > 0 and line == InsuranceLine.DIRECTORS_AND_OFFICERS:
            return min(float(fin.total_asset_value) * 0.1, 5_000_000.0), "asset_proxy_limit", False

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


def underwrite_specialty(bundle: SubmissionBundle, line: InsuranceLine) -> SpecialtyUnderwriteResult:
    """Line-specific heuristics — complements agents, does not replace them."""
    blob = _blob(bundle).lower()
    findings: list[Finding] = []
    reasons: list[str] = []
    flags: list[str] = []
    decision = UWDecision.ACCEPT

    def _find(title: str, detail: str, severity: RiskSeverity, *, refer: bool = False, decline: bool = False) -> None:
        nonlocal decision
        findings.append(
            Finding(
                title=title,
                description=detail,
                severity=severity,
                category="specialty_uw",
            )
        )
        reasons.append(title)
        if decline:
            decision = UWDecision.DECLINE
            flags.append(title)
        elif refer and decision != UWDecision.DECLINE:
            decision = UWDecision.REFER
            flags.append(title)

    if line == InsuranceLine.DIRECTORS_AND_OFFICERS:
        if any(k in blob for k in ("pending litigation", "securities class action", "sec investigation", "doj investigation")):
            _find("Material litigation / regulatory exposure", "Pending litigation or regulatory investigation disclosed — staff UW referral required.", RiskSeverity.CRITICAL, refer=True)
        if any(k in blob for k in ("bankruptcy", "going concern", "insolvent")):
            _find("Financial distress", "Going-concern / insolvency language — decline or refer to CUO.", RiskSeverity.CRITICAL, decline=True)
        if "prior acts" not in blob and "continuity date" not in blob and "claims made" in blob:
            _find("Prior acts / continuity unclear", "Claims-made D&O without clear prior-acts warranty — refer.", RiskSeverity.HIGH, refer=True)
        if not any(k in blob for k in ("financial statement", "10-k", "balance sheet", "p&l", "income statement")):
            _find("Financials missing", "D&O requires recent financials — request from broker.", RiskSeverity.HIGH, refer=True)

    elif line == InsuranceLine.TRADE_CREDIT:
        conc = re.search(r"top\s*(?:buyer|customer)\s*(?:concentration|share)?\s*[:=]?\s*(\d{1,3})\s*%", blob)
        if conc and int(conc.group(1)) >= 40:
            _find(
                "Buyer concentration risk",
                f"Top buyer/customer concentration {conc.group(1)}% — refer for credit committee.",
                RiskSeverity.HIGH,
                refer=True,
            )
        if any(k in blob for k in ("bad debt", "write-off", "write off")) and any(k in blob for k in ("high", "elevated", "deteriorat")):
            _find("Elevated bad-debt history", "Write-off / bad-debt language suggests credit stress — refer.", RiskSeverity.HIGH, refer=True)
        if "aging" not in blob and "accounts receivable" not in blob and "a/r" not in blob:
            _find("AR aging missing", "Trade credit requires current AR aging — request from broker.", RiskSeverity.HIGH, refer=True)

    elif line == InsuranceLine.ERRORS_AND_OMISSIONS:
        if any(k in blob for k in ("guarantee of results", "guaranteed outcome", "indemnify for consequential")):
            _find("Aggressive contract wording", "Client contracts appear to guarantee results / consequential damages — refer.", RiskSeverity.HIGH, refer=True)
        if any(k in blob for k in ("prior claim", "malpractice claim", "professional liability claim", "e&o claim")):
            _find("Prior E&O claims", "Prior professional liability claims disclosed — experience rating / refer.", RiskSeverity.HIGH, refer=True)
        if not any(k in blob for k in ("scope of services", "engagement letter", "professional services", "description of services")):
            _find("Services scope unclear", "E&O needs clear services description — request from broker.", RiskSeverity.MODERATE, refer=True)

    elif line == InsuranceLine.KEY_PERSON:
        if any(k in blob for k in ("tobacco", "smoker", "nicotine")):
            _find("Tobacco use", "Tobacco indicated — rating class impact; confirm with medical.", RiskSeverity.MODERATE)
        if any(k in blob for k in ("cancer", "heart attack", "stroke", "diabetes", "coronary")):
            _find("Material medical history", "Serious medical history — medical underwriting referral.", RiskSeverity.CRITICAL, refer=True)
        if not any(k in blob for k in ("face amount", "coverage amount", "job description", "key person", "key-person")):
            _find("Coverage justification thin", "Need face amount justification / role description.", RiskSeverity.MODERATE, refer=True)

    return SpecialtyUnderwriteResult(decision=decision, findings=findings, reasons=reasons, referral_flags=flags)


def specialty_guideline_keywords(line: InsuranceLine) -> list[str]:
    return {
        InsuranceLine.DIRECTORS_AND_OFFICERS: ["d&o", "directors", "officers", "management liability", "securities"],
        InsuranceLine.TRADE_CREDIT: ["trade credit", "receivables", "buyer credit", "concentration"],
        InsuranceLine.ERRORS_AND_OMISSIONS: ["e&o", "errors and omissions", "professional liability"],
        InsuranceLine.KEY_PERSON: ["key person", "key-person", "keyman", "face amount"],
    }.get(line, [])
