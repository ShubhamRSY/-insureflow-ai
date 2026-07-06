from __future__ import annotations

from typing import Any

from insureflow.config import settings
from insureflow.integrations.factory import (
    build_actuarial_client,
    build_broker_portal_client,
    build_claims_client,
    build_iso_rating_client,
    build_loss_control_client,
    build_policy_admin_service,
)
from insureflow.integrations.http_client import IntegrationHTTPClient, build_http_client
from insureflow.oracles.factory import (
    build_aplus_client,
    build_cat_client,
    build_clue_client,
    build_ncci_client,
)


def effective_mode(service_mode: str, client: IntegrationHTTPClient) -> str:
    mode = (service_mode or "auto").lower()
    if mode == "simulated":
        return "simulated"
    if not client.configured:
        return "misconfigured" if mode == "live" else "simulated"
    health = client.health_check()
    if health.get("reachable"):
        return "live"
    return "simulated" if mode == "auto" else "degraded"


class IntegrationHealthService:
    """Verify connectivity for production integrations."""

    def check_all(self, org_id: str = "default") -> dict[str, Any]:
        clue = build_clue_client()
        feeds = [
            self._oracle_feed("CLUE", clue.http, settings.oracle_mode),
            self._oracle_feed("NCCI", build_ncci_client().http, settings.oracle_mode),
            self._oracle_feed("A-PLUS", build_aplus_client().http, settings.oracle_mode),
            self._oracle_feed("CAT", build_cat_client().http, settings.oracle_mode),
            self._service_feed("ISO Loss Costs", build_iso_rating_client(), settings.iso_rating_mode),
            self._service_feed("Loss Control", build_loss_control_client(), settings.loss_control_mode),
            self._service_feed("Claims", build_claims_client(), settings.claims_mode),
            self._service_feed("Broker Portal", build_broker_portal_client(), settings.broker_portal_mode),
            self._service_feed("Actuarial", build_actuarial_client(), settings.actuarial_mode),
            self._service_feed(
                "HubSpot CRM",
                build_http_client(settings.hubspot_api_key, settings.hubspot_api_url),
                settings.hubspot_mode,
            ),
            self._service_feed(
                "Guidewire",
                build_http_client(settings.guidewire_api_key, settings.guidewire_api_url),
                settings.guidewire_mode,
            ),
            self._service_feed(
                "BriteCore",
                build_http_client(settings.britecore_api_key, settings.britecore_api_url),
                settings.britecore_mode,
            ),
        ]
        return {"org_id": org_id, "feeds": feeds, "policy_admin": build_policy_admin_service().status()}

    def _oracle_feed(self, name: str, http: IntegrationHTTPClient, mode_setting: str) -> dict[str, Any]:
        return self._service_feed(name, http, mode_setting)

    def _service_feed(self, name: str, http: IntegrationHTTPClient, mode_setting: str) -> dict[str, Any]:
        mode = effective_mode(mode_setting, http)
        health = http.health_check() if http.configured else {"reachable": False, "error": "not configured"}
        return {
            "name": name,
            "mode": mode,
            "configured": http.configured,
            "reachable": health.get("reachable", False),
            "health": health,
        }
