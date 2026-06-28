from __future__ import annotations

"""
Re-exports the shared WebhookDispatcher singleton for backward compatibility.
All webhook logic now lives in insureflow.webhooks.dispatcher.
"""

from insureflow.webhooks.dispatcher import (
    BrokerStatusShare,
    WebhookDispatcher,
    WebhookSubscription,
    webhook_dispatcher,
)

__all__ = [
    "webhook_dispatcher",
    "WebhookDispatcher",
    "WebhookSubscription",
    "BrokerStatusShare",
]
