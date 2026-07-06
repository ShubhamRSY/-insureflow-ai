from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.integrations.http_client import IntegrationHTTPError, build_http_client
from insureflow.oracles._live import resolve_integration_mode

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
    """Adapter for HubSpot CRM REST API."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.hubapi.com/crm/v3",
        mode: str = "auto",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mode = mode
        self.http = build_http_client(api_key, base_url)

    def _resolved_mode(self) -> str:
        return resolve_integration_mode(self.mode, self.http)

    def create_contact(self, contact: CRMContact) -> dict[str, Any]:
        if self._resolved_mode() == "live":
            return self._call_live_api("contacts", contact.__dict__)

        contact.hubspot_id = f"contact-{uuid4().hex[:8]}"
        return {
            "success": True,
            "hubspot_id": contact.hubspot_id,
            "email": contact.email,
            "company": contact.company,
            "synced_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def create_deal(self, deal: CRMDeal) -> dict[str, Any]:
        if self._resolved_mode() == "live":
            return self._call_live_api("deals", deal.__dict__)

        deal.hubspot_id = f"deal-{uuid4().hex[:8]}"
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
            contact_ids=[contact_result.get("hubspot_id", "")] if contact_result.get("success") else [],
        )
        deal_result = self.create_deal(deal)
        return {
            "success": contact_result.get("success", False) and deal_result.get("success", False),
            "contact": contact_result,
            "deal": deal_result,
        }

    def _call_live_api(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        try:
            if endpoint == "contacts":
                body = {
                    "properties": {
                        "email": data.get("email", ""),
                        "firstname": data.get("first_name", ""),
                        "lastname": data.get("last_name", ""),
                        "company": data.get("company", ""),
                        "phone": data.get("phone", ""),
                        "lifecyclestage": data.get("lifecycle_stage", "lead"),
                    }
                }
                resp = self.http.post("/objects/contacts", body)
            else:
                body = {
                    "properties": {
                        "dealname": data.get("deal_name", ""),
                        "amount": str(data.get("amount", 0)),
                        "dealstage": data.get("stage", "appointmentscheduled"),
                    }
                }
                resp = self.http.post("/objects/deals", body)
            if not resp.ok:
                return {"success": False, "error": f"HubSpot HTTP {resp.status_code}"}
            payload = resp.json_dict()
            return {"success": True, "hubspot_id": str(payload.get("id", "")), "response": payload}
        except IntegrationHTTPError as exc:
            return {"success": False, "error": str(exc)}
