from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from insureflow.integration.base_adapter import (
    BasePolicyAdminAdapter,
    IntegrationResult,
    PolicySubmissionPayload,
)
from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.integrations.http_client import build_http_client
from insureflow.oracles._live import resolve_integration_mode

logger = logging.getLogger(__name__)


class GuidewireAdapter(BasePolicyAdminAdapter):
    """Adapter for Guidewire PolicyCenter REST API."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://policycenter.guidewire.com/api/v1",
        username: str = "",
        password: str = "",
        mode: str = "auto",
        submit_path: str = "/jobs",
        bind_path: str = "/policies/bind",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.username = username
        self.password = password
        self.mode = mode
        self.submit_path = submit_path
        self.bind_path = bind_path
        self.http = build_http_client(api_key, base_url)
        self.last_quote_reference = ""

    def get_system_name(self) -> str:
        return "Guidewire PolicyCenter"

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def submit_quote(self, payload: PolicySubmissionPayload) -> IntegrationResult:
        if self._resolved_mode() == "live":
            return self._submit_live(payload)
        return self._submit_simulated(payload)

    def bind_policy(self, payload: PolicySubmissionPayload, quote_reference: str) -> IntegrationResult:
        if self._resolved_mode() == "live":
            return self._bind_live(payload, quote_reference)
        policy_number = f"GW-POL-{datetime.now(tz=timezone.utc).year}-{uuid4().hex[:8].upper()}"
        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=quote_reference,
            policy_number=policy_number,
            response_payload={"policy_number": policy_number, "status": "in_force"},
        )

    def status(self) -> dict:
        return {
            "system": self.get_system_name(),
            "mode": self._resolved_mode(),
            "configured": self.http.configured,
            "health": self.http.health_check() if self.http.configured else {"reachable": False},
        }

    def _submit_simulated(self, payload: PolicySubmissionPayload) -> IntegrationResult:
        job_number = f"GW-JOB-{uuid4().hex[:10].upper()}"
        self.last_quote_reference = job_number
        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=job_number,
            response_payload={
                "job_number": job_number,
                "status": "in_review",
                "insured": payload.insured_name,
                "integration_type": "simulated",
            },
        )

    def _submit_live(self, payload: PolicySubmissionPayload) -> IntegrationResult:
        try:
            body = {
                "bundle_id": payload.bundle_id,
                "org_id": payload.org_id,
                "insured_name": payload.insured_name,
                "naics_code": payload.naics_code,
                "state": payload.state,
                "tiv": payload.tiv,
                "base_premium": payload.base_premium,
                "adjusted_premium": payload.adjusted_premium,
                "uw_decision": payload.uw_decision,
                "coverages": payload.coverages,
                "locations": payload.locations,
                "memo_summary": payload.memo_summary,
            }
            resp = self.http.post(self.submit_path, body)
            if not resp.ok:
                return IntegrationResult(success=False, system=self.get_system_name(), error=f"HTTP {resp.status_code}")
            data = resp.json_dict()
            ref = str(data.get("job_number") or data.get("external_reference") or data.get("id", ""))
            self.last_quote_reference = ref
            return IntegrationResult(success=True, system=self.get_system_name(), external_reference=ref, response_payload=data)
        except IntegrationHTTPError as exc:
            return IntegrationResult(success=False, system=self.get_system_name(), error=str(exc))

    def _bind_live(self, payload: PolicySubmissionPayload, quote_reference: str) -> IntegrationResult:
        try:
            resp = self.http.post(
                self.bind_path,
                {"quote_reference": quote_reference, "bundle_id": payload.bundle_id, "premium": payload.adjusted_premium},
            )
            if not resp.ok:
                return IntegrationResult(success=False, system=self.get_system_name(), error=f"HTTP {resp.status_code}")
            data = resp.json_dict()
            return IntegrationResult(
                success=True,
                system=self.get_system_name(),
                external_reference=quote_reference,
                policy_number=str(data.get("policy_number", "")),
                response_payload=data,
            )
        except IntegrationHTTPError as exc:
            return IntegrationResult(success=False, system=self.get_system_name(), error=str(exc))
