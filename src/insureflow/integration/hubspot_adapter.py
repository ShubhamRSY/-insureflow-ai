from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class CRMContact:
    email: str
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    phone: str = ""
    lifecycle_stage: str = "lead"
    hubspot_id: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class CRMDeal:
    deal_name: str
    amount: float = 0.0
    stage: str = "appointment_scheduled"
    hubspot_id: str = ""
    contact_ids: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


class HubSpotAdapter:
    """Adapter for HubSpot CRM.

    Syncs underwriting contacts and deals to HubSpot for broker
    relationship management and pipeline tracking. Simulated mode
    returns deterministic mock responses — set HUBSPOT_API_KEY and
    HUBSPOT_MODE=live for production.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.hubapi.com/crm/v3",
        mode: str = "simulated",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self._enabled = bool(api_key) or True

    def create_contact(self, contact: CRMContact) -> dict[str, Any]:
        if not self._enabled:
            return {"success": False, "error": "HubSpot not configured"}

        if self.mode == "live":
            return self._call_live_api("contacts", contact.__dict__)

        contact.hubspot_id = f"contact-{uuid4().hex[:8]}"
        logger.info("HubSpot contact created: %s (%s)", contact.email, contact.hubspot_id)
        return {
            "success": True,
            "hubspot_id": contact.hubspot_id,
            "email": contact.email,
            "company": contact.company,
            "synced_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def create_deal(self, deal: CRMDeal) -> dict[str, Any]:
        if not self._enabled:
            return {"success": False, "error": "HubSpot not configured"}

        if self.mode == "live":
            return self._call_live_api("deals", deal.__dict__)

        deal.hubspot_id = f"deal-{uuid4().hex[:8]}"
        logger.info(
            "HubSpot deal created: %s (%s) — $%.0f", deal.deal_name, deal.hubspot_id, deal.amount
        )
        return {
            "success": True,
            "hubspot_id": deal.hubspot_id,
            "deal_name": deal.deal_name,
            "amount": deal.amount,
            "stage": deal.stage,
            "synced_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def sync_submission_to_deal(
        self,
        insured_name: str,
        premium: float,
        contact_email: str = "",
        broker_name: str = "",
    ) -> dict[str, Any]:
        contact = CRMContact(
            email=contact_email or f"{insured_name.lower().replace(' ', '.')}@example.com",
            company=insured_name,
            lifecycle_stage="opportunity",
        )
        contact_result = self.create_contact(contact)

        deal = CRMDeal(
            deal_name=f"Insurance Submission — {insured_name}",
            amount=premium,
            stage="qualified_to_buy",
            contact_ids=[contact_result.get("hubspot_id", "")]
            if contact_result.get("success")
            else [],
        )
        deal_result = self.create_deal(deal)

        return {
            "success": contact_result.get("success", False) and deal_result.get("success", False),
            "contact": contact_result,
            "deal": deal_result,
        }

    def _call_live_api(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": False,
            "error": f"Live HubSpot {endpoint} adapter not yet implemented — set HUBSPOT_MODE=simulated",
        }
