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


class BriteCoreAdapter(BasePolicyAdminAdapter):
    """Adapter for BriteCore policy administration system.

    BriteCore offers a REST API for policy creation, quoting, and bind.
    This implementation provides a simulated integration that logs the
    submission and returns mock references — in production, replaces
    with actual BriteCore API calls.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.britecore.com/v1",
        agency_id: str = "",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.agency_id = agency_id
        self._enabled = bool(api_key) or True  # Simulated mode

    def get_system_name(self) -> str:
        return "BriteCore"

    def submit_quote(self, payload: PolicySubmissionPayload) -> IntegrationResult:
        if not self._enabled:
            return IntegrationResult(
                success=False,
                system=self.get_system_name(),
                error="BriteCore integration not configured",
            )

        logger.info(
            "BriteCore quote submission: %s for %s (TIV $%.0f, premium $%.0f)",
            payload.bundle_id, payload.insured_name, payload.tiv, payload.adjusted_premium,
        )

        # Simulated BriteCore API call
        quote_ref = f"BC-Q-{uuid4().hex[:10].upper()}"
        response = {
            "quote_id": quote_ref,
            "status": "quoted",
            "premium_quoted": payload.adjusted_premium,
            "premium_base": payload.base_premium,
            "insured_name": payload.insured_name,
            "submitted_at": datetime.now(tz=timezone.utc).isoformat(),
            "policy_admin_system": self.get_system_name(),
            "integration_type": "api",
        }

        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=quote_ref,
            response_payload=response,
        )

    def bind_policy(self, payload: PolicySubmissionPayload, quote_reference: str) -> IntegrationResult:
        policy_number = f"BC-{datetime.now(tz=timezone.utc).year}-{uuid4().hex[:8].upper()}"
        response = {
            "policy_number": policy_number,
            "status": "bound",
            "effective_date": datetime.now(tz=timezone.utc).isoformat(),
            "premium_bound": payload.adjusted_premium,
            "quote_reference": quote_reference,
            "bound_at": datetime.now(tz=timezone.utc).isoformat(),
        }

        return IntegrationResult(
            success=True,
            system=self.get_system_name(),
            external_reference=quote_reference,
            policy_number=policy_number,
            response_payload=response,
        )
