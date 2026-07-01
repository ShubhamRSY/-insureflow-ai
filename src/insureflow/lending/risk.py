from insureflow.lending.models import (
    BusinessFinancialData,
    BusinessLoanApplication,
    ConsumerLoanApplication,
    CreditAnalysis,
)


class LendingRiskEngine:
    def analyze(
        self,
        application: BusinessLoanApplication | ConsumerLoanApplication,
    ) -> CreditAnalysis:
        if isinstance(application, BusinessLoanApplication):
            return self._analyze_business(application)
        return self._analyze_consumer(application)

    def _analyze_business(self, app: BusinessLoanApplication) -> CreditAnalysis:
        fin = app.financials[0] if app.financials else BusinessFinancialData()
        analysis = CreditAnalysis()
        analysis.overall_risk_score = 50.0
        ratios: list[str] = []

        if fin.current_liabilities > 0:
            current_ratio = fin.current_assets / fin.current_liabilities
            analysis.liquidity_ratio = current_ratio
            ratios.append(f"Current ratio {current_ratio:.2f}")
            if current_ratio < 1.0:
                analysis.overall_risk_score += 15
                analysis.weaknesses.append(f"Current ratio {current_ratio:.2f}x below 1.0x")
            elif current_ratio > 2.0:
                analysis.overall_risk_score -= 5
                analysis.strengths.append(f"Strong liquidity {current_ratio:.2f}x")

        if fin.total_liabilities > 0 and fin.total_assets > 0:
            leverage = (
                fin.total_liabilities / fin.shareholder_equity
                if fin.shareholder_equity > 0
                else 999
            )
            analysis.leverage_ratio = leverage
            ratios.append(f"Leverage {leverage:.2f}x")
            if leverage > 4.0:
                analysis.overall_risk_score += 15
                analysis.weaknesses.append(f"High leverage {leverage:.2f}x")
            elif leverage < 2.0:
                analysis.overall_risk_score -= 5
                analysis.strengths.append(f"Conservative leverage {leverage:.2f}x")

        if fin.debt_service > 0 and fin.ebitda > 0:
            dscr = fin.ebitda / fin.debt_service
            analysis.dscr = dscr
            ratios.append(f"DSCR {dscr:.2f}x")
            if dscr < 1.15:
                analysis.overall_risk_score += 20
                analysis.weaknesses.append(f"DSCR {dscr:.2f}x below 1.15x")
            elif dscr > 1.5:
                analysis.overall_risk_score -= 5
                analysis.strengths.append(f"Strong DSCR {dscr:.2f}x")

        if fin.annual_revenue > 0:
            margin = (fin.net_income / fin.annual_revenue) * 100
            analysis.profitability_score = margin
            ratios.append(f"Profit margin {margin:.1f}%")
            if margin < 5:
                analysis.overall_risk_score += 10
                analysis.weaknesses.append(f"Thin profit margin {margin:.1f}%")
            elif margin > 15:
                analysis.overall_risk_score -= 5
                analysis.strengths.append(f"Healthy margin {margin:.1f}%")

        years = app.years_in_business
        if years < 2:
            analysis.overall_risk_score += 10
            analysis.weaknesses.append(f"Business only {years:.0f} years old")
        elif years > 7:
            analysis.overall_risk_score -= 5
            analysis.strengths.append(f"Established business ({years:.0f} years)")

        industry = app.industry.lower() if app.industry else ""
        risky_industries = ["construction", "restaurant", "retail", "hospitality", "healthcare"]
        for ri in risky_industries:
            if ri in industry:
                analysis.overall_risk_score += 5
                analysis.industry_risk_score += 20
                analysis.weaknesses.append(f"Higher-risk industry: {app.industry}")

        if app.collateral:
            total_cv = sum(c.estimated_value for c in app.collateral)
            if app.requested_amount > 0:
                ltv = app.requested_amount / total_cv * 100
                analysis.loan_to_value = ltv
                ratios.append(f"LTV {ltv:.1f}%")
                if ltv <= 65:
                    analysis.overall_risk_score -= 10
                    analysis.strengths.append(f"Strong collateral position (LTV {ltv:.1f}%)")
                elif ltv > 80:
                    analysis.overall_risk_score += 10
                    analysis.weaknesses.append(f"High LTV {ltv:.1f}%")

        score = max(0, min(100, analysis.overall_risk_score))
        analysis.overall_risk_score = score

        if score < 30:
            analysis.risk_rating = "low"
            analysis.credit_score_tier = "A"
        elif score < 50:
            analysis.risk_rating = "moderate"
            analysis.credit_score_tier = "B"
        elif score < 70:
            analysis.risk_rating = "above_average"
            analysis.credit_score_tier = "C"
        else:
            analysis.risk_rating = "high"
            analysis.credit_score_tier = "D"

        analysis.conditions.extend(analysis.weaknesses)
        mitigation_suggestions = []
        if analysis.dscr < 1.15:
            mitigation_suggestions.append("Additional guarantor or cash injection to improve DSCR")
        if analysis.leverage_ratio > 4.0:
            mitigation_suggestions.append("Debt paydown or equity injection to reduce leverage")
        if analysis.loan_to_value > 80:
            mitigation_suggestions.append("Additional collateral pledged to lower LTV")
        analysis.mitigants = mitigation_suggestions

        return analysis

    def _analyze_consumer(self, app: ConsumerLoanApplication) -> CreditAnalysis:
        fin = app.financial_data
        analysis = CreditAnalysis()
        analysis.overall_risk_score = 50.0

        cs = fin.credit_score
        if cs > 0:
            if cs >= 760:
                analysis.credit_score_tier = "excellent"
                analysis.overall_risk_score -= 15
                analysis.strengths.append(f"Excellent credit score {cs}")
            elif cs >= 700:
                analysis.credit_score_tier = "good"
                analysis.overall_risk_score -= 5
                analysis.strengths.append(f"Good credit score {cs}")
            elif cs >= 660:
                analysis.credit_score_tier = "fair"
                analysis.weaknesses.append(f"Fair credit score {cs}")
            elif cs >= 620:
                analysis.credit_score_tier = "subprime"
                analysis.overall_risk_score += 10
                analysis.weaknesses.append(f"Subprime credit score {cs}")
            else:
                analysis.credit_score_tier = "poor"
                analysis.overall_risk_score += 20
                analysis.weaknesses.append(f"Poor credit score {cs}")
        else:
            analysis.credit_score_tier = "unknown"
            analysis.overall_risk_score += 10
            analysis.weaknesses.append("No credit score available")

        if fin.annual_income > 0:
            monthly_income = fin.annual_income / 12
            dti = fin.total_monthly_debt / monthly_income * 100 if monthly_income > 0 else 0
            analysis.debt_to_income_ratio = dti
            if dti > 43:
                analysis.overall_risk_score += 15
                analysis.weaknesses.append(f"DTI {dti:.1f}% exceeds 43%")
            elif dti < 36:
                analysis.overall_risk_score -= 5
                analysis.strengths.append(f"Low DTI {dti:.1f}%")
        else:
            analysis.overall_risk_score += 10
            analysis.weaknesses.append("No income verified")

        if fin.employment_years > 0:
            if fin.employment_years < 1:
                analysis.overall_risk_score += 10
                analysis.weaknesses.append("Less than 1 year at current employer")
            elif fin.employment_years > 5:
                analysis.overall_risk_score -= 5
                analysis.strengths.append(f"Stable employment ({fin.employment_years:.0f} years)")

        if fin.bankruptcies_last_7_years > 0:
            analysis.overall_risk_score += 25
            analysis.weaknesses.append(
                f"{fin.bankruptcies_last_7_years} bankruptcy(ies) in last 7 years"
            )

        if fin.foreclosures_last_7_years > 0:
            analysis.overall_risk_score += 20
            analysis.weaknesses.append(
                f"{fin.foreclosures_last_7_years} foreclosure(s) in last 7 years"
            )

        score = max(0, min(100, analysis.overall_risk_score))
        analysis.overall_risk_score = score

        if score < 30:
            analysis.risk_rating = "low"
        elif score < 50:
            analysis.risk_rating = "moderate"
        elif score < 70:
            analysis.risk_rating = "above_average"
        else:
            analysis.risk_rating = "high"

        analysis.conditions = analysis.weaknesses.copy()
        mitigation: list[str] = []
        if analysis.debt_to_income_ratio > 43:
            mitigation.append("Debt consolidation or co-borrower to reduce DTI")
        if fin.bankruptcies_last_7_years > 0 or fin.foreclosures_last_7_years > 0:
            mitigation.append("Credit exception letter explaining bankruptcy/foreclosure")
        if analysis.credit_score_tier in ("poor", "subprime"):
            mitigation.append("Higher rate or secured structure required for risk grade")
        analysis.mitigants = mitigation

        return analysis
