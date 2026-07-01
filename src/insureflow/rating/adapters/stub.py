from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteRequest, QuoteResult, RateComponent


class StubPolicyAdminAdapter:
    """Deterministic stub for Guidewire/Duck Creek-style policy admin integration."""

    def submit_quote(self, request: QuoteRequest, memo: UnderwritingMemo, bundle: SubmissionBundle) -> QuoteResult:
        base_rate = 0.45 if request.line == InsuranceLine.COMMERCIAL_PROPERTY else 0.12
        base_premium = (request.tiv / 100.0) * base_rate

        adjusted = base_premium
        mods: list[RateComponent] = []

        if request.loss_ratio > 0.40:
            adjusted *= 1.25
            mods.append(RateComponent("loss_ratio_surcharge", adjusted - base_premium, "loss_ratio", 25.0))
        elif request.loss_ratio < 0.10:
            adjusted *= 0.90
            mods.append(RateComponent("loss_free_credit", adjusted - base_premium, "loss_ratio", -10.0))

        if request.schedule_mod_pct:
            factor = 1 + (request.schedule_mod_pct / 100.0)
            delta = adjusted * (factor - 1)
            adjusted *= factor
            mods.append(RateComponent("uw_schedule_mod", delta, "memo", request.schedule_mod_pct))

        ineligible: list[str] = []
        if memo.decision.value == "decline":
            ineligible.append("UW decision is DECLINE")
        if request.tiv <= 0:
            ineligible.append("TIV could not be determined")

        ref = f"PA-{uuid4().hex[:10].upper()}"
        valid_until = (datetime.now(tz=timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")

        return QuoteResult(
            bundle_id=request.bundle_id,
            line=request.line,
            base_premium=round(base_premium, 2),
            adjusted_premium=round(adjusted, 2),
            schedule_modifications=mods,
            rate_per_100_tiv=round(base_rate, 4),
            quote_valid_until=valid_until,
            eligible=len(ineligible) == 0,
            ineligibility_reasons=ineligible,
            policy_admin_reference=ref,
        )

    def bind_policy(self, bundle_id: str, quote_reference: str, bound_by: str) -> dict:
        return {
            "status": "bound",
            "bundle_id": bundle_id,
            "policy_number": f"POL-{uuid4().hex[:8].upper()}",
            "quote_reference": quote_reference,
            "bound_by": bound_by,
            "bound_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def sync_status(self, reference: str) -> dict:
        return {
            "reference": reference,
            "status": "quoted",
            "last_synced": datetime.now(tz=timezone.utc).isoformat(),
        }
