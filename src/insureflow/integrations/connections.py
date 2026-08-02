"""Persisted source-connector registry.

Shared by the "Connect & pull" source hubs (insurance / mortgage / lending)
and the Integrations page: every successful pull registers the connection, and
the Integrations page lists all connectors with their live connected state.
"""

from __future__ import annotations

from typing import Any

from insureflow.storage.job_store import get_job_store

CONNECTIONS_NS = "connections"


def list_connections(org_id: str = "default") -> dict[str, dict[str, Any]]:
    store = get_job_store()
    return store.get(CONNECTIONS_NS, "registry", org_id=org_id) or {}


def get_connection(source_id: str, org_id: str = "default") -> dict[str, Any] | None:
    return list_connections(org_id).get(source_id)


def save_connection(
    source_id: str,
    config: dict[str, Any],
    label: str,
    org_id: str = "default",
) -> None:
    store = get_job_store()
    registry = list_connections(org_id)
    registry[source_id] = {
        "source_id": source_id,
        "config": config,
        "label": label,
        "connected": True,
    }
    store.set(CONNECTIONS_NS, "registry", registry, org_id=org_id)


def remove_connection(source_id: str, org_id: str = "default") -> bool:
    store = get_job_store()
    registry = list_connections(org_id)
    if source_id not in registry:
        return False
    del registry[source_id]
    store.set(CONNECTIONS_NS, "registry", registry, org_id=org_id)
    return True
