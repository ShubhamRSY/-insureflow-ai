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


class ISiModotechAdapter(BasePolicyAdminAdapter):
    """Adapter for ISi/Modotech policy administration.

    Built specifically for smaller property and casualty insurers.
    This implementation provides a simulated integration — in production,
    replace with actual Modotech REST API calls.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.modotech.com/v1",
        tenant_id: str = "",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.tenant_id = tenant_id
        self._enabled = bool(api_key) or True

    def get_system_name(self) -> str:
        return "ISi/Modotech"

    def submit_quote(self, payload: PolicySubmissionPayload) -> IntegrationResult:
        if not self._enabled:
            return IntegrationResult(
                success=False,
                system=self.get_system_name(),
                error="ISi/Modotech integration not configured",
            )

        logger.info(
            "ISi/Modotech quote: %s for %s (premium $%.0f)",
            payload.bundle_id, payload.insured_name, payload.adjusted_premium,
        )

        quote_ref = f"MOD-Q-{uuid4().hex[:10].upper()}"
        response = {
            "quote_id": quote_ref,
            "status": "quoted",
            "premium_quoted": payload.adjusted_premium,
            "insured_name": payload.insured_name,
            "tenant_id": self.tenant_id or "default",
            "submitted_at": datetime.now(tz=timezone.utc).isoformat(),
            "system": self.get_system_name(),
        }

        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=quote_ref,
            response_payload=response,
        )

    def bind_policy(self, payload: PolicySubmissionPayload, quote_reference: str) -> IntegrationResult:
        policy_number = f"MOD-{datetime.now(tz=timezone.utc).year}-{uuid4().hex[:8].upper()}"
        response = {
            "policy_number": policy_number,
            "status": "bound",
            "effective_date": datetime.now(tz=timezone.utc).isoformat(),
            "premium_bound": payload.adjusted_premium,
            "quote_reference": quote_reference,
        }

        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=quote_reference,
            policy_number=policy_number,
            response_payload=response,
        )
