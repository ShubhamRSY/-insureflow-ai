"""Life Insurance Underwriting Pipeline — 4-Step Orchestrator.

Step 1: Intake & Triage (10-point checklist compliance)
Step 2: Identity & Database Screening (SSN, MIB, Rx, OFAC)
Step 3: Medical & Build Evaluation (BMI, vitals, paramedical, class)
        + Full underwriting factor assessment (health, medical, lifestyle, financial, persistency)
Step 4: Actuarial Pricing & Financial UW (mortality, NSP, reserves, HLV, table rating, reinsurance)

Product families: Level Term, Whole Life, Universal, Endowment, ULIP,
Money-Back, Annuities/Pensions.
Product variants: Decreasing Term, Increasing Term, Convertible, Renewable.
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
from .underwriting_factors import (
    UWFactors,
    assess_financial,
    assess_health,
    assess_lifestyle,
    assess_medical_history,
    assess_persistency,
    classify_uw_risk,
)

logger = logging.getLogger(__name__)

# Product family-specific requirements
PRODUCT_FAMILY_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "term": {
        "label": "Level Term Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": "term",
    },
    "decreasing_term": {
        "label": "Decreasing Term Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": "decreasing_term",
    },
    "increasing_term": {
        "label": "Increasing Term Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": "increasing_term",
    },
    "convertible_term": {
        "label": "Convertible Term Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": "convertible_term",
    },
    "renewable_term": {
        "label": "Renewable Term Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": "renewable_term",
    },
    "whole_life": {
        "label": "Whole Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": "whole_life",
    },
    "universal": {
        "label": "Universal Life Insurance",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": "whole_life",  # uses whole life formulas as base
    },
    "endowment": {
        "label": "Endowment Plan",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": True,
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": "whole_life",  # endowment uses whole life base
    },
    "ulip": {
        "label": "Unit-Linked Insurance Plan (ULIP)",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": False,  # investment-linked, not actuarial
        "requires_suitability": True,
        "requires_paramed_above": 250_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": None,
    },
    "money_back": {
        "label": "Money-Back Policy",
        "requires_medical": True,
        "requires_financial": True,
        "requires_actuarial": False,  # simplified pricing
        "requires_paramed_above": 100_000,
        "contestability_years": 2,
        "suicide_years": 2,
        "actuarial_type": None,
    },
    "annuity": {
        "label": "Annuity / Pension",
        "requires_medical": False,
        "requires_financial": True,
        "requires_actuarial": False,
        "requires_suitability": True,
        "requires_paramed_above": 0,
        "contestability_years": 0,
        "suicide_years": 0,
        "actuarial_type": None,
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
    if any(k in pid for k in ("decreasing", "mortgage_protection")):
        return "decreasing_term"
    if any(k in pid for k in ("increasing", "coli", "cost_of_living")):
        return "increasing_term"
    if any(k in pid for k in ("convertible", "conversion")):
        return "convertible_term"
    if any(k in pid for k in ("renewable", "renewal")):
        return "renewable_term"
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
    # Step 3.5: Full UW factor assessment
    uw_factors: UWFactors | None = None
    # Step 4
    financial: FinancialAnalysisResult | None = None

    # Actuarial output
    actuarial_quote: dict[str, Any] | None = None
    mortality_table_used: str = "CSO 2017 VBT (illustrative)"
    interest_rate_used: float = 0.04

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
            "uw_factors": self.uw_factors.to_metadata() if self.uw_factors else None,
            "financial": self.financial.to_metadata() if self.financial else None,
            "actuarial_quote": self.actuarial_quote,
            "mortality_table": self.mortality_table_used,
            "interest_rate": self.interest_rate_used,
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


def _run_actuarial_pricing(
    family: str,
    family_req: dict[str, Any],
    factors: Any,
    age: int,
    sex: str,
    smoker: bool,
    face_amount: float,
    term_years: int,
    interest_rate: float,
    medical: MedicalEvalResult | None,
    uw_factors: UWFactors | None,
) -> dict[str, Any] | None:
    """Run actuarial pricing based on product family."""
    actuarial_type = family_req.get("actuarial_type")
    if not actuarial_type:
        return None

    try:
        result_dict: dict[str, Any] | None = None

        if actuarial_type == "term":
            from .term_formulas import compute_full_quote

            q_term = compute_full_quote(
                age=age,
                sex=sex,
                smoker=smoker,
                face_amount=face_amount,
                term_years=term_years,
                interest_rate=interest_rate,
            )
            if uw_factors and uw_factors.premium_multiplier > 0:
                q_term.level_net_premium = round(q_term.level_net_premium * uw_factors.premium_multiplier, 2)
                q_term.gross_premium = round(q_term.gross_premium * uw_factors.premium_multiplier, 2)
            result_dict = q_term.to_metadata()

        elif actuarial_type == "whole_life":
            from .whole_life_formulas import compute_full_whole_life_quote

            q_wl = compute_full_whole_life_quote(
                age=age,
                sex=sex,
                smoker=smoker,
                face_amount=face_amount,
                interest_rate=interest_rate,
            )
            if uw_factors and uw_factors.premium_multiplier > 0:
                q_wl.level_net_premium = round(q_wl.level_net_premium * uw_factors.premium_multiplier, 2)
                q_wl.gross_premium = round(q_wl.gross_premium * uw_factors.premium_multiplier, 2)
            result_dict = q_wl.to_metadata()

        elif actuarial_type == "decreasing_term":
            from .product_variants import compute_decreasing_term

            q_dt = compute_decreasing_term(
                age=age,
                sex=sex,
                smoker=smoker,
                initial_face=face_amount,
                term_years=term_years,
                interest_rate=interest_rate,
                amortize=True,
            )
            if uw_factors and uw_factors.premium_multiplier > 0:
                q_dt.level_premium = round(q_dt.level_premium * uw_factors.premium_multiplier, 2)
            result_dict = q_dt.to_metadata()

        elif actuarial_type == "increasing_term":
            from .product_variants import compute_increasing_term

            q_it = compute_increasing_term(
                age=age,
                sex=sex,
                smoker=smoker,
                initial_face=face_amount,
                term_years=term_years,
                interest_rate=interest_rate,
            )
            if uw_factors and uw_factors.premium_multiplier > 0:
                q_it.level_premium = round(q_it.level_premium * uw_factors.premium_multiplier, 2)
            result_dict = q_it.to_metadata()

        elif actuarial_type == "convertible_term":
            from .product_variants import compute_convertible_term

            q_ct = compute_convertible_term(
                age=age,
                sex=sex,
                smoker=smoker,
                face_amount=face_amount,
                term_years=term_years,
                interest_rate=interest_rate,
            )
            if uw_factors and uw_factors.premium_multiplier > 0:
                q_ct.level_premium = round(q_ct.level_premium * uw_factors.premium_multiplier, 2)
                q_ct.converted_premium = round(q_ct.converted_premium * uw_factors.premium_multiplier, 2)
            result_dict = q_ct.to_metadata()

        elif actuarial_type == "renewable_term":
            from .product_variants import compute_renewable_term

            q_rt = compute_renewable_term(
                age=age,
                sex=sex,
                smoker=smoker,
                face_amount=face_amount,
                interest_rate=interest_rate,
            )
            result_dict = q_rt.to_metadata()

        return result_dict

    except Exception as exc:
        logger.warning("Actuarial pricing failed: %s", exc)
        return {"error": str(exc)}

    return None


def run_life_pipeline(
    bundle: SubmissionBundle,
    *,
    product_id: str | None = None,
    coverage_id: str | None = None,
    state_code: str | None = None,
) -> LifePipelineResult:
    """Run the complete Life Insurance underwriting pipeline with actuarial engine."""
    factors = extract_life_factors(bundle)
    family = detect_product_family(product_id)
    family_req = PRODUCT_FAMILY_REQUIREMENTS.get(family, PRODUCT_FAMILY_REQUIREMENTS["term"])

    # Demographics for actuarial
    age = factors.age or 35
    sex = (getattr(factors, "sex", None) or "male").lower()
    smoker = (getattr(factors, "tobacco", "no") or "no").lower() in ("yes", "y", "true", "1")
    face_amount = float(factors.face_amount or 500_000)
    term_years = 20
    interest_rate = 0.04

    result = LifePipelineResult(
        product_family=family,
        product_label=family_req["label"],
        bundle_id=bundle.bundle_id,
        interest_rate_used=interest_rate,
    )

    logger.info(
        "Life pipeline: family=%s, age=%d, sex=%s, smoker=%s, face=$%.0f, bundle=%s",
        family,
        age,
        sex,
        smoker,
        face_amount,
        bundle.bundle_id,
    )

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

    # ── Step 3.5: Full Underwriting Factor Assessment ───────────
    # Structured assessment of health, medical history, lifestyle,
    # financial justification, and persistency
    health = assess_health(
        height_inches=getattr(factors, "height_inches", 70) or 70,
        weight_lbs=getattr(factors, "weight_lbs", 170) or 170,
        systolic_bp=getattr(factors, "systolic_bp", 120) or 120,
        diastolic_bp=getattr(factors, "diastolic_bp", 80) or 80,
        total_cholesterol=getattr(factors, "total_cholesterol", 190) or 190,
        hdl=getattr(factors, "hdl", 55) or 55,
        ldl=getattr(factors, "ldl", 110) or 110,
        fasting_glucose=getattr(factors, "fasting_glucose", 90) or 90,
        hba1c=getattr(factors, "hba1c", 5.2) or 5.2,
        nicotine_metabolite="positive" if smoker else "negative",
        bun=getattr(factors, "bun", 15) or 15,
        creatinine=getattr(factors, "creatinine", 1.0) or 1.0,
        egfr=getattr(factors, "egfr", 100) or 100,
        ast=getattr(factors, "ast", 25) or 25,
        alt=getattr(factors, "alt", 25) or 25,
        ggt=getattr(factors, "ggt", 30) or 30,
        stability_years=getattr(factors, "stability_years", 5) or 5,
    )

    medical_hist = assess_medical_history(
        personal_conditions=getattr(factors, "personal_conditions", []) or [],
        family_conditions=getattr(factors, "family_conditions", []) or [],
        parent_ages_at_death=getattr(factors, "parent_ages_at_death", []) or [],
        parent_causes=getattr(factors, "parent_causes", []) or [],
    )

    lifestyle = assess_lifestyle(
        tobacco_use="regular" if smoker else "none",
        tobacco_years=getattr(factors, "tobacco_years", 0) or 0,
        alcohol_use=getattr(factors, "alcohol_use", "none") or "none",
        substance_use=getattr(factors, "substance_use", "none") or "none",
        hazardous_hobbies=getattr(factors, "hazardous_hobbies", []) or [],
        occupation_risk=getattr(factors, "occupation_risk", "standard") or "standard",
        travel_risk=getattr(factors, "travel_risk", "low") or "low",
    )

    financial_just = assess_financial(
        annual_income=float(factors.income or 0),
        net_worth=float(getattr(factors, "net_worth", 0) or 0),
        requested_face=face_amount,
        existing_coverage=float(getattr(factors, "existing_coverage", 0) or 0),
        mortgage_balance=float(getattr(factors, "mortgage_balance", 0) or 0),
        dependents=int(getattr(factors, "dependents", 0) or 0),
        age=age,
    )

    persistency = assess_persistency(
        stated_purpose=getattr(factors, "purpose", "") or "",
        mortgage_years_remaining=int(getattr(factors, "mortgage_years", 0) or 0),
        children_min_age=int(getattr(factors, "children_min_age", 0) or 0),
        children_max_age=int(getattr(factors, "children_max_age", 0) or 0),
        retirement_age=int(getattr(factors, "retirement_age", 65) or 65),
        requested_term=term_years,
        current_age=age,
    )

    uw_factors = classify_uw_risk(
        age=age,
        sex=sex,
        smoker=smoker,
        health=health,
        medical=medical_hist,
        lifestyle=lifestyle,
        financial=financial_just,
        persistency=persistency,
    )
    result.uw_factors = uw_factors

    # Add UW factor findings
    for finding_text in uw_factors.findings:
        severity = RiskSeverity.MODERATE
        if "decline" in finding_text.lower() or "diabetic" in finding_text.lower():
            severity = RiskSeverity.CRITICAL
        elif "elevated" in finding_text.lower() or "history" in finding_text.lower():
            severity = RiskSeverity.HIGH
        result.findings.append(
            Finding(
                title="UW Factor",
                description=finding_text,
                severity=severity,
                category="life_uw_factors",
            )
        )

    if uw_factors.decision == "DECLINE":
        result.decision = UWDecision.DECLINE
    elif uw_factors.decision == "REFER" and result.decision != UWDecision.DECLINE:
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

    # ── Step 4.5: Actuarial Pricing ─────────────────────────────
    if family_req.get("requires_actuarial", False):
        actuarial = _run_actuarial_pricing(
            family=family,
            family_req=family_req,
            factors=factors,
            age=age,
            sex=sex,
            smoker=smoker,
            face_amount=face_amount,
            term_years=term_years,
            interest_rate=interest_rate,
            medical=result.medical,
            uw_factors=uw_factors,
        )
        result.actuarial_quote = actuarial

    # ── Final Decision Matrix ────────────────────────────────────
    uw_class = uw_factors.uw_class if uw_factors else "standard"
    table_index = 0
    flat_extras = uw_factors.flat_extra if uw_factors else 0.0

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
    memo_kwargs: dict[str, Any] = dict(
        bundle_id=bundle.bundle_id,
        product_type=family_req["label"],
        face_amount=face_amount,
        term_years=term_years,
        uw_class=uw_class,
        table_index=final.table_index,
        flat_extras=flat_extras,
        bmi=result.medical.bmi if result.medical else None,
        income=float(factors.income or 0),
        net_worth=float(getattr(factors, "net_worth", 0) or 0),
        age=age,
        decision=result.decision,
        checklist=result.checklist.to_metadata() if result.checklist else None,
        screening=result.screening.to_metadata() if result.screening else None,
        medical=result.medical.to_metadata() if result.medical else None,
        financial=result.financial.to_metadata() if result.financial else None,
        reinsurance=result.financial.reinsurance.to_metadata() if result.financial and result.financial.reinsurance else None,
        state_code=state_code or "",
    )
    if uw_factors:
        memo_kwargs["mortality_table"] = "CSO 2017 VBT"
        memo_kwargs["base_q_x"] = uw_factors.base_q_x
        memo_kwargs["risk_adjusted_q_x"] = uw_factors.risk_adjusted_q_x
    if result.actuarial_quote:
        memo_kwargs["actuarial"] = result.actuarial_quote

    result.memo_text = generate_memo(**memo_kwargs)

    return result
