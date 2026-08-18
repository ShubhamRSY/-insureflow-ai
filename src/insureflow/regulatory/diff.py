from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from insureflow.regulatory.monitor import RegulatoryChange, RegulatoryMonitor

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"

_STATE_CODES: set[str] = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
}

_STATE_NAMES: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}

_NAME_TO_CODE: dict[str, str] = {v.lower(): k for k, v in _STATE_NAMES.items()}

_LINE_KEYWORDS: dict[str, list[str]] = {
    "auto": ["auto", "automobile", "vehicle", "motor vehicle", "personal auto", "commercial auto"],
    "property": ["property", "homeowners", "dwelling", "commercial property", "fire", "casualty"],
    "liability": ["liability", "general liability", "professional liability", "gl", "e&o", "e and o"],
    "workers_comp": ["workers comp", "workers compensation", "workforce", "wc", "employers liability"],
    "life": ["life insurance", "life", "term life", "whole life", "universal life", "annuity"],
    "health": ["health", "medical", "group health", "individual health", "health insurance"],
    "cyber": ["cyber", "data breach", "cybersecurity", "cyber liability"],
    "marine": ["marine", "ocean marine", "inland marine", "cargo"],
    "flood": ["flood", "nfip", "flood insurance"],
    "financial": ["financial", "credit", "credit life"],
    "specialty": ["specialty", "excess", "surplus lines", "surplus"],
    "package": ["package", "bundle", "commercial package", "cpp"],
}

