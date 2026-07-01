from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from insureflow.integration.base_adapter import (
    BasePolicyAdminAdapter,
    IntegrationResult,
    PolicySubmissionPayload,
)

logger = logging.getLogger(__name__)


class GuidewireAdapter(BasePolicyAdminAdapter):
    """Adapter for Guidewire PolicyCenter.

    Guidewire offers SOAP/REST APIs (PolicyCenter v10+) for policy
    administration. This implementation is a simulated stub — in
    production, replace with actual Guidewire Integration Gateway calls.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://policycenter.guidewire.com/v1",
        username: str = "",
        password: str = "",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.username = username
        self.password = password
        self._enabled = bool(api_key) or True

    def get_system_name(self) -> str:
        return "Guidewire PolicyCenter"

    def submit_quote(self, payload: PolicySubmissionPayload) -> IntegrationResult:
        if not self._enabled:
            return IntegrationResult(
                success=False,
                system=self.get_system_name(),
                error="Guidewire integration not configured",
            )

        logger.info(
            "Guidewire quote submission: %s for %s",
            payload.bundle_id,
            payload.insured_name,
        )

        job_number = f"GW-JOB-{uuid4().hex[:10].upper()}"
        response = {
            "job_number": job_number,
            "job_type": "new_submission",
            "status": "in_review",
            "product": "commercial_package",
            "insured": payload.insured_name,
            "underwriter_assignment": "auto",
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "integration_type": "api_rest",
            "system": self.get_system_name(),
        }

        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=job_number,
            response_payload=response,
        )

    def bind_policy(self, payload: PolicySubmissionPayload, quote_reference: str) -> IntegrationResult:
        policy_number = f"GW-POL-{datetime.now(tz=timezone.utc).year}-{uuid4().hex[:8].upper()}"
        response = {
            "policy_number": policy_number,
            "policy_period": {
                "effective_date": datetime.now(tz=timezone.utc).isoformat(),
                "term_type": "annual",
            },
            "status": "in_force",
            "job_reference": quote_reference,
            "premium": payload.adjusted_premium,
            "bound_at": datetime.now(tz=timezone.utc).isoformat(),
        }

        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=quote_reference,
            policy_number=policy_number,
            response_payload=response,
        )
