from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from insureflow.storage.job_store import JobStore

logger = logging.getLogger(__name__)

BROKER_SHARE_NS = "broker_shares"
BROKER_SHARE_ORG = "_public"
DELIVERY_LOG_NS = "webhook_deliveries"
_MAX_DELIVERY_LOG_ENTRIES = 200


@dataclass
class WebhookSubscription:
    subscription_id: str
    org_id: str
    url: str
    events: list[str] = field(default_factory=lambda: ["insurance.completed", "insurance.failed"])
    secret: str = ""
    active: bool = True
    label: str = ""


@dataclass
class DeliveryAttempt:
    attempt: int
    timestamp: str
    status: str
    http_status: int = 0
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class DeliveryRecord:
    delivery_id: str
    subscription_id: str
    event: str
    url: str
    org_id: str
    final_status: str
    attempts: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    completed_at: str = ""

    def to_store(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> DeliveryRecord | None:
        if not data or not data.get("delivery_id"):
            return None
        try:
            return cls(
                delivery_id=str(data["delivery_id"]),
                subscription_id=str(data.get("subscription_id") or ""),
                event=str(data.get("event") or ""),
                url=str(data.get("url") or ""),
                org_id=str(data.get("org_id") or ""),
                final_status=str(data.get("final_status") or "unknown"),
                attempts=data.get("attempts") or [],
                created_at=str(data.get("created_at") or ""),
                completed_at=str(data.get("completed_at") or ""),
            )
        except (TypeError, KeyError, ValueError):
            return None


@dataclass
class BrokerStatusShare:
    """A shareable token that lets a broker view submission status without auth."""

    token: str
    bundle_id: str
    org_id: str
    broker_name: str = ""
    broker_email: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    expires_at: str = ""
    active: bool = True

    def to_store(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> BrokerStatusShare | None:
        if not data or not data.get("token"):
            return None
        try:
            return cls(
                token=str(data["token"]),
                bundle_id=str(data.get("bundle_id") or ""),
                org_id=str(data.get("org_id") or ""),
                broker_name=str(data.get("broker_name") or ""),
                broker_email=str(data.get("broker_email") or ""),
                created_at=str(data.get("created_at") or ""),
                expires_at=str(data.get("expires_at") or ""),
                active=bool(data.get("active", True)),
            )
        except (TypeError, KeyError, ValueError):
            return None


def _share_store() -> JobStore | None:
    try:
        from insureflow.storage.job_store import get_job_store

        return get_job_store()
    except Exception:
        logger.debug("Broker share store unavailable", exc_info=True)
        return None


class WebhookDispatcher:
    """Shared webhook dispatcher for both insurance and mortgage events."""

    _subscriptions: dict[str, WebhookSubscription] = {}
    _broker_shares: dict[str, BrokerStatusShare] = {}

    def register(
        self,
        org_id: str,
        url: str,
        events: list[str] | None = None,
        secret: str = "",
        label: str = "",
    ) -> WebhookSubscription:
        sub = WebhookSubscription(
            subscription_id=f"wh-{uuid4().hex[:12]}",
            org_id=org_id,
            url=url,
            events=events or ["insurance.completed", "insurance.failed"],
            secret=secret or uuid4().hex,
            label=label,
        )
        self._subscriptions[sub.subscription_id] = sub
        return sub

    def unregister(self, subscription_id: str, org_id: str) -> bool:
        sub = self._subscriptions.get(subscription_id)
        if sub and sub.org_id == org_id:
            del self._subscriptions[subscription_id]
            return True
        return False

    def list_for_org(self, org_id: str) -> list[WebhookSubscription]:
        return [s for s in self._subscriptions.values() if s.org_id == org_id and s.active]

    def dispatch(self, event: str, org_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        envelope = {
            "event": event,
            "org_id": org_id,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "payload": payload,
        }
        body = json.dumps(envelope, default=str)

        for sub in self.list_for_org(org_id):
            if event not in sub.events and "*" not in sub.events:
                continue
            result = self._deliver_with_retry(sub, body, envelope)
            results.append(result)
        return results

    def dispatch_async(self, event: str, org_id: str, payload: dict[str, Any]) -> None:
        """Fire-and-forget dispatch in a background thread so the pipeline is never blocked."""
        t = threading.Thread(target=self.dispatch, args=(event, org_id, payload), daemon=True)
        t.start()

    def _deliver_with_retry(
        self,
        sub: WebhookSubscription,
        body: str,
        envelope: dict[str, Any],
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> dict[str, Any]:
        delivery = DeliveryRecord(
            delivery_id=f"dlv-{uuid4().hex[:12]}",
            subscription_id=sub.subscription_id,
            event=envelope["event"],
            url=sub.url,
            org_id=sub.org_id,
            final_status="pending",
        )

        last_result: dict[str, Any] = {}
        for attempt in range(max_retries + 1):
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                time.sleep(delay)

            t0 = time.monotonic()
            result = self._deliver(sub, body, envelope)
            duration = (time.monotonic() - t0) * 1000

            attempt_record = {
                "attempt": attempt + 1,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "status": result.get("status", "failed"),
                "http_status": result.get("http_status", 0),
                "error": result.get("error", ""),
                "duration_ms": round(duration, 1),
            }
            delivery.attempts.append(attempt_record)
            last_result = result

            if result.get("status") == "delivered":
                delivery.final_status = "delivered"
                break

            http_status = result.get("http_status", 0)
            if http_status and 400 <= http_status < 500 and http_status != 429:
                delivery.final_status = "failed"
                break
        else:
            delivery.final_status = "failed"

        delivery.completed_at = datetime.now(tz=timezone.utc).isoformat()
        self._log_delivery(delivery)

        last_result["delivery_id"] = delivery.delivery_id
        last_result["attempts"] = len(delivery.attempts)
        last_result["final_status"] = delivery.final_status
        return last_result

    def _deliver(
        self,
        sub: WebhookSubscription,
        body: str,
        envelope: dict[str, Any],
    ) -> dict[str, Any]:
        import urllib.error
        import urllib.request

        headers = {"Content-Type": "application/json", "User-Agent": "InsureFlow-Webhook/1.0"}
        if sub.secret:
            sig = hmac.new(sub.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-InsureFlow-Signature"] = f"sha256={sig}"

        req = urllib.request.Request(sub.url, data=body.encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {
                    "subscription_id": sub.subscription_id,
                    "url": sub.url,
                    "status": "delivered",
                    "http_status": resp.status,
                    "event": envelope["event"],
                }
        except urllib.error.HTTPError as exc:
            logger.warning("Webhook delivery failed %s: HTTP %s", sub.url, exc.code)
            return {
                "subscription_id": sub.subscription_id,
                "url": sub.url,
                "status": "failed",
                "http_status": exc.code,
                "error": str(exc),
            }
        except Exception as exc:
            logger.warning("Webhook delivery failed %s: %s", sub.url, exc)
            return {
                "subscription_id": sub.subscription_id,
                "url": sub.url,
                "status": "failed",
                "error": str(exc),
            }

    def _log_delivery(self, record: DeliveryRecord) -> None:
        store = _share_store()
        if store is None:
            return
        try:
            store.set(
                DELIVERY_LOG_NS,
                record.delivery_id,
                record.to_store(),
                org_id=record.org_id,
            )
        except Exception:
            logger.debug("Failed to persist delivery log %s", record.delivery_id, exc_info=True)

    def get_delivery(self, delivery_id: str, org_id: str) -> DeliveryRecord | None:
        store = _share_store()
        if store is None:
            return None
        try:
            raw = store.get(DELIVERY_LOG_NS, delivery_id, org_id=org_id)
            return DeliveryRecord.from_store(raw)
        except Exception:
            return None

    def list_deliveries(self, org_id: str, limit: int = 50) -> list[DeliveryRecord]:
        store = _share_store()
        if store is None:
            return []
        try:
            ids = store.list_ids(DELIVERY_LOG_NS, org_id)
            records: list[DeliveryRecord] = []
            for did in ids[-limit:]:
                raw = store.get(DELIVERY_LOG_NS, did, org_id=org_id)
                rec = DeliveryRecord.from_store(raw)
                if rec:
                    records.append(rec)
            return sorted(records, key=lambda r: r.created_at, reverse=True)
        except Exception:
            return []

    # ── Broker Status Share (unauthenticated submission tracking) ──

    def create_broker_share(
        self,
        bundle_id: str,
        org_id: str,
        broker_name: str = "",
        broker_email: str = "",
        ttl_hours: int = 168,
    ) -> str:
        """Create a shareable token that returns submission status without auth."""
        from datetime import timedelta

        token = f"brk-{uuid4().hex[:16]}"
        now = datetime.now(tz=timezone.utc)
        share = BrokerStatusShare(
            token=token,
            bundle_id=bundle_id,
            org_id=org_id,
            broker_name=broker_name,
            broker_email=broker_email,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(hours=ttl_hours)).isoformat(),
        )
        self._broker_shares[token] = share
        store = _share_store()
        if store is not None:
            try:
                store.set(BROKER_SHARE_NS, token, {"share": share.to_store()}, org_id=BROKER_SHARE_ORG)
            except Exception:
                logger.warning("Failed to persist broker share %s", token, exc_info=True)
        return token

    def get_broker_share(self, token: str) -> BrokerStatusShare | None:
        share = self._broker_shares.get(token)
        if share is None:
            store = _share_store()
            if store is not None:
                try:
                    raw = store.get(BROKER_SHARE_NS, token, org_id=BROKER_SHARE_ORG) or {}
                    payload = raw.get("share") if isinstance(raw.get("share"), dict) else raw
                    share = BrokerStatusShare.from_store(payload)
                    if share is not None:
                        self._broker_shares[token] = share
                except Exception:
                    logger.debug("Broker share lookup failed for %s", token, exc_info=True)
                    share = None
        if not share or not share.active:
            return None
        if share.expires_at:
            try:
                expires = datetime.fromisoformat(share.expires_at)
                if datetime.now(tz=timezone.utc) > expires:
                    return None
            except (ValueError, TypeError):
                pass
        return share

    def revoke_broker_share(self, token: str) -> bool:
        share = self.get_broker_share(token)
        if not share:
            return False
        share.active = False
        self._broker_shares[token] = share
        store = _share_store()
        if store is not None:
            try:
                store.set(BROKER_SHARE_NS, token, {"share": share.to_store()}, org_id=BROKER_SHARE_ORG)
            except Exception:
                logger.debug("Failed to persist revoked broker share", exc_info=True)
        return True

    def list_broker_shares(self, org_id: str) -> list[BrokerStatusShare]:
        found = {s.token: s for s in self._broker_shares.values() if s.org_id == org_id and s.active}
        store = _share_store()
        if store is not None:
            try:
                for token in store.list_ids(BROKER_SHARE_NS, org_id=BROKER_SHARE_ORG):
                    raw = store.get(BROKER_SHARE_NS, token, org_id=BROKER_SHARE_ORG) or {}
                    payload = raw.get("share") if isinstance(raw.get("share"), dict) else raw
                    share = BrokerStatusShare.from_store(payload)
                    if share and share.org_id == org_id and share.active:
                        found[share.token] = share
                        self._broker_shares[share.token] = share
            except Exception:
                logger.debug("list_broker_shares store scan failed", exc_info=True)
        return list(found.values())


# Module-level singleton (replaces old mortgage-only dispatcher)
webhook_dispatcher = WebhookDispatcher()
