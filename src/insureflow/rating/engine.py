from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.calibration import calibrated_lcm, calibrated_loss_costs, calibrated_territory, load_rate_curves
from insureflow.rating.models import COMMERCIAL_SPECIALTY_LINES, PERSONAL_LINES, InsuranceLine, QuoteRequest, QuoteResult, RateComponent, RatingAdapter
from insureflow.underwriting.cope import COPERatingEngine
from insureflow.underwriting.market import get_market_cycle

# ISO-style base loss costs (per $100 of TIV) — representative values
# Overridden by data/rate_curves.json or RATE_CURVES_URL when present
ISO_LOSS_COSTS: dict[InsuranceLine, float] = {
    InsuranceLine.COMMERCIAL_PROPERTY: 0.28,
    InsuranceLine.GENERAL_LIABILITY: 0.08,
    InsuranceLine.WORKERS_COMP: 0.05,
    InsuranceLine.BOP: 0.32,
    InsuranceLine.COMMERCIAL_PACKAGE: 0.30,
    InsuranceLine.UMBRELLA: 0.03,
    InsuranceLine.DIRECTORS_AND_OFFICERS: 0.45,
    InsuranceLine.TRADE_CREDIT: 0.22,
    InsuranceLine.ERRORS_AND_OMISSIONS: 0.55,
    InsuranceLine.KEY_PERSON: 0.12,
    InsuranceLine.CYBER: 0.85,
    InsuranceLine.COMMERCIAL_AUTO: 0.40,
    InsuranceLine.INLAND_MARINE: 0.55,
    InsuranceLine.CRIME: 0.18,
    InsuranceLine.BUILDERS_RISK: 0.42,
    InsuranceLine.SURETY: 0.15,
    # Personal lines — representative synthetic rates (per $100 exposure)
    InsuranceLine.PERSONAL_HOMEOWNERS: 0.35,
    InsuranceLine.PERSONAL_AUTO: 1.20,
    InsuranceLine.LIFE: 0.08,
}

# Loss Cost Multipliers (LCM) — carrier's expense + profit loading
# Realistic for small carrier: 2.0-2.5x
LCM: dict[InsuranceLine, float] = {
    InsuranceLine.COMMERCIAL_PROPERTY: 2.10,
    InsuranceLine.GENERAL_LIABILITY: 2.25,
    InsuranceLine.WORKERS_COMP: 2.40,
    InsuranceLine.BOP: 2.00,
    InsuranceLine.COMMERCIAL_PACKAGE: 2.05,
    InsuranceLine.UMBRELLA: 2.50,
    InsuranceLine.DIRECTORS_AND_OFFICERS: 2.35,
    InsuranceLine.TRADE_CREDIT: 2.15,
    InsuranceLine.ERRORS_AND_OMISSIONS: 2.40,
    InsuranceLine.KEY_PERSON: 1.70,
    InsuranceLine.CYBER: 2.20,
    InsuranceLine.COMMERCIAL_AUTO: 2.15,
    InsuranceLine.INLAND_MARINE: 2.00,
    InsuranceLine.CRIME: 2.15,
    InsuranceLine.BUILDERS_RISK: 2.05,
    InsuranceLine.SURETY: 1.80,
    InsuranceLine.PERSONAL_HOMEOWNERS: 1.85,
    InsuranceLine.PERSONAL_AUTO: 1.95,
    InsuranceLine.LIFE: 1.60,
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
    InsuranceLine.COMMERCIAL_PACKAGE: 2_500.0,
    InsuranceLine.UMBRELLA: 1_000.0,
    InsuranceLine.DIRECTORS_AND_OFFICERS: 2_500.0,
    InsuranceLine.TRADE_CREDIT: 1_500.0,
    InsuranceLine.ERRORS_AND_OMISSIONS: 2_000.0,
    InsuranceLine.KEY_PERSON: 500.0,
    InsuranceLine.CYBER: 2_500.0,
    InsuranceLine.COMMERCIAL_AUTO: 1_200.0,
    InsuranceLine.INLAND_MARINE: 750.0,
    InsuranceLine.CRIME: 500.0,
    InsuranceLine.BUILDERS_RISK: 1_000.0,
    InsuranceLine.SURETY: 250.0,
    InsuranceLine.PERSONAL_HOMEOWNERS: 450.0,
    InsuranceLine.PERSONAL_AUTO: 650.0,
    InsuranceLine.LIFE: 250.0,
}

