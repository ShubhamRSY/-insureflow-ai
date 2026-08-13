"""ISO-style rating adapter — production policy admin integration.

Uses ISO loss cost tables and the internal rating engine when no external
API is configured. When GUIDEWIRE_API_KEY or ISO_RATING_API_KEY is set,
attempts live policy admin integration first.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteRequest, QuoteResult, RateComponent, RatingAdapter

logger = logging.getLogger(__name__)


class ISORatingAdapter(RatingAdapter):
    """ISO-based policy admin adapter with optional live Guidewire/Duck Creek integration."""

    def __init__(self) -> None:
        self._guidewire_key = os.getenv("GUIDEWIRE_API_KEY", "")
        self._guidewire_url = os.getenv("GUIDEWIRE_API_URL", "")
        self._iso_key = os.getenv("ISO_RATING_API_KEY", "")
        self._iso_url = os.getenv("ISO_RATING_API_URL", "")

    @property
    def _use_live(self) -> bool:
        from insureflow.oracles._live import is_bundled_gateway_url

        if self._guidewire_key and not is_bundled_gateway_url(self._guidewire_url, self._guidewire_key):
            return True
        if self._iso_key and not is_bundled_gateway_url(self._iso_url, self._iso_key):
            return True
        return False

    def submit_quote(self, request: QuoteRequest, memo: UnderwritingMemo, bundle: SubmissionBundle) -> QuoteResult:
        if self._use_live:
            try:
                return self._live_submit(request, memo, bundle)
            except Exception as exc:
                logger.warning("Live policy admin submit failed, falling back to local: %s", exc)

        return self._local_submit(request, memo, bundle)

    def _local_submit(self, request: QuoteRequest, memo: UnderwritingMemo, bundle: SubmissionBundle) -> QuoteResult:
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
        from insureflow.decisions import is_decline

        if is_decline(memo.decision):
            ineligible.append("UW decision is DECLINE")
        if request.tiv <= 0:
            ineligible.append("TIV could not be determined")

        ref = f"ISO-{uuid4().hex[:10].upper()}"
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

    def _live_submit(self, request: QuoteRequest, memo: UnderwritingMemo, bundle: SubmissionBundle) -> QuoteResult:
        import json
        import urllib.request

        url = f"{self._guidewire_url.rstrip('/')}/jobs" if self._guidewire_key else f"{self._iso_url.rstrip('/')}/rate"
        payload = json.dumps(
            {
                "bundle_id": request.bundle_id,
                "line": request.line.value,
                "tiv": request.tiv,
                "state": request.state,
                "naics_code": request.naics_code,
                "loss_ratio": request.loss_ratio,
                "schedule_mod_pct": request.schedule_mod_pct,
            }
        ).encode()

        api_key = self._guidewire_key or self._iso_key
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        return QuoteResult(
            bundle_id=request.bundle_id,
            line=request.line,
            base_premium=float(data.get("base_premium", 0)),
            adjusted_premium=float(data.get("adjusted_premium", 0)),
            schedule_modifications=[RateComponent(name=m["name"], amount=m["amount"], basis=m.get("basis", ""), modifier_pct=m.get("modifier_pct", 0)) for m in data.get("modifiers", [])],
            rate_per_100_tiv=float(data.get("rate_per_100_tiv", 0)),
            quote_valid_until=data.get("valid_until", ""),
            eligible=data.get("eligible", True),
            ineligibility_reasons=data.get("ineligibility_reasons", []),
            policy_admin_reference=str(data.get("job_number") or data.get("external_reference") or data.get("reference") or data.get("id") or f"LIVE-{uuid4().hex[:8].upper()}"),
        )

    def bind_policy(self, bundle_id: str, quote_reference: str, bound_by: str) -> dict[str, Any]:
        from insureflow.security.posture import allow_simulated_bind, resolve_security_posture

        if self._guidewire_key:
            try:
                return self._live_bind(bundle_id, quote_reference, bound_by)
            except Exception as exc:
                logger.warning("Live bind failed: %s", exc)
                if resolve_security_posture().is_hardened and not allow_simulated_bind():
                    return {
                        "status": "failed",
                        "success": False,
                        "bundle_id": bundle_id,
                        "quote_reference": quote_reference,
                        "bound_by": bound_by,
                        "error": f"Live policy-admin bind failed: {exc}",
                        "bound_at": datetime.now(tz=timezone.utc).isoformat(),
                    }

        if resolve_security_posture().is_hardened and not allow_simulated_bind():
            return {
                "status": "failed",
                "success": False,
                "bundle_id": bundle_id,
                "quote_reference": quote_reference,
                "bound_by": bound_by,
                "error": "Simulated bind is disabled in BANK_MODE/production. Configure live Guidewire bind or set ALLOW_SIMULATED_BIND=true.",
                "bound_at": datetime.now(tz=timezone.utc).isoformat(),
            }

        return {
            "status": "bound",
            "success": True,
            "mode": "simulated",
            "bundle_id": bundle_id,
            "policy_number": f"POL-{uuid4().hex[:8].upper()}",
            "quote_reference": quote_reference,
            "bound_by": bound_by,
            "bound_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def _live_bind(self, bundle_id: str, quote_reference: str, bound_by: str) -> dict[str, Any]:
        import json
        import urllib.request

        url = f"{self._guidewire_url.rstrip('/')}/policies/bind"
        payload = json.dumps(
            {
                "bundle_id": bundle_id,
                "quote_reference": quote_reference,
                "bound_by": bound_by,
                "source": "iso_adapter",
                "note": "Prefer PolicyAdminService.bind_from_summary for full Guidewire terms",
            }
        ).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._guidewire_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result: dict[str, Any] = json.loads(resp.read().decode())
            return result

    def sync_status(self, reference: str) -> dict[str, Any]:
        return {
            "reference": reference,
            "status": "quoted",
            "last_synced": datetime.now(tz=timezone.utc).isoformat(),
        }
