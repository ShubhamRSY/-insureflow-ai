from __future__ import annotations

from datetime import datetime, timezone

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.adapters.stub import StubPolicyAdminAdapter
from insureflow.rating.models import InsuranceLine, QuoteRequest, QuoteResult, RateComponent
from insureflow.underwriting.cope import COPERatingEngine
from insureflow.underwriting.market import get_market_cycle

# ISO-style base loss costs (per $100 of TIV) — representative values
# These would come from ISO/Verisk filings in production
ISO_LOSS_COSTS: dict[InsuranceLine, float] = {
    InsuranceLine.COMMERCIAL_PROPERTY: 0.28,
    InsuranceLine.GENERAL_LIABILITY: 0.08,
    InsuranceLine.WORKERS_COMP: 0.05,
    InsuranceLine.BOP: 0.32,
    InsuranceLine.UMBRELLA: 0.03,
}

# Loss Cost Multipliers (LCM) — carrier's expense + profit loading
# Realistic for small carrier: 2.0-2.5x
LCM: dict[InsuranceLine, float] = {
    InsuranceLine.COMMERCIAL_PROPERTY: 2.10,
    InsuranceLine.GENERAL_LIABILITY: 2.25,
    InsuranceLine.WORKERS_COMP: 2.40,
    InsuranceLine.BOP: 2.00,
    InsuranceLine.UMBRELLA: 2.50,
}

# Territory relativities by state (1.0 = national average)
TERRITORY_RELATIVITIES: dict[str, dict[InsuranceLine, float]] = {
    "TX": {
        InsuranceLine.COMMERCIAL_PROPERTY: 1.15,
        InsuranceLine.GENERAL_LIABILITY: 1.05,
        InsuranceLine.WORKERS_COMP: 0.95,
        InsuranceLine.BOP: 1.10,
        InsuranceLine.UMBRELLA: 1.05,
    },
    "FL": {
        InsuranceLine.COMMERCIAL_PROPERTY: 1.60,
        InsuranceLine.GENERAL_LIABILITY: 1.10,
        InsuranceLine.WORKERS_COMP: 1.00,
        InsuranceLine.BOP: 1.45,
        InsuranceLine.UMBRELLA: 1.10,
    },
    "CA": {
        InsuranceLine.COMMERCIAL_PROPERTY: 1.30,
        InsuranceLine.GENERAL_LIABILITY: 1.20,
        InsuranceLine.WORKERS_COMP: 1.15,
        InsuranceLine.BOP: 1.20,
        InsuranceLine.UMBRELLA: 1.15,
    },
    "NY": {
        InsuranceLine.COMMERCIAL_PROPERTY: 1.20,
        InsuranceLine.GENERAL_LIABILITY: 1.25,
        InsuranceLine.WORKERS_COMP: 1.10,
        InsuranceLine.BOP: 1.15,
        InsuranceLine.UMBRELLA: 1.20,
    },
    "LA": {
        InsuranceLine.COMMERCIAL_PROPERTY: 1.55,
        InsuranceLine.GENERAL_LIABILITY: 1.08,
        InsuranceLine.WORKERS_COMP: 0.98,
        InsuranceLine.BOP: 1.40,
        InsuranceLine.UMBRELLA: 1.08,
    },
    "IL": {
        InsuranceLine.COMMERCIAL_PROPERTY: 1.05,
        InsuranceLine.GENERAL_LIABILITY: 1.08,
        InsuranceLine.WORKERS_COMP: 0.92,
        InsuranceLine.BOP: 1.05,
        InsuranceLine.UMBRELLA: 1.05,
    },
    "GA": {
        InsuranceLine.COMMERCIAL_PROPERTY: 1.10,
        InsuranceLine.GENERAL_LIABILITY: 1.02,
        InsuranceLine.WORKERS_COMP: 0.90,
        InsuranceLine.BOP: 1.05,
        InsuranceLine.UMBRELLA: 1.02,
    },
}