# Territory defaults for personal lines (merged into each state below)
_PERSONAL_TERRITORY = {
    InsuranceLine.PERSONAL_HOMEOWNERS: 1.10,
    InsuranceLine.PERSONAL_AUTO: 1.05,
    InsuranceLine.LIFE: 1.00,
}

for _state, _rels in TERRITORY_RELATIVITIES.items():
    for _line, _rel in _PERSONAL_TERRITORY.items():
        _rels.setdefault(_line, _rel)
# FL/CA/LA homeowners CAT load
for _state, _bump in (("FL", 1.55), ("LA", 1.45), ("CA", 1.35)):
    if _state in TERRITORY_RELATIVITIES:
        TERRITORY_RELATIVITIES[_state][InsuranceLine.PERSONAL_HOMEOWNERS] = _bump
for _state, _bump in (("FL", 1.25), ("NY", 1.20), ("CA", 1.30)):
    if _state in TERRITORY_RELATIVITIES:
        TERRITORY_RELATIVITIES[_state][InsuranceLine.PERSONAL_AUTO] = _bump


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

    def __init__(self, adapter: RatingAdapter | None = None) -> None:
        if adapter is None:
            from insureflow.rating.adapters.iso_adapter import ISORatingAdapter

            adapter = ISORatingAdapter()
        self.adapter = adapter
        self._cope = COPERatingEngine()
        self._market = get_market_cycle()

    def quote(
        self,
        bundle: SubmissionBundle,
        memo: UnderwritingMemo,
        line: InsuranceLine = InsuranceLine.COMMERCIAL_PROPERTY,
        commercial_product_id: str | None = None,
    ) -> QuoteResult:
        personal = line in PERSONAL_LINES
        if personal:
            from insureflow.rating.personal import rate_personal_line
            from insureflow.underwriting.personal_lines import _blob, _state_from_blob

            state = self._primary_state(bundle) or _state_from_blob(_blob(bundle))
            deductible = 0.0 if line == InsuranceLine.LIFE else self._estimate_deductible(bundle)
            if deductible <= 0 and line == InsuranceLine.PERSONAL_HOMEOWNERS:
                deductible = 1000.0
            result = rate_personal_line(bundle, line, state=state, deductible=deductible)
            # Preserve adapter reference fields
            adapted = self.adapter.submit_quote(
                QuoteRequest(
                    bundle_id=bundle.bundle_id,
                    line=line,
                    tiv=float((result.metadata or {}).get("tiv") or 0),
                    state=state,
                    naics_code="",
                    loss_ratio=0.0,
                    schedule_mod_pct=0.0,
                ),
                memo,
                bundle,
            )
            adapted.base_premium = result.base_premium
            adapted.adjusted_premium = result.adjusted_premium
            adapted.schedule_modifications = result.schedule_modifications
            adapted.rate_per_100_tiv = result.rate_per_100_tiv
            adapted.eligible = result.eligible
            adapted.ineligibility_reasons = list(result.ineligibility_reasons or [])
            meta = dict(result.metadata or {})
            meta["market_phase"] = self._market.current.phase.value
            meta["market_mod_pct"] = self._get_market_mod(line)
            adapted.metadata = meta
            return self._finalize_quote(adapted)

        if line in COMMERCIAL_SPECIALTY_LINES:
            from insureflow.rating.commercial_specialty import rate_specialty_line

            state = self._primary_state(bundle)
            schedule_mod = memo.recommendation.suggested_premium_modification if memo.recommendation else 0.0
            schedule_mod = schedule_mod or 0.0
            market_mod = self._get_market_mod(line)
            result = rate_specialty_line(
                bundle,
                line,
                state=state,
                schedule_mod_pct=float(schedule_mod),
                market_mod_pct=market_mod,
            )
            adapted = self.adapter.submit_quote(
                QuoteRequest(
                    bundle_id=bundle.bundle_id,
                    line=line,
                    tiv=float((result.metadata or {}).get("exposure") or 0),
                    state=state,
                    naics_code=self._naics(bundle),
                    loss_ratio=self._loss_ratio(bundle),
                    schedule_mod_pct=float(schedule_mod),
                ),
                memo,
                bundle,
            )
            adapted.base_premium = result.base_premium
            adapted.adjusted_premium = result.adjusted_premium
            adapted.schedule_modifications = result.schedule_modifications
            adapted.rate_per_100_tiv = result.rate_per_100_tiv
            adapted.eligible = result.eligible
            adapted.ineligibility_reasons = list(result.ineligibility_reasons or [])
            meta = dict(result.metadata or {})
            meta["market_phase"] = self._market.current.phase.value
            meta["market_mod_pct"] = market_mod
            adapted.metadata = meta
            return self._finalize_quote(adapted)

        # Extended actuarial manuals + NCCI WC + multi-section packages
        from insureflow.rating.commercial_actuarial import (
            is_extended_commercial,
            is_package_line,
            rate_extended_commercial,
            rate_package_policy,
            rate_workers_comp_ncci,
        )
        from insureflow.rating.models import PACKAGE_LINES

        state = self._primary_state(bundle)
        schedule_mod = memo.recommendation.suggested_premium_modification if memo.recommendation else 0.0
        schedule_mod = float(schedule_mod or 0.0)
        market_mod = self._get_market_mod(line)

        # Customer SERFF book wins over hardcoded WC / cyber / auto / package tables.
        from insureflow.rating.leaf_filings import rate_leaf_filing, should_use_leaf_filing

        leaf_product = commercial_product_id or (line.value if line else "")
        if should_use_leaf_filing(leaf_product, line):
            leaf = rate_leaf_filing(
                bundle,
                memo,
                leaf_product,
                state=state,
                schedule_mod_pct=schedule_mod,
                market_mod_pct=market_mod,
            )
            if leaf is not None:
                return self._adapt_actuarial_result(leaf, memo, bundle, schedule_mod)

        if line == InsuranceLine.WORKERS_COMP:
            result = rate_workers_comp_ncci(bundle, memo, state=state, schedule_mod_pct=schedule_mod, market_mod_pct=market_mod)
            return self._adapt_actuarial_result(result, memo, bundle, schedule_mod)

        if is_package_line(line) or line in PACKAGE_LINES:
            result = rate_package_policy(bundle, memo, line, state=state, schedule_mod_pct=schedule_mod, market_mod_pct=market_mod)
            return self._adapt_actuarial_result(result, memo, bundle, schedule_mod)

        if is_extended_commercial(line):
            extended = rate_extended_commercial(bundle, memo, line, state=state, schedule_mod_pct=schedule_mod, market_mod_pct=market_mod)
            if extended is not None:
                return self._adapt_actuarial_result(extended, memo, bundle, schedule_mod)

        personal_meta: dict[str, Any] = {}
        tiv = self._estimate_tiv(bundle)
        cope_result = self._cope.analyze(bundle)
        cope_mod = cope_result.score.schedule_mod_pct

        state = self._primary_state(bundle)
        tiv_unknown = tiv <= 0

        curves = load_rate_curves()
        loss_costs = calibrated_loss_costs(ISO_LOSS_COSTS)
        lcms = calibrated_lcm(LCM)
        territories = calibrated_territory(TERRITORY_RELATIVITIES)
        iso_cost = loss_costs.get(line, 0.30)
        lcm = lcms.get(line, 2.0)
        territory_rel = territories.get(state, {}).get(line, 1.0)
        if not isinstance(territory_rel, (int, float)):
            territory_rel = 1.0

        base_premium = (tiv / 100.0) * iso_cost * lcm * territory_rel if not tiv_unknown else 0.0

        market_cycle_mod = self._get_market_mod(line)
        market_adjusted = base_premium * (1 + market_cycle_mod / 100.0)
        cope_adjusted = market_adjusted * (1 + cope_mod / 100.0)

        schedule_mod = memo.recommendation.suggested_premium_modification if memo.recommendation else 0.0
        schedule_mod = schedule_mod or 0.0

        deductible = 0.0 if line == InsuranceLine.LIFE else self._estimate_deductible(bundle)
        deductible_credit = 0.0
        if line != InsuranceLine.LIFE:
            for (lo, hi), cr in DEDUCTIBLE_CREDITS.items():
                if lo <= deductible < hi:
                    deductible_credit = cr
                    break

        loss_ratio = self._loss_ratio(bundle)
        exp_mod = 0.0
        for lo_, hi_, mod in LOSS_EXPERIENCE_MODIFIERS:
            if (lo_ is None or loss_ratio >= lo_) and (hi_ is None or loss_ratio < hi_):
                exp_mod = mod
                break

        years_mod = 0.0 if personal else self._years_in_business_mod(bundle)

        if tiv_unknown:
            adjusted_premium = 0.0
        else:
            adjusted_premium = cope_adjusted * (1 + schedule_mod / 100.0) * (1 + deductible_credit / 100.0) * (1 + exp_mod / 100.0) * (1 + years_mod / 100.0)
            adjusted_premium += self.EXPENSE_CONSTANT
            min_prem = MINIMUM_PREMIUMS.get(line, 500.0)
            adjusted_premium = max(adjusted_premium, min_prem)
            adjusted_premium = round(adjusted_premium, 2)

        schedule_label = "personal_schedule_rating" if personal else "cope_schedule_rating"
        components: list[RateComponent] = [
            RateComponent(name="iso_base_loss_cost", amount=round(iso_cost, 4), basis="per_100_tiv", modifier_pct=0.0),
            RateComponent(name="loss_cost_multiplier", amount=lcm, basis="expense_profit", modifier_pct=0.0),
            RateComponent(name=f"territory_relativity_{state}", amount=territory_rel, basis="state", modifier_pct=0.0),
            RateComponent(name=schedule_label, amount=round(cope_mod, 1), basis="schedule", modifier_pct=cope_mod),
            RateComponent(name="market_cycle_adjustment", amount=round(market_cycle_mod, 1), basis="market", modifier_pct=market_cycle_mod),
        ]
        if deductible_credit != 0:
            components.append(RateComponent(name="deductible_credit", amount=deductible, basis="deductible", modifier_pct=deductible_credit))
        if exp_mod != 0:
            components.append(RateComponent(name="loss_experience", amount=round(loss_ratio, 4), basis="loss_ratio", modifier_pct=exp_mod))
        if years_mod != 0:
            components.append(RateComponent(name="years_in_business", amount=0, basis="tenure", modifier_pct=years_mod))
        if schedule_mod != 0:
            components.append(RateComponent(name="uw_schedule_modification", amount=0, basis="uw_discretion", modifier_pct=schedule_mod))

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
        if tiv_unknown:
            result.eligible = False
            if "TIV could not be determined" not in result.ineligibility_reasons:
                result.ineligibility_reasons.append("TIV could not be determined")

        result.metadata = {
            "cope_grade": cope_result.score.risk_grade.value if cope_result is not None else "personal",
            "cope_score": cope_result.score.total_score if cope_result is not None else None,
            "cope_mod_pct": cope_mod,
            "market_phase": self._market.current.phase.value,
            "market_mod_pct": market_cycle_mod,
            "territory_relativity": territory_rel,
            "loss_cost": iso_cost * lcm,
            "deductible_credit": deductible_credit,
            "expense_constant": self.EXPENSE_CONSTANT if not tiv_unknown else 0.0,
            "years_in_business_mod_pct": years_mod,
            "loss_experience_mod_pct": exp_mod,
            "tiv_unknown": tiv_unknown,
            "tiv": tiv,
            "insurance_line": line.value,
            "personal_lines": personal,
            "rate_curve_source": curves.get("source", "builtin"),
            "rate_curve_synthetic": bool(curves.get("synthetic", True)),
        }
        if personal_meta:
            result.metadata["personal_factors"] = {k: v for k, v in personal_meta.items() if k != "findings"}

        return self._finalize_quote(result)

    def bind(self, bundle_id: str, quote_reference: str, bound_by: str) -> dict[str, Any]:
        return self.adapter.bind_policy(bundle_id, quote_reference, bound_by)

    def _finalize_quote(self, result: QuoteResult) -> QuoteResult:
        """Desk+ refuses pilot manuals — rating must be the carrier's SERFF book."""
        from insureflow.billing.plan import current_plan, is_customer_rate_book
        from insureflow.rating.leaf_filings import carrier_book_status

        plan = current_plan()
        status = carrier_book_status()
        meta = dict(result.metadata or {})
        meta["plan_id"] = plan.plan_id
        meta["rate_book_posture"] = status.get("posture")
        meta["rate_book_id"] = status.get("book_id")
        meta["is_customer_book"] = is_customer_rate_book(status)
        if plan.require_carrier_book and not is_customer_rate_book(status):
            result.eligible = False
            reason = (
                "Pilot manuals are not your SERFF filing. Import your carrier rate book "
                "before Desk+ quoting (POST /rating/carrier-book or CARRIER_BOOK_PATH)."
            )
            if reason not in result.ineligibility_reasons:
                result.ineligibility_reasons.append(reason)
            meta["rate_book_gate"] = "blocked_demo_book"
        else:
            meta["rate_book_gate"] = "ok"
        result.metadata = meta
        return result

    def _adapt_actuarial_result(
        self,
        result: QuoteResult,
        memo: UnderwritingMemo,
        bundle: SubmissionBundle,
        schedule_mod: float,
    ) -> QuoteResult:
        adapted = self.adapter.submit_quote(
            QuoteRequest(
                bundle_id=bundle.bundle_id,
                line=result.line,
                tiv=float((result.metadata or {}).get("exposure") or (result.metadata or {}).get("payroll") or (result.metadata or {}).get("tiv") or 0),
                state=str((result.metadata or {}).get("state") or self._primary_state(bundle)),
                naics_code=self._naics(bundle),
                loss_ratio=self._loss_ratio(bundle),
                schedule_mod_pct=float(schedule_mod),
            ),
            memo,
            bundle,
        )
        adapted.base_premium = result.base_premium
        adapted.adjusted_premium = result.adjusted_premium
        adapted.schedule_modifications = result.schedule_modifications
        adapted.rate_per_100_tiv = result.rate_per_100_tiv
        adapted.eligible = result.eligible
        adapted.ineligibility_reasons = list(result.ineligibility_reasons or [])
        meta = dict(result.metadata or {})
        meta["market_phase"] = self._market.current.phase.value
        adapted.metadata = meta
        return self._finalize_quote(adapted)

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
        return 0.0

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
        elif line in (
            InsuranceLine.DIRECTORS_AND_OFFICERS,
            InsuranceLine.ERRORS_AND_OMISSIONS,
            InsuranceLine.TRADE_CREDIT,
        ):
            return (cycle.liability_rate_mod - 1.0) * 100.0
        elif line == InsuranceLine.KEY_PERSON:
            return 0.0
        elif line == InsuranceLine.PERSONAL_HOMEOWNERS:
            return (cycle.property_rate_mod - 1.0) * 100.0
        elif line == InsuranceLine.PERSONAL_AUTO:
            return (cycle.auto_rate_mod - 1.0) * 100.0
        elif line == InsuranceLine.LIFE:
            return 0.0
        return (cycle.auto_rate_mod - 1.0) * 100.0
