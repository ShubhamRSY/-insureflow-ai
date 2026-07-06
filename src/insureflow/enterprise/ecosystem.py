from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from insureflow.audit.store import AuditStore
from insureflow.config import settings
from insureflow.integrations.factory import (
    build_actuarial_client,
    build_broker_portal_client,
    build_claims_client,
    build_hubspot_adapter,
    build_loss_control_client,
)
from insureflow.integrations.health import IntegrationHealthService, effective_mode
from insureflow.integrations.http_client import IntegrationHTTPError
from insureflow.outcomes.feedback import FeedbackEngine
from insureflow.oracles._live import resolve_integration_mode


class EnterpriseEcosystemService:
    """Production enterprise integrations with live HTTP adapters and simulated fallback."""

    def oracle_feed_status(self, org_id: str) -> dict[str, Any]:
        return IntegrationHealthService().check_all(org_id)

    def loss_control_dispatch(self, bundle_id: str, org_id: str, notes: str = "") -> dict[str, Any]:
        client = build_loss_control_client()
        mode = resolve_integration_mode(settings.loss_control_mode, client)
        if mode == "live":
            try:
                resp = client.post(
                    "/inspections",
                    {"bundle_id": bundle_id, "org_id": org_id, "notes": notes, "priority": "standard"},
                )
                if resp.ok:
                    data = resp.json_dict()
                    return {
                        "dispatch_id": data.get("dispatch_id", f"lc-{uuid4().hex[:8]}"),
                        "bundle_id": bundle_id,
                        "org_id": org_id,
                        "status": data.get("status", "scheduled"),
                        "inspector": data.get("inspector", ""),
                        "scheduled_for": data.get("scheduled_for", datetime.now(tz=timezone.utc).isoformat()),
                        "mode": "live",
                    }
            except IntegrationHTTPError as exc:
                return {"bundle_id": bundle_id, "status": "failed", "error": str(exc), "mode": "live"}
        return {
            "dispatch_id": f"lc-{uuid4().hex[:8]}",
            "bundle_id": bundle_id,
            "org_id": org_id,
            "status": "scheduled",
            "inspector": "Rytera Field Network (simulated)",
            "scheduled_for": datetime.now(tz=timezone.utc).isoformat(),
            "notes": notes,
            "mode": "simulated",
        }

    def claims_ops_summary(self, bundle_id: str, org_id: str) -> dict[str, Any]:
        client = build_claims_client()
        if resolve_integration_mode(settings.claims_mode, client) == "live":
            try:
                resp = client.get(f"/claims/summary/{bundle_id}", query={"org_id": org_id})
                if resp.ok:
                    return {**resp.json_dict(), "bundle_id": bundle_id, "org_id": org_id, "mode": "live"}
            except IntegrationHTTPError:
                pass
        summary = self._claims_from_submission(bundle_id, org_id)
        summary["mode"] = "simulated"
        summary["full_claims_ops"] = resolve_integration_mode(settings.claims_mode, client) == "live"
        return summary

    def _claims_from_submission(self, bundle_id: str, org_id: str) -> dict[str, Any]:
        store = AuditStore()
        bundle = store.load_json(bundle_id, "submission_bundle.json", org_id=org_id) or {}
        fin = (bundle.get("structured") or {}).get("financial") or {}
        loss_run = fin.get("loss_run") or {}
        claims = loss_run.get("claims") or []
        incurred = float(loss_run.get("total_incurred", 0) or 0)
        return {
            "bundle_id": bundle_id,
            "org_id": org_id,
            "open_claims": sum(1 for c in claims if str(c.get("status", "")).lower() == "open"),
            "closed_claims": sum(1 for c in claims if str(c.get("status", "")).lower() != "open") or max(len(claims), 0),
            "total_incurred": incurred,
            "loss_run_source": "submission_ingest",
        }

    def actuarial_filing_status(self, bundle_id: str, org_id: str) -> dict[str, Any]:
        client = build_actuarial_client()
        if resolve_integration_mode(settings.actuarial_mode, client) == "live":
            try:
                resp = client.get(f"/filings/status/{bundle_id}", query={"org_id": org_id})
                if resp.ok:
                    return {**resp.json_dict(), "bundle_id": bundle_id, "mode": "live"}
            except IntegrationHTTPError:
                pass
        return {
            "bundle_id": bundle_id,
            "org_id": org_id,
            "filing_status": "rules_in_code",
            "rate_table_version": "iso_2024_q4",
            "model_governance": "internal_review",
            "actuarial_signoff_required": True,
            "mode": "simulated",
        }

    def agency_crm_summary(self, bundle_id: str, org_id: str, insured_name: str = "", premium: float = 0.0) -> dict[str, Any]:
        hubspot = build_hubspot_adapter()
        mode = hubspot._resolved_mode()
        crm: dict[str, Any] = {
            "bundle_id": bundle_id,
            "org_id": org_id,
            "broker_portal": "status_link",
            "mode": mode,
        }
        if mode == "live" and insured_name:
            sync = hubspot.sync_submission_to_deal(insured_name, premium)
            crm.update({"hubspot": sync, "full_ams": True})
        else:
            bundle = AuditStore().load_json(bundle_id, "submission_bundle.json", org_id=org_id) or {}
            broker = ((bundle.get("structured") or {}).get("broker") or {})
            crm.update({
                "full_ams": False,
                "agency_name": broker.get("broker_name", "Broker portal"),
                "producer_code": broker.get("producer_code", ""),
                "submission_channel": broker.get("channel", "email_ingest"),
            })
        return crm

    def request_broker_documents(self, bundle_id: str, org_id: str, documents: list[str]) -> dict[str, Any]:
        client = build_broker_portal_client()
        if resolve_integration_mode(settings.broker_portal_mode, client) == "live":
            try:
                resp = client.post(
                    "/document-requests",
                    {"bundle_id": bundle_id, "org_id": org_id, "documents": documents},
                )
                if resp.ok:
                    data = resp.json_dict()
                    return {
                        "request_id": data.get("request_id", f"br-{uuid4().hex[:8]}"),
                        "bundle_id": bundle_id,
                        "status": data.get("status", "sent"),
                        "requested_documents": documents,
                        "broker_notified": True,
                        "mode": "live",
                    }
            except IntegrationHTTPError as exc:
                return {"bundle_id": bundle_id, "status": "failed", "error": str(exc), "mode": "live"}
        return {
            "request_id": f"br-{uuid4().hex[:8]}",
            "bundle_id": bundle_id,
            "org_id": org_id,
            "status": "sent",
            "requested_documents": documents,
            "broker_notified": True,
            "message": "Document request queued (simulated)",
            "mode": "simulated",
        }

    def resolve_checkpoint(
        self,
        bundle_id: str,
        org_id: str,
        checkpoint_id: str,
        action: str,
        reviewer: str = "",
    ) -> dict[str, Any]:
        store = AuditStore()
        raw = store.load_json(bundle_id, "checkpoints.json", org_id=org_id) or []
        checkpoints = raw.get("items", []) if isinstance(raw, dict) else list(raw)
        updated = []
        for cp in checkpoints:
            if cp.get("id") == checkpoint_id:
                cp["status"] = "approved" if action == "approve" else "rejected"
                cp["reviewed_by"] = reviewer or "underwriter"
                cp["reviewed_at"] = datetime.now(tz=timezone.utc).isoformat()
            updated.append(cp)
        if not updated:
            updated = [{
                "id": checkpoint_id,
                "status": "approved" if action == "approve" else "rejected",
                "reviewed_by": reviewer or "underwriter",
                "reviewed_at": datetime.now(tz=timezone.utc).isoformat(),
            }]
        store.save_json(bundle_id, "checkpoints.json", updated, org_id=org_id)
        return {
            "bundle_id": bundle_id,
            "checkpoint_id": checkpoint_id,
            "action": action,
            "status": "approved" if action == "approve" else "rejected",
            "reviewed_by": reviewer or "underwriter",
            "reviewed_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    def actuarial_feedback_loop(self, org_id: str) -> dict[str, Any]:
        engine = FeedbackEngine()
        pending = len(engine.store.list_experiences(org_id))
        client = build_actuarial_client()
        mode = effective_mode(settings.actuarial_mode, client)
        if mode == "live":
            try:
                resp = client.get("/calibration/status", query={"org_id": org_id})
                if resp.ok:
                    return {**resp.json_dict(), "org_id": org_id, "mode": "live"}
            except IntegrationHTTPError:
                pass
        return {
            "org_id": org_id,
            "last_calibration": datetime.now(tz=timezone.utc).isoformat(),
            "claims_to_actuarial": "enabled" if pending else "awaiting_outcomes",
            "rate_tables_updated": False,
            "pending_loss_development": pending,
            "recommended_action": "Record bind outcomes to close the actuarial feedback loop",
            "mode": mode,
        }

    def bundle_ecosystem(self, bundle_id: str, org_id: str) -> dict[str, Any]:
        summary = AuditStore().load_json(bundle_id, "pipeline_summary.json", org_id=org_id) or {}
        insured = summary.get("insured_name", "")
        premium = float((summary.get("quote") or {}).get("adjusted_premium", 0) or 0)
        return {
            "bundle_id": bundle_id,
            "org_id": org_id,
            "oracle_feeds": self.oracle_feed_status(org_id),
            "loss_control": {"available": True, "mode": resolve_integration_mode(settings.loss_control_mode, build_loss_control_client())},
            "claims": self.claims_ops_summary(bundle_id, org_id),
            "actuarial": self.actuarial_filing_status(bundle_id, org_id),
            "agency": self.agency_crm_summary(bundle_id, org_id, insured_name=insured, premium=premium),
            "actuarial_loop": self.actuarial_feedback_loop(org_id),
        }


_ecosystem: EnterpriseEcosystemService | None = None


def get_ecosystem_service() -> EnterpriseEcosystemService:
    global _ecosystem
    if _ecosystem is None:
        _ecosystem = EnterpriseEcosystemService()
    return _ecosystem
