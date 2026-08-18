from __future__ import annotations

import html.parser
import logging
from datetime import datetime, timezone
from typing import Any

import requests

from insureflow.regulatory.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class _AnnouncementParser(html.parser.HTMLParser):
    """Parses GovDelivery HTML to extract announcement links and titles."""

    def __init__(self) -> None:
        super().__init__()
        self._links: list[dict[str, str]] = []
        self._in_a = False
        self._current_href = ""
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._in_a = True
            for name, value in attrs:
                if name == "href":
                    self._current_href = value or ""
                    break

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_a:
            text = "".join(self._text_parts).strip()
            if self._current_href and text:
                self._links.append({"url": self._current_href, "title": text})
            self._in_a = False
            self._current_href = ""
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._text_parts.append(data)

    @property
    def links(self) -> list[dict[str, str]]:
        """Return all extracted link dicts with 'url' and 'title' keys."""
        return self._links


class GovDeliveryCollector(BaseCollector):
    """Collects announcements from GovDelivery account pages.

    Fetches the configured account page, parses anchor tags to extract
    announcement titles and URLs. The current UTC timestamp is used as
    the published date since GovDelivery pages rarely expose structured
    date metadata.
    """

    def collect(self) -> list[dict[str, Any]]:
        """Fetch the GovDelivery account page and return standardised items."""
        items: list[dict[str, Any]] = []
        url: str = self.config.get("url", "")
        if not url:
            return items

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            parser = _AnnouncementParser()
            parser.feed(response.text)

            now = datetime.now(timezone.utc).isoformat()
            for link in parser.links:
                items.append(
                    {
                        "source": self.source_name,
                        "title": link["title"],
                        "url": link["url"],
                        "published": now,
                        "raw": link,
                    }
                )
        except Exception as exc:
            logger.warning("Failed to collect GovDelivery from %s: %s", url, exc)

        return items
