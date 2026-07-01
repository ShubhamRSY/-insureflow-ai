from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from insureflow.models.mortgage import MortgageBundle, MortgageMemo


class LoanProduct(str, Enum):
    CONVENTIONAL_30_FIXED = "conventional_30_fixed"
    CONVENTIONAL_15_FIXED = "conventional_15_fixed"
    FHA_30_FIXED = "fha_30_fixed"
    VA_30_FIXED = "va_30_fixed"
    USDA_30_FIXED = "usda_30_fixed"
    JUMBO_30_FIXED = "jumbo_30_fixed"
    COMMERCIAL_5_1_ARM = "commercial_5_1_arm"


@dataclass(frozen=True)
class ProductRules:
    product: LoanProduct
    min_credit_score: int
    max_ltv: float
    max_dti: float
    min_down_payment_pct: float
    base_rate: float
    rate_lock_days: int = 45
    pmi_required_above_ltv: float = 80.0
    notes: str = ""


PRODUCT_CATALOG: dict[LoanProduct, ProductRules] = {
    LoanProduct.CONVENTIONAL_30_FIXED: ProductRules(
        product=LoanProduct.CONVENTIONAL_30_FIXED,
        min_credit_score=620,
        max_ltv=97.0,
        max_dti=43.0,
        min_down_payment_pct=3.0,
        base_rate=6.75,
        notes="Conforming conventional 30-year fixed",
    ),
    LoanProduct.CONVENTIONAL_15_FIXED: ProductRules(
        product=LoanProduct.CONVENTIONAL_15_FIXED,
        min_credit_score=620,
        max_ltv=90.0,
        max_dti=43.0,
        min_down_payment_pct=10.0,
        base_rate=6.125,
    ),
    LoanProduct.FHA_30_FIXED: ProductRules(
        product=LoanProduct.FHA_30_FIXED,
        min_credit_score=580,
        max_ltv=96.5,
        max_dti=50.0,
        min_down_payment_pct=3.5,
        base_rate=6.50,
        notes="FHA insured — MIP required",
    ),
    LoanProduct.VA_30_FIXED: ProductRules(
        product=LoanProduct.VA_30_FIXED,
        min_credit_score=580,
        max_ltv=100.0,
        max_dti=45.0,
        min_down_payment_pct=0.0,
        base_rate=6.375,
        notes="VA eligible veterans — funding fee applies",
    ),
    LoanProduct.USDA_30_FIXED: ProductRules(
        product=LoanProduct.USDA_30_FIXED,
        min_credit_score=640,
        max_ltv=100.0,
        max_dti=41.0,
        min_down_payment_pct=0.0,
        base_rate=6.625,
        notes="Rural development — property must be in eligible area",
    ),
    LoanProduct.JUMBO_30_FIXED: ProductRules(
        product=LoanProduct.JUMBO_30_FIXED,
        min_credit_score=700,
        max_ltv=80.0,
        max_dti=43.0,
        min_down_payment_pct=20.0,
        base_rate=7.125,
        notes="Loan amount > conforming limit",
    ),
    LoanProduct.COMMERCIAL_5_1_ARM: ProductRules(
        product=LoanProduct.COMMERCIAL_5_1_ARM,
        min_credit_score=680,
        max_ltv=75.0,
        max_dti=45.0,
        min_down_payment_pct=25.0,
        base_rate=7.50,
        rate_lock_days=60,
        notes="Commercial 5/1 ARM — min DSCR 1.20x",
    ),
}


@dataclass
class RateLockQuote:
    product: LoanProduct
    base_rate: float
    adjusted_rate: float
    rate_lock_expires: str
    rate_lock_days: int
    loan_amount: float
    monthly_pi: float
    pmi_required: bool
    pricing_adjustments: list[dict[str, Any]] = field(default_factory=list)
    eligible: bool = True
    ineligibility_reasons: list[str] = field(default_factory=list)