# Minimum premium by line
MINIMUM_PREMIUMS: dict[InsuranceLine, float] = {
    InsuranceLine.COMMERCIAL_PROPERTY: 500.0,
    InsuranceLine.GENERAL_LIABILITY: 750.0,
    InsuranceLine.WORKERS_COMP: 1_000.0,
    InsuranceLine.BOP: 1_500.0,
    InsuranceLine.UMBRELLA: 1_000.0,
}

# Deductible credit factors
DEDUCTIBLE_CREDITS: dict[tuple[float, float], float] = {
    (0, 999): 0.0,
    (1_000, 2_500): -5.0,
    (2_500, 5_000): -10.0,
    (5_000, 10_000): -15.0,
    (10_000, 25_000): -20.0,
    (25_000, float("inf")): -25.0,
}

# Years-in-business premium modifiers (generic tiers for any business)
# < 2 years = startup risk, 2-5 = still green, 5-10 = established, 10+ = mature
YEARS_IN_BUSINESS_MODIFIERS: list[tuple[int | None, int | None, float]] = [
    (None, 2, 10.0),  # < 2 years → +10% surcharge
    (2, 5, 0.0),  # 2-5 years → no adjustment
    (5, 10, -5.0),  # 5-10 years → -5% credit
    (10, None, -10.0),  # 10+ years → -10% credit
]

# Loss experience modifiers (multi-tier for any claims history)
LOSS_EXPERIENCE_MODIFIERS: list[tuple[float | None, float | None, float]] = [
    (None, 0.10, -10.0),  # LR < 10% → -10% credit
    (0.10, 0.20, -5.0),  # LR 10-20% → -5% credit
    (0.20, 0.30, 0.0),  # LR 20-30% → no adjustment
    (0.30, 0.50, 5.0),  # LR 30-50% → +5% surcharge
    (0.50, 0.75, 10.0),  # LR 50-75% → +10% surcharge
    (0.75, None, 20.0),  # LR 75%+ → +20% surcharge
]


