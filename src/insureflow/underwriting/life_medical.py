"""Life medical underwriting — knockouts, class assignment, APS requirements."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.personal.manuals import life_manual, life_medical_guide
from insureflow.underwriting.personal_lines import _blob, _int_field, _money, extract_life_factors, strip_negated_clauses


@dataclass
class LifeMedicalDecision:
    decision: UWDecision
    underwriting_class: str
    tobacco: bool
    flat_extras_per_1000: float
    require_aps: bool
    require_paramed: bool
    reasons: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    vitals: dict[str, float] = field(default_factory=dict)
    guide_id: str = ""

    def to_metadata(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "underwriting_class": self.underwriting_class,
            "tobacco": self.tobacco,
            "flat_extras_per_1000": self.flat_extras_per_1000,
            "require_aps": self.require_aps,
            "require_paramed": self.require_paramed,
            "reasons": self.reasons,
            "vitals": self.vitals,
            "guide_id": self.guide_id,
        }


def _parse_vitals(blob: str) -> dict[str, float]:
    out: dict[str, float] = {}
    m = re.search(r"(?:bp|blood pressure)\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})", blob, re.I)
    if m:
        out["bp_systolic"] = float(m.group(1))
        out["bp_diastolic"] = float(m.group(2))
    m = re.search(r"bmi\s*[:=]?\s*(\d+(?:\.\d+)?)", blob, re.I)
    if m:
        out["bmi"] = float(m.group(1))
    m = re.search(r"cholesterol\s*[:=]?\s*(\d+(?:\.\d+)?)", blob, re.I)
    if m:
        out["cholesterol"] = float(m.group(1))
    m = re.search(r"a1c\s*[:=]?\s*(\d+(?:\.\d+)?)", blob, re.I)
    if m:
        out["a1c"] = float(m.group(1))
    return out


def _class_rank(name: str) -> int:
    order = [
        "super_preferred",
        "preferred",
        "standard_plus",
        "standard",
        "table_a",
        "table_b",
        "table_c",
        "table_d",
        "table_e",
        "table_f",
        "substandard",
    ]
    try:
        return order.index(name)
    except ValueError:
        return order.index("standard")


def _worse_class(a: str, b: str) -> str:
    return a if _class_rank(a) >= _class_rank(b) else b


def _better_or_equal_cap(current: str, cap: str) -> str:
    """If current is better than cap, keep current; class_cap means best allowed."""
    return current if _class_rank(current) <= _class_rank(cap) else cap


def underwrite_life(bundle: SubmissionBundle) -> LifeMedicalDecision:
    guide = life_medical_guide()
    rate = life_manual()
    factors = extract_life_factors(bundle)
    blob = _blob(bundle)
    uw_blob = strip_negated_clauses(blob)
    vitals = _parse_vitals(blob)
    findings: list[Finding] = list(factors.findings)
    reasons: list[str] = []

    # Knockouts — affirmative disclosures only (negated histories stripped).
    for ko in guide.get("knockouts") or []:
        if re.search(ko.get("pattern", ""), uw_blob, re.I):
            findings.append(
                Finding(
                    title=ko.get("reason") or ko.get("id", "Knockout"),
                    description=f"Medical guide knockout {ko.get('id')}",
                    severity=RiskSeverity.CRITICAL,
                    category="life_medical",
                )
            )
            return LifeMedicalDecision(
                decision=UWDecision.DECLINE,
                underwriting_class="substandard",
                tobacco=factors.smoker,
                flat_extras_per_1000=0.0,
                require_aps=True,
                require_paramed=True,
                reasons=[ko.get("reason") or "Knockout"],
                findings=findings,
                vitals=vitals,
                guide_id=str(guide.get("guide_id") or ""),
            )

    uw_class = "standard"
    tobacco = factors.smoker
    flat_extra = 0.0

    # Class rules from patterns
    for rule in guide.get("class_rules") or []:
        if not re.search(rule.get("pattern", ""), uw_blob, re.I):
            continue
        if rule.get("tobacco"):
            tobacco = True
        if rule.get("class_floor"):
            uw_class = _worse_class(uw_class, str(rule["class_floor"]))
            reasons.append(f"Class floor from {rule.get('id')}: {rule['class_floor']}")
        if rule.get("class_cap"):
            # Cap = best class allowed if matched preferred language without worse findings
            if uw_class in ("standard", "standard_plus", "preferred", "super_preferred"):
                uw_class = str(rule["class_cap"])
                reasons.append(f"Class from {rule.get('id')}: {rule['class_cap']}")

    if factors.health_class == "preferred" and _class_rank(uw_class) > _class_rank("preferred"):
        pass
    elif factors.health_class == "preferred":
        uw_class = _worse_class(uw_class, "preferred") if tobacco else "preferred"
    elif factors.health_class == "substandard":
        uw_class = _worse_class(uw_class, "table_b")

    # Vitals bands
    bands = guide.get("vitals_bands") or {}
    for vital, limits in bands.items():
        if vital not in vitals:
            continue
        val = vitals[vital]
        if val > float(limits.get("decline_above", 9999)):
            findings.append(
                Finding(
                    title=f"{vital} outside issue limits",
                    description=f"{vital}={val} exceeds decline threshold",
                    severity=RiskSeverity.CRITICAL,
                    category="life_medical",
                )
            )
            return LifeMedicalDecision(
                decision=UWDecision.DECLINE,
                underwriting_class="substandard",
                tobacco=tobacco,
                flat_extras_per_1000=0.0,
                require_aps=True,
                require_paramed=True,
                reasons=[f"{vital} decline"],
                findings=findings,
                vitals=vitals,
                guide_id=str(guide.get("guide_id") or ""),
            )
        if val > float(limits.get("table_a_max", 9999)):
            uw_class = _worse_class(uw_class, "table_b")
            reasons.append(f"{vital} → table_b")
        elif val > float(limits.get("standard_max", 9999)):
            uw_class = _worse_class(uw_class, "table_a")
            reasons.append(f"{vital} → table_a")
        elif val > float(limits.get("preferred_max", 9999)):
            uw_class = _worse_class(uw_class, "standard")
            reasons.append(f"{vital} blocks preferred")

    # Avocation flat extras
    extras = guide.get("avocation_flat_extras") or {}
    for name, amt in extras.items():
        if name.lower() in blob:
            flat_extra += float(amt)
            reasons.append(f"Flat extra {name}: ${amt}/1000")
            findings.append(
                Finding(
                    title=f"Avocation flat extra — {name}",
                    description=f"${amt} per $1,000 face",
                    severity=RiskSeverity.HIGH,
                    category="life_medical",
                )
            )

    # Referrals
    decision = UWDecision.ACCEPT
    for rf in guide.get("referrals") or []:
        if re.search(rf.get("pattern", ""), uw_blob, re.I):
            decision = UWDecision.REFER
            reasons.append(rf.get("reason") or rf.get("id", "refer"))
            findings.append(
                Finding(
                    title=rf.get("reason") or "Medical referral",
                    description=f"Guide referral {rf.get('id')}",
                    severity=RiskSeverity.HIGH,
                    category="life_medical",
                )
            )

    age = factors.age or _int_field(blob, "applicant age", "insured age") or 40
    face = factors.face_amount or _money(blob, "face amount", "death benefit")
    elig = rate.get("eligibility") or {}
    if age > int(elig.get("max_age", 75)) or age < int(elig.get("min_age", 18)):
        decision = UWDecision.DECLINE
        reasons.append("Age outside issue ages")
        findings.append(
            Finding(
                title="Age outside life eligibility",
                description=f"Age {age}",
                severity=RiskSeverity.CRITICAL,
                category="life_medical",
            )
        )
    if face >= float(rate.get("facultative_threshold", 10_000_000)):
        decision = UWDecision.REFER
        reasons.append("Facultative face amount")
    elif face >= float(rate.get("jumbo_threshold", 5_000_000)):
        if decision == UWDecision.ACCEPT:
            decision = UWDecision.REFER
        reasons.append("Jumbo face amount")

    from insureflow.underwriting.life_financial import income_multiple_for_age

    income_mult = income_multiple_for_age(age if factors.age else age)
    if factors.income and face > factors.income * income_mult:
        decision = UWDecision.REFER if decision != UWDecision.DECLINE else decision
        reasons.append("Financial underwriting — face exceeds age-banded income multiple")
        findings.append(
            Finding(
                title="Financial underwriting stretch",
                description=f"Face ${face:,.0f} vs earned income ${factors.income:,.0f} × {income_mult:.0f}",
                severity=RiskSeverity.HIGH,
                category="life_medical",
            )
        )

    require_aps = False
    for rule in guide.get("aps_requirements") or []:
        if age >= int(rule.get("min_age", 0)) and face >= float(rule.get("min_face", 0)):
            require_aps = bool(rule.get("require_aps", False))
    require_paramed = False
    for rule in guide.get("paramed_requirements") or []:
        if age >= int(rule.get("min_age", 0)) and face >= float(rule.get("min_face", 0)):
            require_paramed = bool(rule.get("require_paramed", False))

    if decision == UWDecision.DECLINE:
        pass
    elif decision == UWDecision.REFER or require_aps and "aps" not in blob and "attending physician" not in blob:
        if require_aps and "aps" not in blob and "attending physician" not in blob and "medical records" not in blob:
            decision = UWDecision.CONDITIONAL_ACCEPT if decision == UWDecision.ACCEPT else decision
            reasons.append("APS required before bind")
    elif _class_rank(uw_class) >= _class_rank("table_c"):
        decision = UWDecision.REFER
        reasons.append("Table C+ requires medical director")

    if tobacco and uw_class in ("super_preferred", "preferred"):
        uw_class = "standard"
        reasons.append("Tobacco blocks preferred classes")

    return LifeMedicalDecision(
        decision=decision,
        underwriting_class=uw_class,
        tobacco=tobacco,
        flat_extras_per_1000=round(flat_extra, 2),
        require_aps=require_aps,
        require_paramed=require_paramed,
        reasons=reasons,
        findings=findings,
        vitals=vitals,
        guide_id=str(guide.get("guide_id") or ""),
    )