class LoanPricingEngine:
    """Rate lock and loan product eligibility engine."""

    def quote(
        self,
        bundle: MortgageBundle,
        memo: MortgageMemo,
        loan_amount: float | None = None,
        product: LoanProduct | None = None,
    ) -> RateLockQuote:
        from datetime import timedelta

        # Auto-select product
        if product is None:
            product = self._select_product(bundle, memo, loan_amount or 0)

        rules = PRODUCT_CATALOG[product]
        adjustments: list[dict[str, Any]] = []
        ineligible: list[str] = []
        rate = rules.base_rate

        credit_score = bundle.credit.credit_score if bundle.credit else 0
        ltv = memo.ltv_ratio or (bundle.collateral.ltv if bundle.collateral else 0)
        dti = memo.dti_ratio or 0

        if credit_score and credit_score < rules.min_credit_score:
            ineligible.append(f"Credit score {credit_score} below minimum {rules.min_credit_score}")
        if ltv and ltv > rules.max_ltv:
            ineligible.append(f"LTV {ltv:.1f}% exceeds product max {rules.max_ltv}%")
        if dti and dti > rules.max_dti:
            ineligible.append(f"DTI {dti:.1f}% exceeds product max {rules.max_dti}%")

        # Credit score pricing adjustments (LLPA-style)
        if credit_score >= 760:
            adjustments.append({"reason": "excellent_credit", "bps": -25})
            rate -= 0.25
        elif credit_score >= 700:
            adjustments.append({"reason": "good_credit", "bps": 0})
        elif credit_score >= 660:
            adjustments.append({"reason": "fair_credit", "bps": 50})
            rate += 0.50
        elif credit_score >= 620:
            adjustments.append({"reason": "marginal_credit", "bps": 100})
            rate += 1.00

        if ltv and ltv > 80:
            adjustments.append({"reason": "high_ltv", "bps": 25})
            rate += 0.25

        amount = loan_amount or (bundle.collateral.purchase_price if bundle.collateral else 0)
        if amount > 766_550:
            adjustments.append({"reason": "jumbo_threshold", "bps": 50})
            rate += 0.50

        pmi = bool(ltv and ltv > rules.pmi_required_above_ltv)
        monthly_pi = self._calc_monthly_pi(amount, rate, 30)

        lock_expires = (datetime.now(tz=timezone.utc) + timedelta(days=rules.rate_lock_days)).strftime("%Y-%m-%d")

        return RateLockQuote(
            product=product,
            base_rate=rules.base_rate,
            adjusted_rate=round(rate, 3),
            rate_lock_expires=lock_expires,
            rate_lock_days=rules.rate_lock_days,
            loan_amount=amount,
            monthly_pi=round(monthly_pi, 2),
            pmi_required=pmi,
            pricing_adjustments=adjustments,
            eligible=len(ineligible) == 0 and memo.decision.value in ("approve", "refer"),
            ineligibility_reasons=ineligible,
        )

    def _select_product(
        self,
        bundle: MortgageBundle,
        memo: MortgageMemo,
        loan_amount: float,
    ) -> LoanProduct:
        from insureflow.models.mortgage import ProductLine

        if bundle.product_line == ProductLine.COMMERCIAL_MORTGAGE:
            return LoanProduct.COMMERCIAL_5_1_ARM
        if loan_amount > 766_550:
            return LoanProduct.JUMBO_30_FIXED
        # Check for USDA indicators in documents
        for doc in bundle.documents:
            if "usda" in doc.source_path.lower():
                return LoanProduct.USDA_30_FIXED
        credit = bundle.credit.credit_score if bundle.credit else 700
        if credit < 620:
            return LoanProduct.FHA_30_FIXED
        return LoanProduct.CONVENTIONAL_30_FIXED

    @staticmethod
    def _calc_monthly_pi(principal: float, annual_rate: float, years: int) -> float:
        if principal <= 0 or annual_rate <= 0:
            return 0.0
        r = annual_rate / 100 / 12
        n = years * 12
        return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
