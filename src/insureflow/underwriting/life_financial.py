"""Life financial UW — income vs net worth, suitability, riders, 1035, insurable interest."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.personal.manuals import life_manual
from insureflow.underwriting.life_product import classify_life_family
from insureflow.underwriting.personal_lines import LifeFactors, _blob, extract_life_factors


def income_multiple_for_age(age: int | None) -> float:
    elig = life_manual().get("eligibility") or {}
    bands = elig.get("financial_multiple_by_age") or {}
    if not bands:
        return float(elig.get("financial_multiple_income") or 30)
    age_n = int(age or 40)
    best = 30.0
    for max_age, mult in sorted(((int(k), float(v)) for k, v in bands.items()), key=lambda kv: kv[0]):
        best = mult
        if age_n <= max_age:
            return mult
    return best


def _has_doc(blob: str, *needles: str) -> bool:
    return any(n.lower() in blob.lower() for n in needles)


@dataclass
class LifeFinancialResult:
    income: float
    net_worth: float
    in_force_face: float
    max_face_income: float
    max_face_net_worth: float
    income_multiple: float
    replacement: bool
    exchange_1035: bool
    insurable_interest_ok: bool | None
    suitability_ok: bool | None
    riders: list[str] = field(default_factory=list)
    rider_load_per_1000: float = 0.0
    findings: list[Finding] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    decision_hint: UWDecision = UWDecision.ACCEPT

    def to_metadata(self) -> dict[str, Any]:
        return {
            "income": self.income,
            "net_worth": self.net_worth,
            "in_force_face": self.in_force_face,
            "income_multiple": self.income_multiple,
            "max_face_income": self.max_face_income,
            "max_face_net_worth": self.max_face_net_worth,
            "replacement": self.replacement,
            "exchange_1035": self.exchange_1035,
            "insurable_interest_ok": self.insurable_interest_ok,
            "suitability_ok": self.suitability_ok,
            "riders": list(self.riders),
            "rider_load_per_1000": self.rider_load_per_1000,
        }


def evaluate_life_financial(
    bundle: SubmissionBundle,
    *,
    factors: LifeFactors | None = None,
    product_id: str | None = None,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
) -> LifeFinancialResult:
    factors = factors or extract_life_factors(bundle)
    blob = _blob(bundle)
    manual = life_manual()
    elig = manual.get("eligibility") or {}
    family = classify_life_family(product_id, coverage_id, coverage_name)

    income = float(factors.income or 0)
    net_worth = float(getattr(factors, "net_worth", 0) or 0)
    in_force = float(getattr(factors, "in_force_face", 0) or 0)
    face = float(factors.face_amount or 0)
    age = factors.age
    multiple = income_multiple_for_age(age)
    nw_mult = float(elig.get("net_worth_multiple") or 0.5)
    max_income = income * multiple if income > 0 else 0.0
    max_nw = net_worth * nw_mult if net_worth > 0 else 0.0
    total_face = face + in_force

    findings: list[Finding] = []
    reasons: list[str] = []
    hint = UWDecision.ACCEPT

    if face > 0 and income <= 0 and net_worth <= 0:
        hint = UWDecision.REFER
        reasons.append("Financial UW — income and net worth both missing")
        findings.append(
            Finding(
                title="Financial UW incomplete",
                description="Face amount present but neither earned income nor net worth was captured (they are not interchangeable).",
                severity=RiskSeverity.HIGH,
                category="life_financial",
            )
        )
    elif income > 0 and total_face > max_income * 1.05 and (max_nw <= 0 or total_face > max_nw):
        hint = UWDecision.REFER
        reasons.append(f"Financial UW — face exceeds {multiple:.0f}× income (age-banded) and net-worth limit")
        findings.append(
            Finding(
                title="Financial underwriting stretch",
                description=(
                    f"Applied + in-force ${total_face:,.0f} vs income ${income:,.0f} × {multiple:.0f} "
                    f"(cap ${max_income:,.0f})" + (f" and net worth ${net_worth:,.0f} × {nw_mult:.0%} (cap ${max_nw:,.0f})" if net_worth else "")
                ),
                severity=RiskSeverity.HIGH,
                category="life_financial",
            )
        )
    elif net_worth > 0 and income <= 0 and total_face > max_nw:
        hint = UWDecision.REFER
        reasons.append("Financial UW — estate/net-worth multiple exceeded (no earned income)")
        findings.append(
            Finding(
                title="Estate-basis face exceeds net-worth multiple",
                description=f"Face ${total_face:,.0f} vs net worth ${net_worth:,.0f} × {nw_mult:.0%}",
                severity=RiskSeverity.HIGH,
                category="life_financial",
            )
        )

    rel = str(getattr(factors, "beneficiary_relationship", "") or "")
    if not rel:
        m = re.search(r"beneficiary(?:\s+relationship)?\s*[:=]\s*([A-Za-z][A-Za-z /-]{1,40})", blob, re.I)
        rel = m.group(1).strip() if m else ""
    interest_ok: bool | None = None
    if rel:
        ok_rel = bool(re.search(r"spouse|child|parent|partner|trust|estate|employer|key.?person|business|self", rel, re.I))
        bad_rel = bool(re.search(r"friend|neighbor|stranger|unrelated|acquaintance", rel, re.I))
        interest_ok = ok_rel and not bad_rel
        if bad_rel or not ok_rel:
            hint = UWDecision.REFER if hint != UWDecision.DECLINE else hint
            reasons.append("Insurable interest not established")
            findings.append(
                Finding(
                    title="Insurable interest question",
                    description=f"Beneficiary relationship '{rel}' is not a clear insurable-interest class.",
                    severity=RiskSeverity.CRITICAL,
                    category="life_financial",
                )
            )
    else:
        findings.append(
            Finding(
                title="Beneficiary / insurable interest not stated",
                description="Name a beneficiary and relationship before issue.",
                severity=RiskSeverity.MODERATE,
                category="life_financial",
            )
        )

    replacement = bool(re.search(r"\breplac(?:e|ing|ement)\b|existing\s+policy\s+to\s+be\s+(?:lapsed|surrendered)", blob, re.I))
    exchange = bool(re.search(r"\b1035\b|section\s*1035|tax[- ]free\s+exchange", blob, re.I))
    if replacement or exchange:
        form_ok = _has_doc(
            blob,
            "replacement form",
            "naic replacement notice",
            "1035 exchange form",
            "1035 assignment",
            "absolute assignment",
            "replacement acknowledgement",
        )
        if not form_ok:
            hint = UWDecision.REFER if hint != UWDecision.DECLINE else hint
            reasons.append("Replacement / 1035 form missing")
            findings.append(
                Finding(
                    title="Replacement or 1035 without required form",
                    description="NAIC replacement notice and/or 1035 assignment must be on file before issue.",
                    severity=RiskSeverity.CRITICAL,
                    category="life_financial",
                )
            )

    rider_rates = manual.get("rider_rates_per_1000") or {}
    riders: list[str] = []
    rider_load = 0.0
    checks = (
        ("waiver_of_premium", r"waiver of premium|\bwop\b|premium waiver"),
        ("accidental_death", r"accidental death|\badb\b|double indemnity"),
        ("child_term", r"child\s+term|children.?s?\s+rider"),
        ("accelerated_benefit", r"accelerated\s+(?:death\s+)?benefit|\bchronic\s+illness\s+rider"),
    )
    for rider_id, pat in checks:
        if re.search(pat, blob, re.I):
            riders.append(rider_id)
            rider_load += float(rider_rates.get(rider_id) or 0)

    suitability_ok: bool | None = None
    if family in {"variable_universal", "ulip", "annuity"}:
        q_ok = _has_doc(blob, "suitability questionnaire", "risk profile", "finra", "reg bi", "best interest")
        senior = (age or 0) >= 65
        liquidity = bool(re.search(r"liquidity\s+need|emergency\s+fund|surrender\s+charge", blob, re.I))
        suitability_ok = q_ok and not (senior and not liquidity and family == "annuity" and not q_ok)
        if not q_ok:
            hint = UWDecision.REFER if hint != UWDecision.DECLINE else hint
            reasons.append("Suitability questionnaire missing for VUL/annuity")
            findings.append(
                Finding(
                    title="Suitability not documented",
                    description=f"{family.replace('_', ' ')} requires a suitability / best-interest questionnaire before issue.",
                    severity=RiskSeverity.CRITICAL,
                    category="life_financial",
                )
            )
        elif senior and family == "annuity":
            findings.append(
                Finding(
                    title="Senior annuity suitability review",
                    description="Issue age 65+ annuity — confirm liquidity, surrender schedule, and replacement comparison.",
                    severity=RiskSeverity.HIGH,
                    category="life_financial",
                )
            )

    return LifeFinancialResult(
        income=income,
        net_worth=net_worth,
        in_force_face=in_force,
        max_face_income=round(max_income, 2),
        max_face_net_worth=round(max_nw, 2),
        income_multiple=multiple,
        replacement=replacement,
        exchange_1035=exchange,
        insurable_interest_ok=interest_ok,
        suitability_ok=suitability_ok,
        riders=riders,
        rider_load_per_1000=round(rider_load, 4),
        findings=findings,
        reasons=reasons,
        decision_hint=hint,
    )
