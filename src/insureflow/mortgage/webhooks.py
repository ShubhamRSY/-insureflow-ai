from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class WebhookSubscription:
    subscription_id: str
    org_id: str
    url: str
    events: list[str] = field(default_factory=lambda: ["mortgage.completed", "mortgage.failed"])
    secret: str = ""
    active: bool = True


class WebhookDispatcher:
    """Fire webhook notifications on mortgage pipeline events."""

    _subscriptions: dict[str, WebhookSubscription] = {}

    def register(
        self,
        org_id: str,
        url: str,
        events: list[str] | None = None,
        secret: str = "",
    ) -> WebhookSubscription:
        sub = WebhookSubscription(
            subscription_id=f"wh-{uuid4().hex[:12]}",
            org_id=org_id,
            url=url,
            events=events or ["mortgage.completed", "mortgage.failed"],
            secret=secret or uuid4().hex,
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
            result = self._deliver(sub, body, envelope)
            results.append(result)
        return results

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


# Module-level singleton
webhook_dispatcher = WebhookDispatcher()
