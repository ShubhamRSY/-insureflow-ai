from __future__ import annotations

from insureflow.webhooks.dispatcher import (  # noqa: F401
    BrokerStatusShare,
    WebhookDispatcher,
    WebhookSubscription,
    webhook_dispatcher,
)

"""
Re-exports the shared WebhookDispatcher singleton for backward compatibility.
All webhook logic now lives in insureflow.webhooks.dispatcher.
"""

__all__ = [
    "webhook_dispatcher",
    "WebhookDispatcher",
    "WebhookSubscription",
    "BrokerStatusShare",
]
