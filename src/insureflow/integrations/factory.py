from __future__ import annotations

from insureflow.config import settings
from insureflow.integration.britecore_adapter import BriteCoreAdapter
from insureflow.integration.guidewire_adapter import GuidewireAdapter
from insureflow.integration.hubspot_adapter import HubSpotAdapter
from insureflow.integration.policy_admin_service import PolicyAdminService
from insureflow.integrations.http_client import IntegrationHTTPClient, build_http_client


def build_hubspot_adapter() -> HubSpotAdapter:
    return HubSpotAdapter(
        api_key=settings.hubspot_api_key,
        base_url=settings.hubspot_api_url,
        mode=settings.hubspot_mode,
    )


def build_loss_control_client() -> IntegrationHTTPClient:
    return build_http_client(settings.loss_control_api_key, settings.loss_control_api_url)


def build_claims_client() -> IntegrationHTTPClient:
    return build_http_client(settings.claims_api_key, settings.claims_api_url)


def build_broker_portal_client() -> IntegrationHTTPClient:
    return build_http_client(settings.broker_portal_api_key, settings.broker_portal_api_url)


def build_actuarial_client() -> IntegrationHTTPClient:
    return build_http_client(settings.actuarial_api_key, settings.actuarial_api_url)


def build_iso_rating_client() -> IntegrationHTTPClient:
    return build_http_client(settings.iso_rating_api_key, settings.iso_rating_api_url)


def build_policy_admin_service() -> PolicyAdminService:
    primary = BriteCoreAdapter(
        api_key=settings.britecore_api_key,
        base_url=settings.britecore_api_url,
        mode=settings.britecore_mode,
    )
    fallback = GuidewireAdapter(
        api_key=settings.guidewire_api_key,
        base_url=settings.guidewire_api_url,
        username=settings.guidewire_username,
        password=settings.guidewire_password,
        mode=settings.guidewire_mode,
    )
    return PolicyAdminService(primary_adapter=primary, fallback_adapter=fallback)
