from dataclasses import dataclass

from insureflow.lending.models import (
    CreditAnalysis,
    LoanProductType,
)


@dataclass
class LendingPrice:
    base_rate: float
    risk_spread: float
    term_spread: float
    final_rate: float
    upfront_fee_percent: float
    annual_fee_percent: float


class LendingPricingEngine:
    BASE_RATES: dict[LoanProductType, float] = {
        LoanProductType.BUSINESS_TERM_LOAN: 6.0,
        LoanProductType.BUSINESS_LINE_OF_CREDIT: 5.5,
        LoanProductType.COMMERCIAL_REAL_ESTATE: 5.75,
        LoanProductType.CONSTRUCTION_LOAN: 6.5,
        LoanProductType.SBA_7A: 7.0,
        LoanProductType.SBA_504: 6.5,
        LoanProductType.EQUIPMENT_FINANCING: 6.25,
        LoanProductType.INVOICE_FINANCING: 8.0,
        LoanProductType.PERSONAL_TERM_LOAN: 8.0,
        LoanProductType.PERSONAL_LINE_OF_CREDIT: 9.0,
        LoanProductType.AUTO_LOAN: 6.5,
        LoanProductType.BOAT_LOAN: 7.0,
        LoanProductType.HOME_EQUITY_LOAN: 6.0,
        LoanProductType.HOME_EQUITY_LINE: 5.5,
        LoanProductType.SECURED_PERSONAL: 7.0,
        LoanProductType.UNSECURED_PERSONAL: 10.0,
    }

    RISK_SPREADS: dict[str, float] = {
        "low": -0.50,
        "moderate": 0.0,
        "above_average": 1.50,
        "high": 3.50,
    }

    TERM_SPREAD_MONTHLY: float = 0.008

    def price(
        self,
        product_type: LoanProductType,
        risk_analysis: CreditAnalysis,
        requested_term_months: int,
    ) -> LendingPrice:
        base = self.BASE_RATES.get(product_type, 8.0)
        risk_spread = self.RISK_SPREADS.get(risk_analysis.risk_rating, 1.0)
        term_spread = max(0.0, (requested_term_months - 12) * self.TERM_SPREAD_MONTHLY)
        final_rate = base + risk_spread + term_spread
        return LendingPrice(
            base_rate=base,
            risk_spread=risk_spread,
            term_spread=term_spread,
            final_rate=round(final_rate, 2),
            upfront_fee_percent=(0.5 if risk_analysis.risk_rating == "high" else 0.0),
            annual_fee_percent=(
                0.25 if product_type == LoanProductType.BUSINESS_LINE_OF_CREDIT else 0.0
            ),
        )