_STATE_CODE_PATTERN = re.compile(r"\b([A-Z]{2})\b")
_STATE_NAME_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in sorted(_NAME_TO_CODE.keys(), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


class RegulatoryDiffEngine:
    """Compares current rules against fetched source data to detect changes."""

    def __init__(self) -> None:
        self._monitor = RegulatoryMonitor()
        self._line_files: dict[str, Path] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        for yaml_file in _DATA_DIR.glob("*.yaml"):
            self._line_files[yaml_file.stem] = yaml_file
        self._loaded = True

    def _load_line_data(self, line: str) -> dict[str, Any]:
        """Load current YAML data for a line of business."""
        self._ensure_loaded()
        path = self._line_files.get(line)
        if path is None:
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def match_state_from_text(self, text: str) -> list[str]:
        """Extract state codes from free text using keyword matching."""
        found: set[str] = set()
        for match in _STATE_CODE_PATTERN.finditer(text):
            code = match.group(1)
            if code in _STATE_CODES:
                found.add(code)
        for match in _STATE_NAME_PATTERN.finditer(text):
            name_lower = match.group(1).lower()
            code = _NAME_TO_CODE.get(name_lower)
            if code is not None:
                found.add(code)
        return sorted(found)

    def match_line_from_text(self, text: str) -> str:
        """Extract line of business from free text."""
        text_lower = text.lower()
        best_line = ""
        best_length = 0
        for line_name, keywords in _LINE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower and len(keyword) > best_length:
                    best_line = line_name
                    best_length = len(keyword)
        return best_line

    def detect_changes_from_naic(self, items: list[dict[str, Any]]) -> list[RegulatoryChange]:
        """Parse NAIC API items and detect relevant regulatory changes."""
        changes: list[RegulatoryChange] = []
        now = datetime.now(timezone.utc).isoformat()

        for item in items:
            title = item.get("title", "")
            body = item.get("body", item.get("description", ""))
            url = item.get("url", "")
            combined = f"{title} {body}"

            states = self.match_state_from_text(combined)
            line = self.match_line_from_text(combined)

            if not states or not line:
                continue

            for state_code in states:
                rule_data = self._load_line_data(line)
                states_data = rule_data.get("states", {})
                state_entry = states_data.get(state_code, {})

                if not state_entry:
                    continue

                changes.append(
                    RegulatoryChange(
                        state_code=state_code,
                        line_of_business=line,
                        rule_key="naic_update",
                        old_value=state_entry.get("notes", ""),
                        new_value=f"NAIC update: {title}",
                        source="naic_content_api",
                        detected_at=now,
                        source_url=url,
                        confidence="unverified",
                    )
                )

        logger.info("NAIC detection found %d potential changes", len(changes))
        return changes

    def detect_changes_from_rss(self, items: list[dict[str, Any]], source_name: str = "") -> list[RegulatoryChange]:
        """Parse RSS feed items and detect regulatory changes."""
        changes: list[RegulatoryChange] = []
        now = datetime.now(timezone.utc).isoformat()

        for item in items:
            title = item.get("title", "")
            description = item.get("description", item.get("summary", ""))
            url = item.get("url", item.get("link", ""))
            combined = f"{title} {description}"

            states = self.match_state_from_text(combined)
            line = self.match_line_from_text(combined)

            if not states or not line:
                continue

            for state_code in states:
                rule_data = self._load_line_data(line)
                states_data = rule_data.get("states", {})
                state_entry = states_data.get(state_code, {})

                if not state_entry:
                    continue

                changes.append(
                    RegulatoryChange(
                        state_code=state_code,
                        line_of_business=line,
                        rule_key="rss_update",
                        old_value=state_entry.get("notes", ""),
                        new_value=f"RSS update: {title}",
                        source=source_name or "rss_feed",
                        detected_at=now,
                        source_url=url,
                        confidence="unverified",
                    )
                )

        logger.info("RSS detection from '%s' found %d potential changes", source_name, len(changes))
        return changes

    def detect_changes_from_bulletin(self, items: list[dict[str, Any]], source_name: str = "") -> list[RegulatoryChange]:
        """Parse DOI bulletin items and detect rate/coverage changes."""
        changes: list[RegulatoryChange] = []
        now = datetime.now(timezone.utc).isoformat()

        rate_keywords = ["rate", "rate filing", "premium", "rate increase", "rate decrease"]
        coverage_keywords = ["mandatory coverage", "required coverage", "coverage mandate", "minimum coverage"]

        for item in items:
            title = item.get("title", "")
            description = item.get("description", item.get("body", ""))
            url = item.get("url", "")
            combined = f"{title} {description}".lower()

            states = self.match_state_from_text(combined)
            line = self.match_line_from_text(combined)

            if not states or not line:
                continue

            is_rate_change = any(kw in combined for kw in rate_keywords)
            is_coverage_change = any(kw in combined for kw in coverage_keywords)

            if not is_rate_change and not is_coverage_change:
                continue

            rule_key = "rate_filing" if is_rate_change else "mandatory_coverages"

            for state_code in states:
                rule_data = self._load_line_data(line)
                states_data = rule_data.get("states", {})
                state_entry = states_data.get(state_code, {})

                if not state_entry:
                    continue

                old_value = state_entry.get(rule_key, "")

                changes.append(
                    RegulatoryChange(
                        state_code=state_code,
                        line_of_business=line,
                        rule_key=rule_key,
                        old_value=old_value,
                        new_value=f"Bulletin: {title}",
                        source=source_name or "doi_bulletin",
                        detected_at=now,
                        source_url=url,
                        confidence="unverified",
                    )
                )

        logger.info("Bulletin detection from '%s' found %d potential changes", source_name, len(changes))
        return changes

    def detect_all_changes(self, collected_items: dict[str, list[dict[str, Any]]]) -> list[RegulatoryChange]:
        """Run change detection across all collected items."""
        all_changes: list[RegulatoryChange] = []

        for source_name, items in collected_items.items():
            if not items:
                continue

            first_item = items[0]
            source_type = first_item.get("source", source_name)

            if "naic" in source_type.lower():
                changes = self.detect_changes_from_naic(items)
            elif "rss" in source_type.lower() or "feed" in source_type.lower():
                changes = self.detect_changes_from_rss(items, source_name)
            elif "bulletin" in source_type.lower() or "doi" in source_type.lower():
                changes = self.detect_changes_from_bulletin(items, source_name)
            else:
                changes = self.detect_changes_from_rss(items, source_name)

            for change in changes:
                self._monitor.record_change(change)

            all_changes.extend(changes)

        logger.info(
            "Total changes detected across %d sources: %d",
            len(collected_items),
            len(all_changes),
        )
        return all_changes
