"""Single source of truth for which finding category belongs to which
decision "gate" (risk assessment vs compliance).

Every section that summarizes findings by gate — the internal Report's
Decision Logic section, the in-app "Agent Findings" panel's Compliance
status, and any future section — must read gate membership from here, never
recompute or re-derive it independently. That duplication is exactly what
let "Decision Logic: Compliance gate — 0 findings" and "Compliance agent:
clean" both ship as bugs on the same underlying data: two different pieces
of code guessing at the same classification and drifting apart.
"""

from __future__ import annotations

from typing import Any

RISK_GATE_CATEGORIES = {
    "risk",
    "loss_history",
    "fraud",
    "ml_fraud",
    "ml_loss",
    "adverse_selection",
    "moral_hazard",
    "portfolio_risk",
    "limit_adequacy",
    "coverage_gaps",
    "uw_decision",
}
COMPLIANCE_GATE_CATEGORIES = {
    "compliance",
    "sanctions",
    "mib",
    "hallucination",
    "data_quality",
    "beneficiary_review",
}


def compute_gate_summary(key_findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Bucket the canonical key_findings list by gate — the one place this
    grouping is computed, for every consumer (PDF, in-app) to read."""
    risk_findings = [f for f in key_findings if isinstance(f, dict) and f.get("category") in RISK_GATE_CATEGORIES]
    compliance_findings = [f for f in key_findings if isinstance(f, dict) and f.get("category") in COMPLIANCE_GATE_CATEGORIES]
    return {
        "risk": {"findings": risk_findings, "count": len(risk_findings)},
        "compliance": {"findings": compliance_findings, "count": len(compliance_findings)},
    }
