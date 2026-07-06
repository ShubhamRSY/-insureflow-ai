from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends

from insureflow.gateway import payloads
from insureflow.gateway.auth import verify_gateway_key

router = APIRouter(tags=["integration-gateway"])


def _health(service: str) -> dict[str, str]:
    return {"status": "ok", "service": service, "gateway": "rytera"}


def _service_router(prefix: str, service: str) -> APIRouter:
    sub = APIRouter(prefix=prefix, dependencies=[Depends(verify_gateway_key)])

    @sub.get("/health")
    def health() -> dict[str, str]:
        return _health(service)

    @sub.get("/status")
    def status() -> dict[str, str]:
        return _health(service)

    @sub.get("/")
    def root() -> dict[str, str]:
        return _health(service)

    return sub


# ── Oracles ─────────────────────────────────────────────────────

clue = _service_router("/oracles/clue/v2", "clue")


@clue.post("/queries")
def clue_queries(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.clue_query(body)


ncci = _service_router("/oracles/ncci/v2", "ncci")


@ncci.post("/experience")
def ncci_experience(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.ncci_query(body)


aplus = _service_router("/oracles/aplus/v2", "aplus")


@aplus.post("/queries")
def aplus_queries(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.aplus_query(body)


cat = _service_router("/oracles/cat/v1", "cat")


@cat.post("/model")
def cat_model(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.cat_query(body)


iso = _service_router("/oracles/iso/v1", "iso")


@iso.get("/rating")
def iso_rating() -> dict[str, Any]:
    return payloads.iso_health()


# ── Policy admin ────────────────────────────────────────────────

guidewire = _service_router("/policy/guidewire/v1", "guidewire")


@guidewire.post("/jobs")
def guidewire_jobs(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.policy_submit("guidewire", body)


@guidewire.post("/policies/bind")
def guidewire_bind(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.policy_bind("guidewire", body)


britecore = _service_router("/policy/britecore/v2", "britecore")


@britecore.post("/quotes")
def britecore_quotes(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.policy_submit("britecore", body)


@britecore.post("/policies/bind")
def britecore_bind(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.policy_bind("britecore", body)


# ── Enterprise ──────────────────────────────────────────────────

loss_control = _service_router("/enterprise/loss-control/v1", "loss_control")


@loss_control.post("/dispatch")
def loss_control_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.enterprise_ack("loss_control", body)


claims = _service_router("/enterprise/claims/v1", "claims")


@claims.post("/notify")
def claims_notify(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.enterprise_ack("claims", body)


broker_portal = _service_router("/enterprise/broker-portal/v1", "broker_portal")


@broker_portal.post("/document-requests")
def broker_doc_requests(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.enterprise_ack("broker_portal", body)


actuarial = _service_router("/enterprise/actuarial/v1", "actuarial")


@actuarial.post("/filings")
def actuarial_filings(body: dict[str, Any]) -> dict[str, Any]:
    return payloads.enterprise_ack("actuarial", body)


# ── CRM mock (local dev substitute for HubSpot) ───────────────

hubspot = _service_router("/crm/hubspot/v3", "hubspot")


@hubspot.get("/objects/contacts")
def hubspot_contacts() -> dict[str, Any]:
    return {"results": [], "total": 0}


@hubspot.post("/objects/contacts")
def hubspot_create_contact(body: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"contact-{uuid4().hex[:8]}", "properties": body.get("properties", {})}


@hubspot.post("/objects/deals")
def hubspot_create_deal(body: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"deal-{uuid4().hex[:8]}", "properties": body.get("properties", {})}


router.include_router(clue)
router.include_router(ncci)
router.include_router(aplus)
router.include_router(cat)
router.include_router(iso)
router.include_router(guidewire)
router.include_router(britecore)
router.include_router(loss_control)
router.include_router(claims)
router.include_router(broker_portal)
router.include_router(actuarial)
router.include_router(hubspot)
