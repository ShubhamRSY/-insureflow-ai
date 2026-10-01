from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from insureflow.decisions import is_bind_eligible
from insureflow.models.mortgage import MortgageBundle, MortgageMemo
from insureflow.mortgage.commercial_metrics import compute_commercial_metrics


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
    """Underwriting and pricing rules for one product.

    Residential products are judged on the borrower's personal balance
    sheet: ``min_credit_score`` and ``max_dti``. Commercial products are
    judged on the property's cash flow and leverage: ``min_dscr`` and
    ``min_debt_yield``. ``basis`` says which set applies, so a commercial
    quote can never be denied for a personal score or a DTI that a
    commercial borrower does not have.
    """

    product: LoanProduct
    min_credit_score: int | None = None
    max_ltv: float = 100.0
    max_dti: float | None = None
    min_down_payment_pct: float = 0.0
    base_rate: float = 0.0
    rate_lock_days: int = 45
    pmi_required_above_ltv: float = 80.0
    notes: str = ""
    basis: str = "personal"
    min_dscr: float | None = None
    min_debt_yield: float | None = None

    @property
    def is_commercial(self) -> bool:
        return self.basis == "commercial"


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
        basis="commercial",
        max_ltv=75.0,
        min_down_payment_pct=25.0,
        base_rate=7.50,
        rate_lock_days=60,
        min_dscr=1.20,
        min_debt_yield=0.08,
        notes="Commercial 5/1 ARM — underwritten on property DSCR and debt yield, not borrower DTI or personal credit score",
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
        amount = loan_amount or (bundle.collateral.purchase_price if bundle.collateral else 0)

        if rules.is_commercial:
            rate = self._apply_commercial_pricing(rules, bundle, amount, ltv, adjustments)
            ineligible.extend(self._commercial_ineligibility(rules, bundle, amount, ltv))
        else:
            if rules.min_credit_score and credit_score and credit_score < rules.min_credit_score:
                ineligible.append(f"Credit score {credit_score} below minimum {rules.min_credit_score}")
            if ltv and ltv > rules.max_ltv:
                ineligible.append(f"LTV {ltv:.1f}% exceeds product max {rules.max_ltv}%")
            if rules.max_dti and dti and dti > rules.max_dti:
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

            if amount > 766_550:
                adjustments.append({"reason": "jumbo_threshold", "bps": 50})
                rate += 0.50

        pmi = bool(rules.is_commercial is False and ltv and ltv > rules.pmi_required_above_ltv)
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
            eligible=len(ineligible) == 0 and is_bind_eligible(memo.decision),
            ineligibility_reasons=ineligible,
        )

    def _commercial_ineligibility(
        self,
        rules: ProductRules,
        bundle: MortgageBundle,
        amount: float,
        ltv: float,
    ) -> list[str]:
        """Commercial eligibility: DSCR, debt yield and LTV.

        A commercial borrower is an entity. Its personal credit score and
        DTI say nothing about whether the property services its debt, so
        neither is consulted here. When a metric cannot be computed that is
        ineligibility, not a pass: an unpriced deal is not a qualified one.
        """
        metrics = compute_commercial_metrics(bundle, loan_amount=amount or None)
        reasons: list[str] = []

        dscr = metrics.dscr.dscr
        if dscr is None:
            reasons.append("DSCR could not be computed from the submitted documents")
        elif rules.min_dscr and dscr < rules.min_dscr:
            reasons.append(f"DSCR {dscr:.2f}x below product minimum {rules.min_dscr:.2f}x")

        if metrics.debt_yield is None:
            reasons.append("Debt yield could not be computed: requires annual NOI and a loan amount")
        elif rules.min_debt_yield and metrics.debt_yield < rules.min_debt_yield:
            reasons.append(f"Debt yield {metrics.debt_yield * 100:.1f}% below product minimum {rules.min_debt_yield * 100:.1f}%")

        effective_ltv = metrics.ltv if metrics.ltv is not None else ltv
        if effective_ltv and effective_ltv > rules.max_ltv:
            reasons.append(f"LTV {effective_ltv:.1f}% exceeds product max {rules.max_ltv}%")
        elif not effective_ltv:
            reasons.append("LTV could not be determined: no appraised value or purchase price on file")

        return reasons

    def _apply_commercial_pricing(
        self,
        rules: ProductRules,
        bundle: MortgageBundle,
        amount: float,
        ltv: float,
        adjustments: list[dict[str, Any]],
    ) -> float:
        """Price a commercial deal off property cash flow and leverage.

        Thinner DSCR and lower debt yield mean less cushion for the lender,
        which is worth more than the borrower's personal credit. Higher LTV
        and larger balances carry more exposure, so they price wider.
        """
        metrics = compute_commercial_metrics(bundle, loan_amount=amount or None)
        rate = rules.base_rate

        dscr = metrics.dscr.dscr
        if dscr is not None:
            if dscr >= 1.50:
                adjustments.append({"reason": "strong_dscr", "dscr": round(dscr, 2), "bps": -20})
                rate -= 0.20
            elif dscr >= 1.35:
                adjustments.append({"reason": "adequate_dscr", "dscr": round(dscr, 2), "bps": 0})
            elif dscr >= rules.min_dscr - 0.15 if rules.min_dscr else dscr >= 1.05:
                adjustments.append({"reason": "thin_dscr", "dscr": round(dscr, 2), "bps": 75})
                rate += 0.75
            else:
                adjustments.append({"reason": "substandard_dscr", "dscr": round(dscr, 2), "bps": 150})
                rate += 1.50

        if metrics.debt_yield is not None:
            if metrics.debt_yield >= 0.12:
                adjustments.append({"reason": "strong_debt_yield", "debt_yield": round(metrics.debt_yield, 4), "bps": -10})
                rate -= 0.10
            elif metrics.debt_yield < 0.08:
                adjustments.append({"reason": "thin_debt_yield", "debt_yield": round(metrics.debt_yield, 4), "bps": 60})
                rate += 0.60

        effective_ltv = metrics.ltv if metrics.ltv is not None else ltv
        if effective_ltv and effective_ltv > 75:
            adjustments.append({"reason": "high_ltv", "ltv": round(effective_ltv, 1), "bps": 40})
            rate += 0.40

        if amount >= 2_000_000:
            adjustments.append({"reason": "large_balance", "loan_amount": amount, "bps": 30})
            rate += 0.30
        elif amount >= 1_000_000:
            adjustments.append({"reason": "above_average_balance", "loan_amount": amount, "bps": 15})
            rate += 0.15

        return rate

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
