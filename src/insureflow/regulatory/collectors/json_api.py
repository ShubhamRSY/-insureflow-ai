from __future__ import annotations

import logging
from typing import Any

import requests

from insureflow.regulatory.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class JsonApiCollector(BaseCollector):
    """Collects data from JSON:API-compliant endpoints (e.g. NAIC Content API).

    Polls configured endpoints, parses JSON:API responses with a top-level
    ``data`` array, extracts title/date/attributes, and follows pagination
    via ``links.next``.
    """

    def collect(self) -> list[dict[str, Any]]:
        """Poll all configured endpoints and return standardised items."""
        items: list[dict[str, Any]] = []
        base_url: str = self.config.get("base_url", "")
        endpoints: list[dict[str, Any]] = self.config.get("endpoints", [])

        for endpoint in endpoints:
            path: str = endpoint.get("path", "")
            url = f"{base_url}{path}"
            filter_param: str = endpoint.get("filter", "")
            if filter_param:
                url = f"{url}?{filter_param}"

            try:
                self._poll_endpoint(url, base_url, items)
            except Exception as exc:
                logger.warning("Failed to collect from %s: %s", url, exc)

        return items

    def _poll_endpoint(
        self,
        url: str,
        base_url: str,
        items: list[dict[str, Any]],
    ) -> None:
        """Follow pagination for a single JSON:API endpoint."""
        page_url: str | None = url
        while page_url:
            response = requests.get(page_url, timeout=30)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            for item in data.get("data", []):
                attrs: dict[str, Any] = item.get("attributes", {})
                item_id: str = item.get("id", "")
                items.append(
                    {
                        "source": self.source_name,
                        "title": attrs.get("title", ""),
                        "url": f"{base_url}/node/{item_id}",
                        "published": attrs.get("created", ""),
                        "raw": item,
                    }
                )

            page_url = data.get("links", {}).get("next")
