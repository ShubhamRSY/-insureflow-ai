from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from insureflow.integration.base_adapter import (
    BasePolicyAdminAdapter,
    IntegrationResult,
    PolicySubmissionPayload,
)
from insureflow.integrations.http_client import build_http_client
from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.oracles._live import resolve_integration_mode

logger = logging.getLogger(__name__)


class BriteCoreAdapter(BasePolicyAdminAdapter):
    """Adapter for BriteCore policy administration REST API."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.britecore.com/v2",
        agency_id: str = "",
        mode: str = "auto",
        submit_path: str = "/quotes",
        bind_path: str = "/policies/bind",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.agency_id = agency_id
        self.mode = mode
        self.submit_path = submit_path
        self.bind_path = bind_path
        self.http = build_http_client(api_key, base_url)
        self.last_quote_reference = ""

    def get_system_name(self) -> str:
        return "BriteCore"

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def submit_quote(self, payload: PolicySubmissionPayload) -> IntegrationResult:
        if self._resolved_mode() == "live":
            return self._submit_live(payload)
        quote_ref = f"BC-Q-{uuid4().hex[:10].upper()}"
        self.last_quote_reference = quote_ref
        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=quote_ref,
            response_payload={"quote_id": quote_ref, "status": "quoted", "integration_type": "simulated"},
        )

    def bind_policy(self, payload: PolicySubmissionPayload, quote_reference: str) -> IntegrationResult:
        if self._resolved_mode() == "live":
            return self._bind_live(payload, quote_reference)
        policy_number = f"BC-{datetime.now(tz=timezone.utc).year}-{uuid4().hex[:8].upper()}"
        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=quote_reference,
            policy_number=policy_number,
            response_payload={"policy_number": policy_number, "status": "bound"},
        )

    def status(self) -> dict:
        return {
            "system": self.get_system_name(),
            "mode": self._resolved_mode(),
            "configured": self.http.configured,
            "health": self.http.health_check() if self.http.configured else {"reachable": False},
        }

    def _submit_live(self, payload: PolicySubmissionPayload) -> IntegrationResult:
        try:
            body = {
                "agency_id": self.agency_id,
                "bundle_id": payload.bundle_id,
                "insured_name": payload.insured_name,
                "premium": payload.adjusted_premium,
                "locations": payload.locations,
                "coverages": payload.coverages,
            }
            resp = self.http.post(self.submit_path, body)
            if not resp.ok:
                return IntegrationResult(success=False, system=self.get_system_name(), error=f"HTTP {resp.status_code}")
            data = resp.json_dict()
            ref = str(data.get("quote_id") or data.get("id", ""))
            self.last_quote_reference = ref
            return IntegrationResult(success=True, system=self.get_system_name(), external_reference=ref, response_payload=data)
        except IntegrationHTTPError as exc:
            return IntegrationResult(success=False, system=self.get_system_name(), error=str(exc))

    def _bind_live(self, payload: PolicySubmissionPayload, quote_reference: str) -> IntegrationResult:
        try:
            resp = self.http.post(self.bind_path, {"quote_id": quote_reference, "bundle_id": payload.bundle_id})
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
