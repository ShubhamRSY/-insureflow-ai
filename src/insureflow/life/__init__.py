"""Life Insurance Underwriting Pipeline.

Modules:
  mortality        — Mortality tables (q_x, p_x, survival/mortality probs)
  term_formulas    — Term life: NSP, equivalence principle, gross loading, reserves
  whole_life_formulas — Whole life: A_x, ä_x, P_x, cash value, nonforfeiture CSV
  product_variants — Decreasing/increasing term, convertible, renewable
  underwriting_factors — Health, medical, lifestyle, financial, persistency models
  endowment_uw     — Endowment plan: premium capacity, savings ratio, parking detection
  ulip_uw          — ULIP: investor profiling, suitability, risk appetite, fund allocation
  money_back_uw    — Money-back: cash-flow matching, persistency, lapse risk
  annuity_uw       — Annuity/pension: longevity risk, family history, payout risk
  checklist        — 10-point compliance checklist
  screening        — SSN, MIB, Rx, OFAC screening
  medical_eval     — BMI, vitals, paramedical, class assignment
  financial        — HLV, income multiples, net worth, table rating, reinsurance
  decision_matrix  — Final disposition matrix
  memo             — Underwriting evaluation memo generator
  pipeline         — 4-step orchestrator
"""

from .annuity_uw import AnnuityUWResult, run_annuity_uw
from .endowment_uw import EndowmentUWResult, run_endowment_uw
from .money_back_uw import MoneyBackUWResult, run_money_back_uw
from .mortality import LIMITING_AGE, discount_factor, k_p_x, k_q_x, p_x, q_x, v_k
from .product_variants import (
    ConvertibleTermQuote,
    DecreasingTermQuote,
    IncreasingTermQuote,
    RenewableTermQuote,
    compute_convertible_term,
    compute_decreasing_term,
    compute_increasing_term,
    compute_renewable_term,
)
from .term_formulas import (
    TermLifeQuote,
    compute_full_quote,
    gross_premium_with_loading,
    level_net_premium,
    net_single_premium,
    present_value_annuity_due,
    present_value_benefits,
    prospective_reserve,
    recursive_reserve,
)
from .ulip_uw import InvestorProfile, ULIPUWResult, run_ulip_uw
from .underwriting_factors import (
    FinancialJustification,
    HealthAssessment,
    LifestyleAssessment,
    MedicalHistoryAssessment,
    PersistencyAssessment,
    UWClass,
    UWFactors,
    assess_financial,
    assess_health,
    assess_lifestyle,
    assess_medical_history,
    assess_persistency,
    classify_bp,
    classify_cholesterol,
    classify_uw_risk,
    compute_bmi,
)
from .whole_life_formulas import (
    WholeLifeQuote,
    compute_full_whole_life_quote,
    net_cash_surrender_value,
    prospective_reserve_whole_life,
    pv_whole_life_benefits,
    standard_nonforfeiture_csv,
    whole_life_annuity_due,
    whole_life_net_premium,
)

__all__ = [
    # Mortality
    "q_x",
    "p_x",
    "k_p_x",
    "k_q_x",
    "discount_factor",
    "v_k",
    "LIMITING_AGE",
    # Term
    "TermLifeQuote",
    "present_value_benefits",
    "present_value_annuity_due",
    "level_net_premium",
    "net_single_premium",
    "gross_premium_with_loading",
    "prospective_reserve",
    "recursive_reserve",
    "compute_full_quote",
    # Whole Life
    "WholeLifeQuote",
    "pv_whole_life_benefits",
    "whole_life_annuity_due",
    "whole_life_net_premium",
    "prospective_reserve_whole_life",
    "standard_nonforfeiture_csv",
    "net_cash_surrender_value",
    "compute_full_whole_life_quote",
    # Product Variants
    "DecreasingTermQuote",
    "IncreasingTermQuote",
    "ConvertibleTermQuote",
    "RenewableTermQuote",
    "compute_decreasing_term",
    "compute_increasing_term",
    "compute_convertible_term",
    "compute_renewable_term",
    # Underwriting Factors
    "UWClass",
    "UWFactors",
    "HealthAssessment",
    "MedicalHistoryAssessment",
    "LifestyleAssessment",
    "FinancialJustification",
    "PersistencyAssessment",
    "compute_bmi",
    "classify_bp",
    "classify_cholesterol",
    "assess_health",
    "assess_medical_history",
    "assess_lifestyle",
    "assess_financial",
    "assess_persistency",
    "classify_uw_risk",
    # Endowment UW
    "EndowmentUWResult",
    "run_endowment_uw",
    # ULIP UW
    "InvestorProfile",
    "ULIPUWResult",
    "run_ulip_uw",
    # Money-Back UW
    "MoneyBackUWResult",
    "run_money_back_uw",
    # Annuity UW
    "AnnuityUWResult",
    "run_annuity_uw",
]
