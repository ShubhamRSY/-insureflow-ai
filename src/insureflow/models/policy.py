"""Structured models for the full insurance domain taxonomy.

These fill the gaps where the submission models only carried text labels or
inputs: premium accounting (earned/unearned/collected), policy architecture
(per-occurrence / aggregate / lifetime-max / SIR / coinsurance / elimination),
claim lifecycle (FNOL, adjudication, subrogation, salvage, defense), valuation
bases, health networks, life cash values, and the regulatory/financial screens
(insurability, utmost good faith, proximate cause, solvency/RBC, combined ratio).
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────
# Core financial & actuarial metrics
# ──────────────────────────────────────────────────────────────────────────
class EarningMethod(str, Enum):
    PRO_RATA = "pro_rata"
    SHORT_RATE = "short_rate"


class PremiumAccounting(BaseModel):
    """Written / collected / earned / unearned premium for a policy period."""

    written_premium: float = 0.0
    collected_premium: float = 0.0
    earned_premium: float = 0.0
    unearned_premium: float = 0.0
    collection_rate: Optional[float] = None
    earning_method: EarningMethod = EarningMethod.PRO_RATA
    policy_period_days: int = 0
    elapsed_days: int = 0
    as_of_date: Optional[date] = None
    basis_note: str = ""


class CombinedRatioResult(BaseModel):
    """Loss ratio + expense ratio = combined ratio (<100% is underwriting profit)."""

    loss_ratio: Optional[float] = None
    expense_ratio: Optional[float] = None
    combined_ratio: Optional[float] = None
    underwriting_profit: Optional[bool] = None
    detail: str = ""


class SolvencyAssessment(BaseModel):
    """Policyholder surplus (assets − liabilities) and simplified RBC coverage."""

    policyholder_surplus: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    required_risk_based_capital: float = 0.0
    rbc_ratio: Optional[float] = None
    solvent: Optional[bool] = None
    risk_grades: dict[str, float] = Field(default_factory=dict)
    detail: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Policy architecture — limits, deductibles, cost-sharing, waiting periods
# ──────────────────────────────────────────────────────────────────────────
class ValuationBasis(str, Enum):
    RCV = "rcv"
    ACV = "acv"
    AGREED_VALUE = "agreed_value"
    UNKNOWN = "unknown"


class ValuationAssessment(BaseModel):
    """Replacement-cost / actual-cash-value / agreed-value valuation of an asset."""

    basis: ValuationBasis = ValuationBasis.UNKNOWN
    replacement_cost: Optional[float] = None
    acv: Optional[float] = None
    agreed_value: Optional[float] = None
    depreciation_amount: Optional[float] = None
    depreciation_pct: Optional[float] = None
    effective_value: Optional[float] = None
    source: str = ""
    detail: str = ""


class HealthNetworkType(str, Enum):
    PPO = "ppo"
    HMO = "hmo"
    EPO = "epo"
    POS = "pos"
    INDEMNITY = "indemnity"
    NONE = "none"
    UNKNOWN = "unknown"


class HealthPlanFeatures(BaseModel):
    """Managed-care network structure (PPO / HMO / EPO / POS) and cost sharing."""

    network_type: HealthNetworkType = HealthNetworkType.UNKNOWN
    in_network: bool = True
    primary_care_referral_required: Optional[bool] = None
    out_of_network_coverage: Optional[bool] = None
    in_network_coinsurance: Optional[float] = None
    out_of_network_coinsurance: Optional[float] = None
    rating_factor: float = 1.0
    detail: str = ""


class LifeCashValue(BaseModel):
    """Projected cash value / surrender value accumulation for permanent life."""

    product_family: str = ""
    face_amount: float = 0.0
    annual_premium: float = 0.0
    years_projected: int = 20
    cash_value_schedule: list[dict[str, Any]] = Field(default_factory=list)
    guaranteed: bool = False
    notes: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Claims lifecycle — FNOL, adjudication, subrogation, salvage, defense
# ──────────────────────────────────────────────────────────────────────────
class NoticeOfLoss(BaseModel):
    """First Notice of Loss (FNOL) — the initial claim notification."""

    fnol_id: str
    claim_id: str = ""
    reported_at: date
    loss_date: date
    line_of_business: str = ""
    cause: str = ""
    reporter: str = ""
    description: str = ""
    status: str = "submitted"  # submitted | acknowledged | assigned | pending_policy_check


class ClaimDecision(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    SETTLED = "settled"
    PENDING = "pending"


class ClaimAdjudication(BaseModel):
    """Outcome of evaluating one claim against the policy's coverage terms."""

    claim_id: str
    coverage_valid: bool
    decision: ClaimDecision
    denial_reason: str = ""
    settlement_amount: Optional[float] = None
    paid_indemnity: float = 0.0
    defense_costs: float = 0.0
    disposition_detail: str = ""


