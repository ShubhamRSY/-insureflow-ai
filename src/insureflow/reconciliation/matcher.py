from __future__ import annotations

from typing import Any, Optional


class FieldMatcher:
    def match(self, field_path: str, values: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not values:
            return None

        by_hierarchy = sorted(
            values,
            key=lambda v: v.get("source", {}).get("hierarchy_rank", 0),
            reverse=True,
        )

        authoritative = by_hierarchy[0]
        authoritative_val = str(authoritative.get("value", ""))
        source_name = authoritative.get("source", {}).get("source_name", "unknown")

        consensus_rate = 1.0
        if len(by_hierarchy) > 1:
            matches = sum(
                1 for val in by_hierarchy[1:]
                if str(val.get("value", "")) == authoritative_val
            )
            consensus_rate = matches / (len(by_hierarchy) - 1)

        return {
            "field_path": field_path,
            "resolved_value": authoritative.get("value"),
            "resolved_from": source_name,
            "hierarchy_rank": authoritative.get("source", {}).get("hierarchy_rank", 0),
            "confidence": authoritative.get("confidence", 0) * (0.5 + 0.5 * consensus_rate),
            "sources_checked": len(values),
            "consensus_rate": consensus_rate,
            "authoritative_source": source_name,
        }

    def fuzzy_match(self, val_a: Any, val_b: Any, tolerance: Optional[float] = None) -> bool:
        if val_a is None or val_b is None:
            return False

        str_a, str_b = str(val_a).strip().lower(), str(val_b).strip().lower()

        if str_a == str_b:
            return True

        if tolerance is not None:
            try:
                num_a, num_b = float(str_a), float(str_b)
                if num_a == 0 and num_b == 0:
                    return True
                max_val = max(abs(num_a), abs(num_b))
                if max_val > 0:
                    return abs(num_a - num_b) / max_val <= tolerance
            except (ValueError, TypeError):
                pass

        if len(str_a) > 3 and len(str_b) > 3:
            from difflib import SequenceMatcher
            ratio = SequenceMatcher(None, str_a, str_b).ratio()
            return ratio >= 0.85

        return False
