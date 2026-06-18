from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from insureflow.models.agents import UnderwritingMemo, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.adapters.stub import StubPolicyAdminAdapter
from insureflow.rating.models import InsuranceLine, QuoteRequest, QuoteResult, RateComponent


class InsuranceRatingEngine:
    """Commercial P&C rating with schedule modifications from UW memo findings."""

    BASE_RATES: dict[InsuranceLine, float] = {
        InsuranceLine.COMMERCIAL_PROPERTY: 0.45,  # per $100 TIV
        InsuranceLine.GENERAL_LIABILITY: 0.12,
        InsuranceLine.WORKERS_COMP: 0.08,
        InsuranceLine.BOP: 0.55,
        InsuranceLine.UMBRELLA: 0.05,
    }

    def __init__(self, adapter: StubPolicyAdminAdapter | None = None) -> None:
        self.adapter = adapter or StubPolicyAdminAdapter()

    def quote(
        self,
        bundle: SubmissionBundle,
        memo: UnderwritingMemo,
        line: InsuranceLine = InsuranceLine.COMMERCIAL_PROPERTY,
    ) -> QuoteResult:
        tiv = self._estimate_tiv(bundle)
        loss_ratio = self._loss_ratio(bundle)
        state = self._primary_state(bundle)
        naics = self._naics(bundle)

        schedule_mod = memo.recommendation.suggested_premium_modification if memo.recommendation else 0.0
        schedule_mod = schedule_mod or 0.0

        request = QuoteRequest(
            bundle_id=bundle.bundle_id,
            line=line,
            tiv=tiv,
            state=state,
            naics_code=naics,
            loss_ratio=loss_ratio,
            schedule_mod_pct=schedule_mod,
        )

        result = self.adapter.submit_quote(request, memo, bundle)
        result.schedule_modifications.extend(self._build_modifiers(memo, loss_ratio))
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

    def _build_modifiers(self, memo: UnderwritingMemo, loss_ratio: float) -> list[RateComponent]:
        mods: list[RateComponent] = []
        if loss_ratio > 0.30:
            mods.append(RateComponent(name="adverse_loss_experience", amount=0, basis="loss_ratio", modifier_pct=15.0))
        elif loss_ratio < 0.10:
            mods.append(RateComponent(name="favorable_loss_experience", amount=0, basis="loss_ratio", modifier_pct=-10.0))

        if memo.decision == UWDecision.DECLINE:
            mods.append(RateComponent(name="decline_referral", amount=0, basis="uw_decision", modifier_pct=100.0))
        elif memo.decision == UWDecision.REFER:
            mods.append(RateComponent(name="refer_loading", amount=0, basis="uw_decision", modifier_pct=5.0))

        return mods
