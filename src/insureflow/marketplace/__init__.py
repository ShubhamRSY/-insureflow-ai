"""80+ data-source marketplace and connect registry."""

from __future__ import annotations

from insureflow.marketplace.catalog import MARKETPLACE_SOURCES, get_source, list_marketplace_sources
from insureflow.marketplace.pull import pull_marketplace_source, pull_marketplace_sources
from insureflow.marketplace.registry import connect_source, disconnect_source, list_connected_sources

__all__ = [
    "MARKETPLACE_SOURCES",
    "connect_source",
    "disconnect_source",
    "get_source",
    "list_connected_sources",
    "list_marketplace_sources",
    "pull_marketplace_source",
    "pull_marketplace_sources",
]