class AdjudicationReview(BaseModel):
    decisions: list[ClaimAdjudication] = Field(default_factory=list)
    approved_count: int = 0
    denied_count: int = 0
    settled_count: int = 0
    pending_count: int = 0
    total_paid_indemnity: float = 0.0
    total_defense_costs: float = 0.0
    total_settlements: float = 0.0
    summary: str = ""


class SubrogationStatus(str, Enum):
    NOT_PURSUED = "not_pursued"
    PURSUED = "pursued"
    RECOVERED = "recovered"
    WAIVED = "waived"
    CLOSED = "closed"


class SubrogationRecovery(BaseModel):
    """Insurer stepping into the insured's shoes to recover from a negligent third party."""

    claim_id: str
    status: SubrogationStatus = SubrogationStatus.NOT_PURSUED
    third_party: str = ""
    potential_recovery: float = 0.0
    recovery_amount: float = 0.0
    recovery_percent: Optional[float] = None
    detail: str = ""


class SalvageRecovery(BaseModel):
    """Recovery from the retention/resale of damaged property to offset claim costs."""

    claim_id: str
    property_description: str = ""
    salvage_value: float = 0.0
    resale_amount: float = 0.0
    offset_amount: float = 0.0
    detail: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Regulatory, legal & insurability screens
# ──────────────────────────────────────────────────────────────────────────
class InsurabilityCriteria(BaseModel):
    """The five insurability requirements plus the catastrophic-exclusion check."""

    fortuitous: bool = False
    measurable: bool = False
    large_pool: bool = False
    calculable_probability: bool = False
    affordable_premium: bool = False
    no_catastrophic_exclusion: bool = True
    insurable: bool = False
    failed_criteria: list[str] = Field(default_factory=list)
    detail: str = ""


class DisclosureAssessment(BaseModel):
    """Utmost good faith — material misrepresentation, concealment, warranty breach."""

    utmost_good_faith: bool = True
    material_misrepresentation: bool = False
    concealment: bool = False
    warranty_breach: bool = False
    undisclosed_claims: list[str] = Field(default_factory=list)
    warranty_breaches: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    detail: str = ""


class LegalRemedyType(str, Enum):
    NONE = "none"
    VOIDANCE = "voidance"
    RESCISSION = "rescission"
    CLAIM_DENIAL = "claim_denial"
    CONDITIONAL = "conditional"


class LegalRemedy(BaseModel):
    """Remedy for misrepresentation / concealment / warranty breach."""

    remedy: LegalRemedyType = LegalRemedyType.NONE
    basis: str = ""
    detail: str = ""


class ProximateCauseResult(BaseModel):
    """Proximate-cause analysis: covered peril, unbroken chain, exclusion carve-outs."""

    cause: str = ""
    description: str = ""
    covered_peril: bool = False
    excluded_peril: str = ""
    unbroken_chain: bool = False
    proximate_cause: str = ""
    decision: str = "not_covered"  # covered | not_covered | indeterminate
    reasoning: str = ""
