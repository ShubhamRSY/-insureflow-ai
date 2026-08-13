"""Connect registry for marketplace sources — wraps integrations.connections."""

from __future__ import annotations

from typing import Any

from insureflow.integrations.connections import get_connection, list_connections, remove_connection, save_connection
from insureflow.marketplace.catalog import get_source, list_marketplace_sources


def connect_source(
    source_id: str,
    *,
    config: dict[str, Any] | None = None,
    label: str = "",
    org_id: str = "default",
) -> dict[str, Any]:
    meta = get_source(source_id)
    if meta is None:
        raise ValueError(f"Unknown marketplace source: {source_id}")
    display = label or str(meta["name"])
    save_connection(source_id, config or {}, display, org_id=org_id)
    record = get_connection(source_id, org_id=org_id) or {}
    return {**meta, "connected": True, "connection": record}


def disconnect_source(source_id: str, *, org_id: str = "default") -> bool:
    return remove_connection(source_id, org_id=org_id)


def list_connected_sources(*, org_id: str = "default") -> list[dict[str, Any]]:
    registry = list_connections(org_id)
    out: list[dict[str, Any]] = []
    for source_id, rec in registry.items():
        if not isinstance(rec, dict):
            continue  # job store stamps org_id / updated_at onto the registry blob
        meta = get_source(source_id) or {"id": source_id, "name": rec.get("label", source_id)}
        out.append({**meta, "connected": True, "connection": rec})
    return out


def catalog_with_connection_state(*, org_id: str = "default", **filters: Any) -> list[dict[str, Any]]:
    connected = {sid for sid, rec in list_connections(org_id).items() if isinstance(rec, dict)}
    items = [
        dict(s)
        for s in list_marketplace_sources(
            category=filters.get("category"),
            vertical=filters.get("vertical"),
            q=filters.get("q"),
        )
    ]
    for item in items:
        item["connected"] = item["id"] in connected
    return items
