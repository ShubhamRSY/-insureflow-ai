from __future__ import annotations

import html.parser
import logging
from datetime import datetime, timezone
from typing import Any

import requests

from insureflow.regulatory.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class _LinkTextExtractor(html.parser.HTMLParser):
    """Extracts anchor links and their visible text from HTML pages."""

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


class WebScrapeCollector(BaseCollector):
    """Scrapes web pages for links and content using stdlib HTML parsing.

    Iterates over configured subpages relative to ``base_url``, extracts all
    anchor links with visible text, and resolves relative URLs against the
    base. Designed for sites like CA CDI that lack structured APIs.
    """

    def collect(self) -> list[dict[str, Any]]:
        """Scrape all configured subpages and return standardised items."""
        items: list[dict[str, Any]] = []
        base_url: str = self.config.get("base_url", "")
        subpages: list[str] = self.config.get("subpages", [])
        now = datetime.now(timezone.utc).isoformat()

        for subpage in subpages:
            url = f"{base_url}{subpage}"
            try:
                self._scrape_page(url, base_url, now, items)
            except Exception as exc:
                logger.warning("Failed to scrape %s: %s", url, exc)

        return items

    def _scrape_page(
        self,
        url: str,
        base_url: str,
        now: str,
        items: list[dict[str, Any]],
    ) -> None:
        """Fetch a single page and extract links."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        extractor = _LinkTextExtractor()
        extractor.feed(response.text)

        for link in extractor.links:
            href = link["url"]
            if not href.startswith("http"):
                href = f"{base_url}{href}"
            items.append(
                {
                    "source": self.source_name,
                    "title": link["title"],
                    "url": href,
                    "published": now,
                    "raw": {"page": url, **link},
                }
            )
