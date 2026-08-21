"""Final Underwriting Decision Matrix.

Combines all steps into a final disposition:
  - Preferred Best / Preferred Plus
  - Standard / Standard Plus
  - Rated (Table Ratings / Flat Extras)
  - Postpone / Decline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision

# Decision matrix — maps UW class to disposition
DECISION_MATRIX: list[dict[str, Any]] = [
    {
        "class": "super_preferred",
        "label": "Preferred Best / Preferred Plus",
        "description": "Pristine health, ideal build (BMI ≤ 25), no tobacco, clean family history. Lowest rate tier.",
        "disposition": "ISSUE_AS_APPLIED",
    },
    {
        "class": "preferred",
        "label": "Preferred Non-Tobacco",
        "description": "Excellent health, good build, no tobacco. Near-best rate tier.",
        "disposition": "ISSUE_AS_APPLIED",
    },
    {
        "class": "standard_plus",
        "label": "Standard Plus",
        "description": "Above-average health, minor well-managed issues.",
        "disposition": "ISSUE_AS_APPLIED",
    },
    {
        "class": "standard",
        "label": "Standard",
        "description": "Average build and minor, well-managed health issues.",
        "disposition": "ISSUE_AS_APPLIED",
    },
    {
        "class": "table_a",
        "label": "Rated — Table A (25% surcharge)",
        "description": "Moderate impairment (controlled hypertension, elevated BMI). +25% over standard.",
        "disposition": "ISSUE_WITH_AMENDMENTS",
    },
    {
        "class": "table_b",
        "label": "Rated — Table B (50% surcharge)",
        "description": "Significant impairment. +50% over standard.",
        "disposition": "ISSUE_WITH_AMENDMENTS",
    },
    {
        "class": "table_c",
        "label": "Rated — Table C (75% surcharge)",
        "description": "Major impairment. +75% over standard.",
        "disposition": "ISSUE_WITH_AMENDMENTS",
    },
    {
        "class": "table_d",
        "label": "Rated — Table D (100% surcharge)",
        "description": "Severe impairment. Applicant pays double the standard rate.",
        "disposition": "ISSUE_WITH_AMENDMENTS",
    },
    {
        "class": "substandard",
        "label": "Decline / Postpone",
        "description": "Severe, uncontrolled conditions or unresolvable financial discrepancies.",
        "disposition": "DECLINE_OR_POSTPONE",
    },
]


def get_disposition(uw_class: str) -> dict[str, Any]:
    for entry in DECISION_MATRIX:
        if entry["class"] == uw_class:
            return entry
    # Default to standard
    return DECISION_MATRIX[3]


@dataclass
class FinalDecision:
    disposition: str = ""
    disposition_label: str = ""
    disposition_description: str = ""
    uw_class: str = "standard"
    table_index: int = 0
    flat_extras_per_1000: float = 0.0
    final_premium_multiplier: float = 1.0
    human_review_required: bool = False
    findings: list[Finding] = field(default_factory=list)
    decision: UWDecision = UWDecision.ACCEPT
    open_conditions: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "disposition": self.disposition,
            "disposition_label": self.disposition_label,
            "disposition_description": self.disposition_description,
            "uw_class": self.uw_class,
            "table_index": self.table_index,
            "flat_extras_per_1000": self.flat_extras_per_1000,
            "final_premium_multiplier": self.final_premium_multiplier,
            "human_review_required": self.human_review_required,
            "open_conditions": self.open_conditions,
        }


def resolve_final_decision(
    uw_class: str,
    flat_extras: float = 0.0,
    table_index: int = 0,
    override_decision: UWDecision | None = None,
) -> FinalDecision:
    """Resolve the final underwriting decision from class, table, and extras."""
    result = FinalDecision()
    result.uw_class = uw_class
    result.flat_extras_per_1000 = flat_extras

    # Table index from class name
    if table_index == 0 and uw_class.startswith("table_"):
        letter = uw_class.replace("table_", "")
        if letter.isalpha():
            table_index = ord(letter.lower()) - ord("a") + 1
    result.table_index = table_index

    # Premium multiplier: (1 + 0.25 × table_index)
    result.final_premium_multiplier = round(1.0 + 0.25 * table_index, 2)

    # Get disposition
    disp = get_disposition(uw_class)
    result.disposition = disp["disposition"]
    result.disposition_label = disp["label"]
    result.disposition_description = disp["description"]

    # Map disposition to UWDecision
    if disp["disposition"] == "DECLINE_OR_POSTPONE":
        result.decision = UWDecision.DECLINE
    elif disp["disposition"] == "ISSUE_WITH_AMENDMENTS":
        result.decision = UWDecision.CONDITIONAL_ACCEPT
    else:
        result.decision = UWDecision.ACCEPT

    # Override from upstream
    if override_decision:
        result.decision = override_decision

    # Human review required for any rated case or refer
    result.human_review_required = table_index > 0 or result.decision in (UWDecision.REFER, UWDecision.DECLINE)

    if flat_extras > 0:
        result.findings.append(
            Finding(
                title=f"Flat extra ${flat_extras:.0f}/1,000 applied",
                description=f"${flat_extras:.0f} per $1,000 of face amount for hazardous avocations.",
                severity=RiskSeverity.MODERATE,
                category="life_decision",
            )
        )

    if table_index > 0:
        letter = chr(ord("A") + table_index - 1) if table_index <= 16 else f"T{table_index}"
        result.findings.append(
            Finding(
                title=f"Table {letter} rating — {result.final_premium_multiplier}× standard premium",
                description=f"{(result.final_premium_multiplier - 1) * 100:.0f}% surcharge over standard rate.",
                severity=RiskSeverity.MODERATE,
                category="life_decision",
            )
        )

    return result
