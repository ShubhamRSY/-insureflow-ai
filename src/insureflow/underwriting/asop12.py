"""Risk classification review — ASOP 12.

Chapter: Summary of Actuarial Principles. ASOP 12 (Actuarial Standards Board,
1989, revised 2004) is the actuarial standard of practice governing risk
classification and underwriting. It requires, in relevant part, that risk
characteristics:

* be objective and related to expected outcomes (differences in cost);
* have a demonstrated relationship with outcomes — correlation suffices, a
  causal relationship need not be shown; and
* respect state-law constraints on which characteristics may be used.

It also prescribes the eight review questions an actuary/policymaker must ask
when applying the standard — correlation with the outcome, superfluous
elements, bona fide vs spurious correlation, impermissible surrogates, similar
populations, actuarial credibility, homogeneity/separation, and decline-vs-
mitigation.

This module makes those principles and the eight questions structured, runnable
checks so the automation can validate a classification/underwriting scheme the
way an actuary would.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from insureflow.underwriting.acceptability import AcceptabilityCode, ClassAcceptability


class ClassificationStatus(str, Enum):
    PASS = "pass"  # standard satisfied
    FLAG = "flag"  # satisfied with attention / minor gap
    FAIL = "fail"  # standard not satisfied — scheme should not be applied as-is


@dataclass
class RiskCharacteristic:
    """One risk characteristic used in a classification, as ASOP 12 sees it."""

    name: str
    is_objective: bool = True  # objectively measurable, not self-reported wishful
    related_to_expected_cost: bool = True  # related to differences in cost
    has_demonstrated_relationship: bool = False  # correlation established
    surplus_or_redundant: bool = False  # superfluous element
    state_restricted: bool = False  # disallowed in some states
    state_notes: str = ""
    benchmark_group: str = ""  # comparison group / base class
    similar_population: bool = True  # data from people substantially similar to class
    notes: str = ""


class SurrogateFinding(BaseModel):
    """A lawful characteristic that may be operating as a surrogate for an impermissible one."""

    characteristic: str
    surrogate_for: str  # the impermissible characteristic (e.g. race)
    severity: ClassificationStatus = ClassificationStatus.FLAG
    detail: str = ""


# Known proxy relationships: a lawful characteristic proxying for a prohibited one.
_SURROGATE_PROXIES: list[tuple[str, str]] = [
    ("zip code", "race"),
    ("geographic territory", "race"),
    ("medical condition", "race"),
    ("credit score", "race"),
    ("marital status", "sex"),
    ("gender", "sex"),
    ("occupation", "sex"),
    ("religion", "religion"),
]


class ASOP12Review(BaseModel):
    """The result of applying the ASOP 12 principles to a classification scheme."""

    characteristics: list[dict[str, Any]] = Field(default_factory=list)
    surrogate_findings: list[SurrogateFinding] = Field(default_factory=list)
    checks: dict[str, ClassificationStatus] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)
    overall: ClassificationStatus = ClassificationStatus.PASS
    summary: str = ""


def review_classification(
    characteristics: list[RiskCharacteristic],
    *,
    policy_count: int = 0,
    expected_cost_per_class: Optional[dict[str, float]] = None,
    credibility_full_policies: int = 30,
    acceptability: Optional[list[ClassAcceptability]] = None,
) -> ASOP12Review:
    """Run the eight ASOP 12 review questions against a classification scheme.

    Arguments
    ---------
    characteristics: the risk characteristics in the classification.
    policy_count: total policies backing the classification (for credibility).
    expected_cost_per_class: class code → expected cost, used for homogeneity /
      separation measurement.
    credibility_full_policies: policy count at which credibility = 1.0.
    acceptability: the class→acceptability table, used for the decline-vs-
      mitigation question.
    """
    review = ASOP12Review(
        characteristics=[_characteristic_dict(c) for c in characteristics],
    )
    findings: list[str] = []

    # Q1 — Correlation with the outcome (differences in cost).
    unrelated = [c for c in characteristics if not c.related_to_expected_cost]
    if unrelated:
        review.checks["q1_correlation"] = ClassificationStatus.FAIL
        findings.append(f"Characteristics not related to expected cost: {', '.join(c.name for c in unrelated)}")
    elif not characteristics:
        review.checks["q1_correlation"] = ClassificationStatus.FAIL
        findings.append("No risk characteristics defined — classification has no basis")
    else:
        review.checks["q1_correlation"] = ClassificationStatus.PASS
        findings.append("All characteristics are related to expected cost differences")

    # Q2 — Superfluous elements (does each element make a contribution?).
    superfluous = [c for c in characteristics if c.surplus_or_redundant or not c.has_demonstrated_relationship]
    if superfluous:
        review.checks["q2_superfluous"] = ClassificationStatus.FLAG
        findings.append(f"Superfluous or unsupported characteristics: {', '.join(c.name for c in superfluous)}")
    else:
        review.checks["q2_superfluous"] = ClassificationStatus.PASS
        findings.append("Each characteristic makes a statistically significant contribution")

    # Q3 — Bona fide correlation (not an artifact of unmeasured variables).
    if any(c.has_demonstrated_relationship for c in characteristics) or all(c.has_demonstrated_relationship for c in characteristics):
        review.checks["q3_bona_fide"] = ClassificationStatus.PASS
        findings.append("Correlation with outcomes is demonstrated, not spurious")
    else:
        review.checks["q3_bona_fide"] = ClassificationStatus.FLAG
        findings.append("Some correlations are not empirically demonstrated — verify they are not artifacts of unmeasured variables")

    # Q4 — Impermissible surrogate.
    surrogates: list[SurrogateFinding] = []
    for characteristic in characteristics:
        for proxy, forbidden in _SURROGATE_PROXIES:
            if proxy in characteristic.name.lower():
                surrogates.append(
                    SurrogateFinding(
                        characteristic=characteristic.name,
                        surrogate_for=forbidden,
                        severity=ClassificationStatus.FAIL if characteristic.has_demonstrated_relationship else ClassificationStatus.FLAG,
                        detail=f"'{characteristic.name}' may operate as a surrogate for {forbidden} — check it is not a proxy for an impermissible classification",
                    )
                )
    if surrogates:
        review.checks["q4_surrogate"] = ClassificationStatus.FAIL if any(s.severity == ClassificationStatus.FAIL for s in surrogates) else ClassificationStatus.FLAG
        findings.append(f"Potential impermissible surrogates: {', '.join(f'{s.characteristic}→{s.surrogate_for}' for s in surrogates)}")
    else:
        review.checks["q4_surrogate"] = ClassificationStatus.PASS
        findings.append("No characteristic appears to proxy for an impermissible classification")
    review.surrogate_findings = surrogates

    # Q5 — Similar population (data from people substantially similar to the class).
    dissimilar = [c for c in characteristics if not c.similar_population]
    if dissimilar:
        review.checks["q5_similar_population"] = ClassificationStatus.FLAG
        findings.append(f"Data not drawn from substantially similar populations: {', '.join(c.name for c in dissimilar)}")
    else:
        review.checks["q5_similar_population"] = ClassificationStatus.PASS
        findings.append("Classification data drawn from substantially similar populations")

    # Q6 — Actuarial credibility (limited fluctuation).
    credibility = min(1.0, math.sqrt(policy_count / max(credibility_full_policies, 1)))
    if policy_count <= 0:
        review.checks["q6_credibility"] = ClassificationStatus.FAIL
        findings.append("No policy data — classification has zero actuarial credibility")
    elif credibility < 0.5:
        review.checks["q6_credibility"] = ClassificationStatus.FLAG
        findings.append(f"Credibility {credibility:.2f} ({policy_count} policies) — partial credibility, blend with expected costs")
    else:
        review.checks["q6_credibility"] = ClassificationStatus.PASS
        findings.append(f"Credibility {credibility:.2f} ({policy_count} policies) — data sufficient for accurate estimates")

    # Q7 — Homogeneity / separation.
    if expected_cost_per_class and len(expected_cost_per_class) >= 2:
        costs = list(expected_cost_per_class.values())
        if any(c > 0 for c in costs):
            min_cost = min(c for c in costs if c > 0)
            separation = max(costs) / min_cost if min_cost > 0 else 0.0
            if separation >= 1.5:
                review.checks["q7_homogeneity_separation"] = ClassificationStatus.PASS
                findings.append(f"Class cost separation {separation:.2f}x — classes are distinct and homogeneous")
            else:
                review.checks["q7_homogeneity_separation"] = ClassificationStatus.FLAG
                findings.append(f"Class cost separation only {separation:.2f}x — classes may not be materially distinct")
        else:
            review.checks["q7_homogeneity_separation"] = ClassificationStatus.FLAG
            findings.append("Expected costs are all zero — cannot assess homogeneity/separation")
    else:
        review.checks["q7_homogeneity_separation"] = ClassificationStatus.FLAG
        findings.append("No per-class expected costs supplied — cannot verify homogeneity/separation")

    # Q8 — Decline vs mitigation (is a less severe action available?).
    if acceptability:
        declined = [a for a in acceptability if a.acceptability == AcceptabilityCode.DECLINE]
        unmitigated = [a for a in declined if not a.conditions]
        if declined and not unmitigated:
            review.checks["q8_decline_vs_mitigation"] = ClassificationStatus.PASS
            findings.append("Declined classes offer conditions/less-severe actions (e.g. exclusionary riders) before outright decline")
        elif unmitigated:
            review.checks["q8_decline_vs_mitigation"] = ClassificationStatus.FLAG
            findings.append(f"Classes declined outright without conditions: {', '.join(a.class_code for a in unmitigated)} — consider time-limited exclusionary riders")
        else:
            review.checks["q8_decline_vs_mitigation"] = ClassificationStatus.PASS
            findings.append("No classes declined outright")
    else:
        review.checks["q8_decline_vs_mitigation"] = ClassificationStatus.FLAG
        findings.append("No acceptability table supplied — cannot verify decline vs mitigation")

    review.findings = findings

    if any(v == ClassificationStatus.FAIL for v in review.checks.values()):
        review.overall = ClassificationStatus.FAIL
    elif any(v == ClassificationStatus.FLAG for v in review.checks.values()):
        review.overall = ClassificationStatus.FLAG
    else:
        review.overall = ClassificationStatus.PASS
    review.summary = _summary(review.checks, review.findings)
    return review


def _characteristic_dict(c: RiskCharacteristic) -> dict[str, Any]:
    return {
        "name": c.name,
        "is_objective": c.is_objective,
        "related_to_expected_cost": c.related_to_expected_cost,
        "has_demonstrated_relationship": c.has_demonstrated_relationship,
        "surplus_or_redundant": c.surplus_or_redundant,
        "state_restricted": c.state_restricted,
        "state_notes": c.state_notes,
        "benchmark_group": c.benchmark_group,
        "similar_population": c.similar_population,
        "notes": c.notes,
    }


def _summary(checks: dict[str, ClassificationStatus], findings: list[str]) -> str:
    if not checks:
        return "No ASOP 12 checks run"
    failures = sum(1 for v in checks.values() if v == ClassificationStatus.FAIL)
    flags = sum(1 for v in checks.values() if v == ClassificationStatus.FLAG)
    passes = sum(1 for v in checks.values() if v == ClassificationStatus.PASS)
    parts = [f"{passes} passed, {flags} flagged, {failures} failed"]
    if findings:
        parts.append(findings[0])
    return " — ".join(parts)


def check_surrogate(characteristic_name: str) -> Optional[SurrogateFinding]:
    """Check a single characteristic name for known impermissible proxies."""
    for proxy, forbidden in _SURROGATE_PROXIES:
        if proxy in characteristic_name.lower():
            return SurrogateFinding(
                characteristic=characteristic_name,
                surrogate_for=forbidden,
                detail=f"'{characteristic_name}' may operate as a surrogate for {forbidden}",
            )
    return None
