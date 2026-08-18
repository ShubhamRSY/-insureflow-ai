from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from insureflow.regulatory.collectors.base import BaseCollector
from insureflow.regulatory.collectors.govdelivery import GovDeliveryCollector
from insureflow.regulatory.collectors.json_api import JsonApiCollector
from insureflow.regulatory.collectors.rss import RssCollector
from insureflow.regulatory.collectors.web_scrape import WebScrapeCollector

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_SOURCES_FILE = Path(__file__).parent / "sources.yaml"
_POLL_LOG_DIR = Path(__file__).parent / "poll_logs"

COLLECTOR_MAP: dict[str, type[BaseCollector]] = {
    "json_api": JsonApiCollector,
    "rss": RssCollector,
    "govdelivery": GovDeliveryCollector,
    "web_scrape": WebScrapeCollector,
}


class RegulatoryPoller:
    """Polls all active regulatory sources and stores results.

    Reads source configuration from ``sources.yaml``, instantiates the
    appropriate collector for each source type, polls enabled sources,
    and persists results as JSONL files for downstream consumption.
    """

    def __init__(self) -> None:
        self._sources: dict[str, Any] = {}
        self._loaded = False
        _POLL_LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _ensure_loaded(self) -> None:
        """Load sources.yaml once."""
        if self._loaded:
            return
        try:
            with open(_SOURCES_FILE, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            self._sources = raw.get("sources", {}) if isinstance(raw, dict) else {}
            self._loaded = True
        except Exception as exc:
            logger.warning("Failed to load sources: %s", exc)

    def poll_source(self, source_name: str) -> list[dict[str, Any]]:
        """Poll a single source and return collected items."""
        self._ensure_loaded()
        source_config = self._sources.get(source_name)
        if source_config is None:
            return []
        collector_type: str = source_config.get("type", "")
        collector_cls = COLLECTOR_MAP.get(collector_type)
        if collector_cls is None:
            logger.warning("Unknown collector type %r for source %s", collector_type, source_name)
            return []
        collector = collector_cls(source_name=source_name, config=source_config)
        if not collector.is_enabled():
            return []
        try:
            return collector.collect()
        except Exception as exc:
            logger.warning("Failed to poll %s: %s", source_name, exc)
            return []

    def poll_all(self) -> dict[str, list[dict[str, Any]]]:
        """Poll all enabled sources. Returns ``{source_name: [items]}``."""
        self._ensure_loaded()
        results: dict[str, list[dict[str, Any]]] = {}

        for source_name, source_config in self._sources.items():
            collector_type: str = source_config.get("type", "")
            collector_cls = COLLECTOR_MAP.get(collector_type)
            if collector_cls is None:
                continue
            collector = collector_cls(source_name=source_name, config=source_config)
            if not collector.is_enabled():
                continue

            try:
                items = collector.collect()
                results[source_name] = items
                self._log_poll(source_name, items)
                self._store_items(source_name, items)
            except Exception as exc:
                logger.warning("Failed to poll %s: %s", source_name, exc)
                self._log_poll(source_name, [], error=str(exc))
                results[source_name] = []

        return results

    def get_poll_log(self, limit: int = 20) -> list[dict[str, Any]]:
        """Read recent poll log entries from ``poll_logs/`` directory."""
        log_files = sorted(_POLL_LOG_DIR.glob("*.jsonl"), reverse=True)
        entries: list[dict[str, Any]] = []

        for log_file in log_files:
            if len(entries) >= limit:
                break
            try:
                with open(log_file, encoding="utf-8") as f:
                    lines = f.readlines()
                for line in reversed(lines):
                    if len(entries) >= limit:
                        break
                    stripped = line.strip()
                    if stripped:
                        entries.append(json.loads(stripped))
            except Exception:
                continue

        return entries[:limit]

    def get_latest_items(self, source_name: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Get most recently collected items across all sources."""
        items: list[dict[str, Any]] = []
        if not _DATA_DIR.exists():
            return []

        for data_file in _DATA_DIR.glob("*.jsonl"):
            if source_name and data_file.stem != source_name:
                continue
            try:
                with open(data_file, encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped:
                            items.append(json.loads(stripped))
            except Exception:
                continue

        items.sort(key=lambda x: x.get("published", ""), reverse=True)
        return items[:limit]

    def _log_poll(
        self,
        source_name: str,
        items: list[dict[str, Any]],
        error: str = "",
    ) -> None:
        """Append a poll log entry to the daily JSONL file."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = _POLL_LOG_DIR / f"{date_str}.jsonl"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source_name,
            "items_collected": len(items),
            "error": error,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _store_items(self, source_name: str, items: list[dict[str, Any]]) -> None:
        """Persist collected items to a JSONL file in the data directory."""
        data_file = _DATA_DIR / f"{source_name}.jsonl"
        with open(data_file, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item) + "\n")
