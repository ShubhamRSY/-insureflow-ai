"""Life LOB logic paths — explicit per-LOB / per-Product / per-Coverage code.

Architecture decision (confirmed): every Line of Business, every Product,
and every Coverage option owns a dedicated logic path in code. State rules
are applied INSIDE each path (not as a bolt-on layer) because compliance
differs by state AND product at the same time.

Adding LOB 3–7 later = create ``insureflow.life.lobs.<lob>.<product>``
modules following the same pattern and register them in PRODUCT_LOGIC_PATHS.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Callable

from insureflow.life.lobs.base import LifeProductContext  # re-export
from insureflow.life.lobs.base import LobOutcome as LobOutcome
from insureflow.life.lobs.term_life import TERM_LIFE_LOGIC_PATHS
from insureflow.life.lobs.whole_life import WHOLE_LIFE_LOGIC_PATHS

# Explicit registry: normalized product id -> module path owning its logic.
PRODUCT_LOGIC_PATHS: dict[str, str] = {**TERM_LIFE_LOGIC_PATHS, **WHOLE_LIFE_LOGIC_PATHS}

# Fallback matching when the caller passes only a coverage id / free-text name.
_COVERAGE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"level[_\s-]?term|^\d{2}[\s-]*year"), "level_term"),
    (re.compile(r"mortgage[_\s-]?(protection|balance)|lender[_\s-]?assign", re.I), "mortgage_life"),
    (re.compile(r"debt[_\s-]?reduc|decreasing", re.I), "decreasing_term"),
    (re.compile(r"cpi|step.?up|increasing", re.I), "increasing_term"),
    (re.compile(r"annual[_\s-]?renewable|\bart\b|renewab", re.I), "renewable_term"),
    (re.compile(r"convertib", re.I), "convertible_term"),
    (re.compile(r"\brop\b|return.?of.?premium", re.I), "rop_term"),
    (re.compile(r"group[_\s-]?(basic|supplemental|dependent|life)", re.I), "group_term_life"),
    (re.compile(r"credit[_\s-]?life|loan[_\s-]?balance", re.I), "credit_life"),
    (re.compile(r"limited[_\s-]?pay|(?:10|20|ten|twenty)[_\s-]?pay|paid.?up.?at.?65", re.I), "limited_pay_whole_life"),
    (re.compile(r"single[_\s-]?premium", re.I), "single_premium_whole_life"),
    (re.compile(r"participating|\bpar\b", re.I), "participating_whole_life"),
    (re.compile(r"non[_\s-]?participating|non.?par", re.I), "non_participating_whole_life"),
    (re.compile(r"modified", re.I), "modified_whole_life"),
    (re.compile(r"graded|guaranteed[_\s-]?issue", re.I), "graded_guaranteed_issue_whole_life"),
    (re.compile(r"whole[_\s-]?life|ordinary", re.I), "traditional_whole_life"),
]


def normalize_id(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


@lru_cache(maxsize=None)
def _load_builder(module_path: str) -> Callable[[LifeProductContext], Any] | None:
    try:
        module = __import__(module_path, fromlist=["build_quote"])
        return getattr(module, "build_quote", None)
    except (ImportError, AttributeError):
        return None


def resolve_product_id(
    product_id: str | None,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
) -> str | None:
    """Resolve which registered logic path owns this submission."""
    pid = normalize_id(product_id)
    if pid in PRODUCT_LOGIC_PATHS:
        return pid
    blob = f"{normalize_id(coverage_id)} {coverage_name or ''}"
    for pattern, target in _COVERAGE_HINTS:
        if pattern.search(blob):
            return target
    return None


def resolve_logic_path(product_id: str | None, coverage_id: str | None = None, coverage_name: str | None = None) -> str | None:
    resolved = resolve_product_id(product_id, coverage_id, coverage_name)
    return PRODUCT_LOGIC_PATHS.get(resolved or "")


def run_product_logic(ctx: LifeProductContext) -> Any:
    """Execute the owning product path; None when no dedicated path exists.

    Each product module exposes ``build_quote(ctx) -> QuoteResult`` — the
    full, self-contained logic for that product/coverage including its own
    state-rule application.
    """
    resolved = resolve_product_id(ctx.product_id, ctx.coverage_id, ctx.coverage_name)
    if not resolved:
        return None
    builder = _load_builder(PRODUCT_LOGIC_PATHS[resolved])
    if builder is None:
        return None
    ctx.product_id = ctx.product_id or resolved
    return builder(ctx)