class InsuranceRatingEngine:
    """ISO-style commercial P&C rating with COPE schedule rating and market cycle adjustments.

    Rating formula:
      base_premium = (TIV / 100) * iso_loss_cost * lcm * territory_relativity
      adjusted_premium = base_premium * (1 + cope_schedule_mod/100) * (1 + market_cycle_mod/100)
                        * (1 + deductible_credit/100) * (1 + loss_exp_mod/100) * (1 + years_mod/100)
                        + expense_constant

    Where:
      - iso_loss_cost = ISO base loss cost (per $100 TIV, from industry data)
      - lcm = Loss Cost Multiplier (carrier-specific expense + profit loading)
      - territory_relativity = state-specific adjustment
      - cope_schedule_mod = combined C-O-P-E modifiers (construction, occupancy, protection, exposure)
      - market_cycle_mod = hard/soft market adjustment
      - deductible_credit = credit for higher deductibles
      - loss_exp_mod = multi-tier loss experience modifier based on loss ratio
      - years_mod = tenure-based modifier (startup surcharge, mature credit)
    """

    EXPENSE_CONSTANT: float = 75.0  # Flat policy fee

    def __init__(self, adapter: StubPolicyAdminAdapter | None = None) -> None:
        self.adapter = adapter or StubPolicyAdminAdapter()
        self._cope = COPERatingEngine()
        self._market = get_market_cycle()

    def quote(
        self,
        bundle: SubmissionBundle,
        memo: UnderwritingMemo,
        line: InsuranceLine = InsuranceLine.COMMERCIAL_PROPERTY,
    ) -> QuoteResult:
        tiv = self._estimate_tiv(bundle)
        state = self._primary_state(bundle)

        # COPE analysis
        cope_result = self._cope.analyze(bundle)
        cope_mod = cope_result.score.schedule_mod_pct

        # ISO-style base rate
        iso_cost = ISO_LOSS_COSTS.get(line, 0.30)
        lcm = LCM.get(line, 2.0)
        territory_rel = TERRITORY_RELATIVITIES.get(state, {}).get(line, 1.0)

        base_premium = (tiv / 100.0) * iso_cost * lcm * territory_rel

        # Market cycle adjustment
        market_cycle_mod = self._get_market_mod(line)
        market_adjusted = base_premium * (1 + market_cycle_mod / 100.0)

        # COPE schedule rating
        cope_adjusted = market_adjusted * (1 + cope_mod / 100.0)

        # UW memo schedule modification (from agent findings)
        schedule_mod = memo.recommendation.suggested_premium_modification if memo.recommendation else 0.0
        schedule_mod = schedule_mod or 0.0

        # Deductible credit
        deductible = self._estimate_deductible(bundle)
        deductible_credit = 0.0
        for (lo, hi), cr in DEDUCTIBLE_CREDITS.items():
            if lo <= deductible < hi:
                deductible_credit = cr
                break

        # Loss experience mod (multi-tier)
        loss_ratio = self._loss_ratio(bundle)
        exp_mod = 0.0
        for lo, hi, mod in LOSS_EXPERIENCE_MODIFIERS:
            if (lo is None or loss_ratio >= lo) and (hi is None or loss_ratio < hi):
                exp_mod = mod
                break

        # Years-in-business modifier (generic tiers)
        years_mod = self._years_in_business_mod(bundle)

        # Final premium
        adjusted_premium = cope_adjusted * (1 + schedule_mod / 100.0) * (1 + deductible_credit / 100.0) * (1 + exp_mod / 100.0) * (1 + years_mod / 100.0)
        adjusted_premium += self.EXPENSE_CONSTANT

        # Minimum premium
        min_prem = MINIMUM_PREMIUMS.get(line, 500.0)
        adjusted_premium = max(adjusted_premium, min_prem)
        adjusted_premium = round(adjusted_premium, 2)

        # Build rate components
        components: list[RateComponent] = [
            RateComponent(
                name="iso_base_loss_cost",
                amount=round(iso_cost, 4),
                basis="per_100_tiv",
                modifier_pct=0.0,
            ),
            RateComponent(name="loss_cost_multiplier", amount=lcm, basis="expense_profit", modifier_pct=0.0),
            RateComponent(
                name=f"territory_relativity_{state}",
                amount=territory_rel,
                basis="state",
                modifier_pct=0.0,
            ),
            RateComponent(
                name="cope_schedule_rating",
                amount=round(cope_mod, 1),
                basis="schedule",
                modifier_pct=cope_mod,
            ),
            RateComponent(
                name="market_cycle_adjustment",
                amount=round(market_cycle_mod, 1),
                basis="market",
                modifier_pct=market_cycle_mod,
            ),
        ]
        if deductible_credit != 0:
            components.append(
                RateComponent(
                    name="deductible_credit",
                    amount=deductible,
                    basis="deductible",
                    modifier_pct=deductible_credit,
                )
            )
        if exp_mod != 0:
            components.append(
                RateComponent(
                    name="loss_experience",
                    amount=round(loss_ratio, 4),
                    basis="loss_ratio",
                    modifier_pct=exp_mod,
                )
            )
        if years_mod != 0:
            components.append(RateComponent(name="years_in_business", amount=0, basis="tenure", modifier_pct=years_mod))
        if schedule_mod != 0:
            components.append(
                RateComponent(
                    name="uw_schedule_modification",
                    amount=0,
                    basis="uw_discretion",
                    modifier_pct=schedule_mod,
                )
            )

        result = self.adapter.submit_quote(
            QuoteRequest(
                bundle_id=bundle.bundle_id,
                line=line,
                tiv=tiv,
                state=state,
                naics_code=self._naics(bundle),
                loss_ratio=loss_ratio,
                schedule_mod_pct=cope_mod + schedule_mod + exp_mod + deductible_credit,
            ),
            memo,
            bundle,
        )
        result.base_premium = round(base_premium, 2)
        result.adjusted_premium = adjusted_premium
        result.schedule_modifications = components
        result.rate_per_100_tiv = round(adjusted_premium / (tiv / 100.0), 4) if tiv > 0 else 0.0

        # Attach COPE and market data
        result.metadata = {
            "cope_grade": cope_result.score.risk_grade.value,
            "cope_score": cope_result.score.total_score,
            "cope_mod_pct": cope_mod,
            "market_phase": self._market.current.phase.value,
            "market_mod_pct": market_cycle_mod,
            "territory_relativity": territory_rel,
            "loss_cost": iso_cost * lcm,
            "deductible_credit": deductible_credit,
            "expense_constant": self.EXPENSE_CONSTANT,
            "years_in_business_mod_pct": years_mod,
            "loss_experience_mod_pct": exp_mod,
        }

        return result

    def bind(self, bundle_id: str, quote_reference: str, bound_by: str) -> dict:
        return self.adapter.bind_policy(bundle_id, quote_reference, bound_by)

    def _estimate_tiv(self, bundle: SubmissionBundle) -> float:
        if bundle.structured:
            for loc in bundle.structured.locations:
                total = (loc.building_value or 0) + (loc.contents_value or 0) + (loc.bi_value or 0)
                if total > 0:
                    return total
            if bundle.structured.financial and bundle.structured.financial.total_asset_value:
                return bundle.structured.financial.total_asset_value
            for cov in bundle.structured.coverages:
                if cov.limit_amount > 0:
                    return cov.limit_amount
        for doc in bundle.unstructured:
            for fields in doc.extracted_fields.get("tiv", []):
                try:
                    return float(fields.value.replace(",", ""))
                except ValueError:
                    pass
        return 1_000_000.0

    def _loss_ratio(self, bundle: SubmissionBundle) -> float:
        fin = bundle.structured.financial if bundle.structured else None
        if fin and fin.loss_run and fin.loss_run.loss_ratios:
            return max(fin.loss_run.loss_ratios.values(), default=0.0)
        if fin and fin.loss_run and fin.loss_run.total_incurred > 0:
            premium_proxy = self._estimate_tiv(bundle) * 0.0045
            return fin.loss_run.total_incurred / premium_proxy if premium_proxy else 0.0
        return 0.0

    def _primary_state(self, bundle: SubmissionBundle) -> str:
        if bundle.structured and bundle.structured.locations:
            return bundle.structured.locations[0].state or ""
        return ""

    def _naics(self, bundle: SubmissionBundle) -> str:
        if bundle.structured and bundle.structured.risk_profile:
            return bundle.structured.risk_profile.naics_code or ""
        return ""

    def _estimate_deductible(self, bundle: SubmissionBundle) -> float:
        deductible = 1_000.0  # default
        if bundle.structured:
            for cov in bundle.structured.coverages:
                if cov.deductible > 0:
                    return cov.deductible
        for doc in bundle.unstructured:
            for fields in doc.extracted_fields.get("deductible", []):
                try:
                    return float(fields.value.replace(",", ""))
                except ValueError:
                    pass
        return deductible

    def _years_in_business_mod(self, bundle: SubmissionBundle) -> float:
        years = 0
        for doc in bundle.unstructured:
            for field in doc.extracted_fields.get("year_founded", []):
                try:
                    years = datetime.now(tz=timezone.utc).year - int(field.value)
                except (ValueError, TypeError):
                    pass
        if bundle.structured and bundle.structured.financial and bundle.structured.financial.annual_revenue:
            pass  # annual_revenue is a separate signal, not years
        for lo, hi, mod in YEARS_IN_BUSINESS_MODIFIERS:
            if (lo is None or years >= lo) and (hi is None or years < hi):
                return mod
        return 0.0

    def _get_market_mod(self, line: InsuranceLine) -> float:
        cycle = self._market.current
        if line == InsuranceLine.COMMERCIAL_PROPERTY:
            return (cycle.property_rate_mod - 1.0) * 100.0
        elif line == InsuranceLine.GENERAL_LIABILITY:
            return (cycle.liability_rate_mod - 1.0) * 100.0
        elif line == InsuranceLine.WORKERS_COMP:
            return (cycle.workers_comp_rate_mod - 1.0) * 100.0
        elif line == InsuranceLine.UMBRELLA:
            return (cycle.liability_rate_mod - 1.0) * 100.0
        return (cycle.auto_rate_mod - 1.0) * 100.0
