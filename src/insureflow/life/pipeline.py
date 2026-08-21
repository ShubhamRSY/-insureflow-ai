"""Life Insurance Underwriting Pipeline — 4-Step Orchestrator.

Step 1: Intake & Triage (10-point checklist compliance)
Step 2: Identity & Database Screening (SSN, MIB, Rx, OFAC)
Step 3: Medical & Build Evaluation (BMI, vitals, paramedical, class)
Step 4: Financial UW & Needs Analysis (HLV, income multiples, net worth, reinsurance)

Product families: Level Term, Whole Life, Universal, Endowment, ULIP,
Money-Back, Annuities/Pensions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import extract_life_factors

from .checklist import ChecklistResult, run_checklist
from .decision_matrix import FinalDecision, resolve_final_decision
from .financial import FinancialAnalysisResult, run_financial_analysis
from .medical_eval import MedicalEvalResult, run_medical_eval
from .memo import generate_memo
from .screening import ScreeningResult, run_screening

logger = logging.getLogger(__name__)

# Product family-specific requirements
PRODUCT_FAMILY_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "term": {
        "label": "Level Term Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
    },
    "whole_life": {
        "label": "Whole Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
    },
    "universal": {
        "label": "Universal Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
    },
    "endowment": {
        "label": "Endowment Plan",
        "requires_medical": True,
        "requires_financial": True,  # High premium — strict financial scrutiny
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
    },
    "ulip": {
        "label": "Unit-Linked Insurance Plan (ULIP)",
        "requires_medical": True,
        "requires_financial": True,
        "requires_suitability": True,  # Investor profiling required
        "requires_paramed_above": 250_000,
        "contestability_years": 2,
        "suicide_years": 2,
    },
    "money_back": {
        "label": "Money-Back Policy",
        "requires_medical": True,
        "requires_financial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
    },
    "annuity": {
        "label": "Annuity / Pension",
        "requires_medical": False,  # Longevity risk, not mortality
        "requires_financial": True,
        "requires_suitability": True,  # Senior suitability rules
        "requires_paramed_above": 0,
        "contestability_years": 0,  # No contestability for annuities
        "suicide_years": 0,
    },
}


def detect_product_family(product_id: str | None = None) -> str:
    """Detect product family from product_id."""
    if not product_id:
        return "term"
    pid = product_id.lower()
    if any(k in pid for k in ("ulip", "unit_linked", "variable")):
        return "ulip"
    if any(k in pid for k in ("endow", "with_profit")):
        return "endowment"
    if any(k in pid for k in ("money_back", "money-back", "survival")):
        return "money_back"
    if any(k in pid for k in ("annuit", "pension", "immediate", "deferred")):
        return "annuity"
    if any(k in pid for k in ("whole", "traditional", "participating")):
        return "whole_life"
    if any(k in pid for k in ("universal", "indexed", "variable_universal")):
        return "universal"
    return "term"


@dataclass
class LifePipelineResult:
    product_family: str = "term"
    product_label: str = ""
    bundle_id: str = ""

    # Step 1
    checklist: ChecklistResult | None = None
    # Step 2
    screening: ScreeningResult | None = None
    # Step 3
    medical: MedicalEvalResult | None = None
    # Step 4
    financial: FinancialAnalysisResult | None = None

    # Final
    final_decision: FinalDecision | None = None
    memo_text: str = ""

    findings: list[Finding] = field(default_factory=list)
    decision: UWDecision = UWDecision.ACCEPT
    human_review_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_family": self.product_family,
            "product_label": self.product_label,
            "bundle_id": self.bundle_id,
            "checklist": self.checklist.to_metadata() if self.checklist else None,
            "screening": self.screening.to_metadata() if self.screening else None,
            "medical": self.medical.to_metadata() if self.medical else None,
            "financial": self.financial.to_metadata() if self.financial else None,
            "final_decision": self.final_decision.to_metadata() if self.final_decision else None,
            "decision": self.decision.value,
            "human_review_required": self.human_review_required,
            "memo": self.memo_text,
            "findings_count": len(self.findings),
            "findings_by_severity": {
                "critical": len([f for f in self.findings if f.severity == RiskSeverity.CRITICAL]),
                "high": len([f for f in self.findings if f.severity == RiskSeverity.HIGH]),
                "moderate": len([f for f in self.findings if f.severity == RiskSeverity.MODERATE]),
                "low": len([f for f in self.findings if f.severity == RiskSeverity.LOW]),
            },
        }


def run_life_pipeline(
    bundle: SubmissionBundle,
    *,
    product_id: str | None = None,
    coverage_id: str | None = None,
    state_code: str | None = None,
) -> LifePipelineResult:
    """Run the complete 4-step Life Insurance underwriting pipeline."""
    factors = extract_life_factors(bundle)
    family = detect_product_family(product_id)
    family_req = PRODUCT_FAMILY_REQUIREMENTS.get(family, PRODUCT_FAMILY_REQUIREMENTS["term"])
    result = LifePipelineResult(
        product_family=family,
        product_label=family_req["label"],
        bundle_id=bundle.bundle_id,
    )

    logger.info("Life pipeline: family=%s, bundle=%s", family, bundle.bundle_id)

    # ── Step 1: Intake & Triage ──────────────────────────────────
    checklist = run_checklist(bundle)
    result.checklist = checklist
    result.findings.extend(checklist.findings)

    if not checklist.all_passed:
        result.decision = UWDecision.REFER
        result.human_review_required = True

    # ── Step 2: Identity & Database Screening ────────────────────
    screening = run_screening(bundle)
    result.screening = screening
    result.findings.extend(screening.findings)
    if screening.decision == UWDecision.DECLINE:
        result.decision = UWDecision.DECLINE
    elif screening.decision == UWDecision.REFER and result.decision != UWDecision.DECLINE:
        result.decision = UWDecision.REFER
        result.human_review_required = True

    # ── Step 3: Medical & Build Evaluation ──────────────────────
    if family_req.get("requires_medical", True):
        medical = run_medical_eval(bundle)
        result.medical = medical
        result.findings.extend(medical.findings)
        if medical.decision == UWDecision.DECLINE:
            result.decision = UWDecision.DECLINE
        elif medical.decision == UWDecision.REFER and result.decision != UWDecision.DECLINE:
            result.decision = UWDecision.REFER
            result.human_review_required = True

    # ── Step 4: Financial UW & Needs Analysis ───────────────────
    if family_req.get("requires_financial", True):
        financial = run_financial_analysis(bundle)
        result.financial = financial
        result.findings.extend(financial.findings)
        if financial.decision == UWDecision.DECLINE:
            result.decision = UWDecision.DECLINE
        elif financial.decision == UWDecision.REFER and result.decision != UWDecision.DECLINE:
            result.decision = UWDecision.REFER
            result.human_review_required = True

    # ── Final Decision Matrix ────────────────────────────────────
    uw_class = "standard"
    table_index = 0
    flat_extras = 0.0

    if result.medical and result.medical.medical_decision:
        uw_class = result.medical.medical_decision.underwriting_class
        flat_extras = result.medical.medical_decision.flat_extras_per_1000

    final = resolve_final_decision(
        uw_class=uw_class,
        flat_extras=flat_extras,
        table_index=table_index,
        override_decision=result.decision if result.decision != UWDecision.ACCEPT else None,
    )
    result.final_decision = final
    result.decision = final.decision
    result.human_review_required = final.human_review_required or result.human_review_required

    # ── Generate Memo ────────────────────────────────────────────
    result.memo_text = generate_memo(
        bundle_id=bundle.bundle_id,
        product_type=family_req["label"],
        face_amount=float(factors.face_amount or 0),
        term_years=20,
        uw_class=uw_class,
        table_index=final.table_index,
        flat_extras=flat_extras,
        bmi=result.medical.bmi if result.medical else None,
        income=float(factors.income or 0),
        net_worth=float(getattr(factors, "net_worth", 0) or 0),
        age=factors.age,
        decision=result.decision,
        checklist=result.checklist.to_metadata() if result.checklist else None,
        screening=result.screening.to_metadata() if result.screening else None,
        medical=result.medical.to_metadata() if result.medical else None,
        financial=result.financial.to_metadata() if result.financial else None,
        reinsurance=result.financial.reinsurance.to_metadata() if result.financial and result.financial.reinsurance else None,
        state_code=state_code or "",
    )

    return result
