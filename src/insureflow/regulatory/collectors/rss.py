from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from insureflow.regulatory.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class RssCollector(BaseCollector):
    """Collects data from RSS feeds using stdlib XML parsing.

    Fetches each configured feed URL, parses ``<item>`` elements for title,
    link, pubDate, and description. Dates are converted from RFC 822 to ISO
    8601 when possible.
    """

    def collect(self) -> list[dict[str, Any]]:
        """Poll all configured RSS feeds and return standardised items."""
        items: list[dict[str, Any]] = []
        feeds: list[dict[str, Any]] = self.config.get("feeds", [])

        for feed_config in feeds:
            url: str = feed_config.get("url", "")
            try:
                self._poll_feed(url, items)
            except Exception as exc:
                logger.warning("Failed to collect RSS from %s: %s", url, exc)

        return items

    def _poll_feed(self, url: str, items: list[dict[str, Any]]) -> None:
        """Fetch and parse a single RSS feed."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        for item_elem in root.iter("item"):
            title = self._get_text(item_elem, "title")
            link = self._get_text(item_elem, "link")
            pub_date_str = self._get_text(item_elem, "pubDate")
            description = self._get_text(item_elem, "description")
            published = self._parse_rfc822_date(pub_date_str)

            items.append(
                {
                    "source": self.source_name,
                    "title": title,
                    "url": link,
                    "published": published,
                    "raw": {
                        "title": title,
                        "link": link,
                        "pubDate": pub_date_str,
                        "description": description,
                    },
                }
            )

    @staticmethod
    def _get_text(elem: ET.Element, tag: str) -> str:
        """Return the text content of a child element, or empty string."""
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text
        return ""

    @staticmethod
    def _parse_rfc822_date(date_str: str) -> str:
        """Parse an RFC 822 date string to ISO 8601, returning original on failure."""
        if not date_str:
            return ""
        try:
            return parsedate_to_datetime(date_str).isoformat()
        except Exception:
            return date_str
