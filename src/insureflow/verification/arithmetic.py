"""Layer 1 — deterministic mathematical & logical constraints.

Prevents the most common extraction failure mode: numbers that are individually
plausible but internally inconsistent. Three invariants:

- **Balance-sheet identity**: Assets = Liabilities + Equity.
- **Sum-to-total**: line items must sum to their declared total (explicit groups,
  or auto-detected from ``total_<stem>`` / ``<stem>_total`` field families).
- **Cross-page reconciliation**: a figure stated on multiple pages/sections must
  agree within tolerance.

All checks are pure and deterministic; they return ``VerificationIssue`` objects
carrying the source ``page_number``/``bbox`` for HITL highlighting.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Mapping, Sequence

from insureflow.models.submissions import ExtractedField, VerificationIssue
from insureflow.verification.common import SEVERITY_ERROR, make_issue, to_number

_DEFAULT_TOLERANCE = 0.01
_TOTAL_RE = re.compile(r"(?:^|_)total|total(?:_|$)", re.IGNORECASE)
# A "total" whose stem names a count/quantity must never be summed against
# currency line items (e.g. ``total_claims`` vs ``claim_1``/``claim_2``).
_COUNT_TOTAL_WORDS = (
    "claim",
    "count",
    "number",
    "quantity",
    "days",
    "employees",
    "locations",
    "policies",
)
_LINE_ITEM_WORDS = (
    "claim",
    "premium",
    "expense",
    "payroll",
    "item",
    "value",
    "amount",
    "limit",
    "deduction",
    "asset",
    "liab",
    "equity",
    "revenue",
    "cost",
    "loss",
    "reserve",
    "payment",
)


def _asset_keys(fields: Mapping[str, Sequence[ExtractedField]]) -> list[str]:
    return [k for k in fields if re.search(r"asset", k, re.IGNORECASE) and not re.search(r"liab", k, re.IGNORECASE)]


def balance_sheet_identity(fields: Mapping[str, Sequence[ExtractedField]], tolerance: float = _DEFAULT_TOLERANCE) -> list[VerificationIssue]:
    """Assert Assets = Liabilities + Equity when all three are extracted."""
    parsed = {k: to_number(next(iter(fields[k])).value) for k in fields if fields[k]}
    nums: dict[str, float] = {k: v for k, v in parsed.items() if v is not None}
    assets = sum(v for k, v in nums.items() if re.search(r"asset", k, re.IGNORECASE) and "liab" not in k.lower())
    liabilities = sum(v for k, v in nums.items() if re.search(r"liab", k, re.IGNORECASE))
    equity = sum(v for k, v in nums.items() if re.search(r"equity", k, re.IGNORECASE))
    if assets == 0 and not _asset_keys(fields):
        return []
    if liabilities == 0 and equity == 0:
        return []
    if assets == 0:
        # Only the liability/equity side is present — nothing to balance against.
        return []
    if liabilities == 0 and equity != 0 and not any(re.search(r"liab", k, re.IGNORECASE) for k in fields):
        return []
    expected = liabilities + equity
    if abs(assets - expected) > max(tolerance * abs(expected), 1.0):
        field_name = _asset_keys(fields)[0]
        return [
            make_issue(
                "balance_sheet_identity",
                SEVERITY_ERROR,
                f"Assets ({assets:,.2f}) ≠ Liabilities ({liabilities:,.2f}) + Equity ({equity:,.2f}) = {expected:,.2f} (Δ {assets - expected:,.2f})",
                fields,
                field_name,
            )
        ]
    return []


def sum_to_total_verification(
    fields: Mapping[str, Sequence[ExtractedField]],
    total_key: str,
    item_keys: list[str],
    tolerance: float = _DEFAULT_TOLERANCE,
) -> list[VerificationIssue]:
    """Explicit sum-to-total check for a known line-item family."""
    parsed = {k: to_number(next(iter(fields[k])).value) for k in fields if fields[k]}
    nums: dict[str, float] = {k: v for k, v in parsed.items() if v is not None}
    total = nums.get(total_key)
    if total is None:
        return []
    items = [nums[k] for k in item_keys if k in nums]
    if len(items) < 2:
        return []
    summed = sum(items)
    if abs(summed - total) > max(tolerance * abs(total), 1.0):
        return [
            make_issue(
                "sum_to_total",
                SEVERITY_ERROR,
                f"line items ({', '.join(item_keys)}) sum to {summed:,.2f} but {total_key}={total:,.2f} (Δ {summed - total:,.2f})",
                fields,
                total_key,
            )
        ]
    return []


def auto_sum_to_total(fields: Mapping[str, Sequence[ExtractedField]], tolerance: float = _DEFAULT_TOLERANCE) -> list[VerificationIssue]:
    """Auto-detect ``total_<stem>`` families and verify line items sum to them.

    Conservative: only checks when at least two sibling items share the stem or
    a line-item keyword (claim/premium/expense/...), and never treats count-like
    fields (``total_claims``, ``*_count``) as additive totals.
    """
    parsed = {k: to_number(next(iter(fields[k])).value) for k in fields if fields[k]}
    nums: dict[str, float] = {k: v for k, v in parsed.items() if v is not None}

    def _is_count_total(key: str) -> bool:
        stem = _TOTAL_RE.sub("", key).strip("_ ").lower()
        return any(word in stem for word in _COUNT_TOTAL_WORDS)

    total_keys = [k for k in nums if _TOTAL_RE.search(k) and not _is_count_total(k)]
    if not total_keys:
        return []
    issues: list[VerificationIssue] = []
    for total_key in total_keys:
        stem = _TOTAL_RE.sub("", total_key).strip("_ ")
        items = [k for k, v in nums.items() if k != total_key and not _TOTAL_RE.search(k) and (stem and stem in k.lower() or any(word in k.lower() for word in _LINE_ITEM_WORDS))]
        if len(items) < 2:
            continue
        summed = sum(nums[k] for k in items)
        total = nums[total_key]
        if abs(summed - total) > max(tolerance * abs(total), 1.0):
            issues.append(
                make_issue(
                    "sum_to_total",
                    SEVERITY_ERROR,
                    f"line items ({', '.join(items)}) sum to {summed:,.2f} but {total_key}={total:,.2f} (Δ {summed - total:,.2f})",
                    fields,
                    total_key,
                )
            )
    return issues


def cross_page_reconciliation(
    value_sets: Mapping[str, list[tuple[Any, Any]]],
    tolerance: float = _DEFAULT_TOLERANCE,
) -> list[VerificationIssue]:
    """Check figures stated in multiple locations reconcile.

    ``value_sets`` maps a metric (e.g. ``net_income``) to ``(location, value)``
    pairs, where ``location`` is a page/section identifier and ``value`` a number.
    A metric appearing in ≥2 locations with divergent values produces an error.
    """
    issues: list[VerificationIssue] = []
    for metric, entries in value_sets.items():
        parsed = [(loc, to_number(str(v))) for loc, v in entries]
        numerics: list[tuple[object, float]] = [(loc, num) for loc, num in parsed if num is not None]
        if len(numerics) < 2:
            continue
        baseline = numerics[0]
        for loc, num in numerics[1:]:
            if abs(num - baseline[1]) > max(tolerance * abs(baseline[1]), 1.0):
                issues.append(
                    VerificationIssue(
                        code="cross_page_reconciliation",
                        severity=SEVERITY_ERROR,
                        message=(f"{metric} stated at {baseline[0]}={baseline[1]:,.2f} does not match {loc}={num:,.2f} (Δ {baseline[1] - num:,.2f})"),
                        field_name=metric,
                    )
                )
    return issues


def group_values_by_page(fields: Mapping[str, Sequence[ExtractedField]]) -> dict[str, list[tuple[str, float]]]:
    """Extract (page/section, value) pairs for every numeric field key."""
    out: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for key, entries in fields.items():
        for entry in entries:
            num = to_number(entry.value)
            if num is None:
                continue
            loc = f"page {entry.page_number}" if entry.page_number is not None else f"entry {entry.chunk_index}"
            out[key].append((loc, num))
    return dict(out)
