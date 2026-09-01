"""Health LOB logic paths — explicit per-LOB / per-Product / per-Coverage code.

Mirrors insureflow.life.lobs: every Line of Business, every Product, and
every Coverage option owns a dedicated logic path in code. State rules are
applied INSIDE each path (not as a bolt-on layer) via
insureflow.health.lobs.state_law, which wraps the existing US health
regulatory data (insureflow/regulatory/data/health.yaml).

Adding a new product = create an insureflow.health.lobs.<lob>.<product>
module following the same pattern (DEFAULT_STATE_RULES/STATE_RULES ->
underwrite_<product>(ctx) -> LobOutcome -> build_quote(ctx) -> QuoteResult)
and register it in PRODUCT_LOGIC_PATHS.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Callable, cast

from insureflow.health.lobs.base import HealthProductContext as HealthProductContext  # explicit re-export
from insureflow.health.lobs.base import LobOutcome as LobOutcome
from insureflow.health.lobs.base import QuoteResult as QuoteResult
from insureflow.health.lobs.critical_illness import CRITICAL_ILLNESS_LOGIC_PATHS
from insureflow.health.lobs.disability import DISABILITY_LOGIC_PATHS
from insureflow.health.lobs.family import FAMILY_LOGIC_PATHS
from insureflow.health.lobs.group import GROUP_LOGIC_PATHS
from insureflow.health.lobs.individual import INDIVIDUAL_LOGIC_PATHS
from insureflow.health.lobs.personal_accident import PERSONAL_ACCIDENT_LOGIC_PATHS
from insureflow.health.lobs.senior import SENIOR_LOGIC_PATHS
from insureflow.health.lobs.topup import TOPUP_LOGIC_PATHS

# Explicit registry: normalized product id -> module path owning its logic.
PRODUCT_LOGIC_PATHS: dict[str, str] = {
    **INDIVIDUAL_LOGIC_PATHS,
    **FAMILY_LOGIC_PATHS,
    **CRITICAL_ILLNESS_LOGIC_PATHS,
    **SENIOR_LOGIC_PATHS,
    **GROUP_LOGIC_PATHS,
    **TOPUP_LOGIC_PATHS,
    **PERSONAL_ACCIDENT_LOGIC_PATHS,
    **DISABILITY_LOGIC_PATHS,
}

# Fallback matching when the caller passes only a coverage id / free-text name.
# Order matters — most specific patterns first.
_COVERAGE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"bronze|silver|gold|platinum|marketplace|exchange(?!.*off)", re.I), "aca_marketplace_plan"),
    (re.compile(r"off[_\s-]?exchange|off[_\s-]?market", re.I), "off_exchange_major_medical"),
    (re.compile(r"family[_\s-]?(health|floater|plan)", re.I), "family_health_plan"),
    (re.compile(r"cancer|cardiac|diabetes|kidney|disease[_\s-]?specific", re.I), "disease_specific_critical_illness"),
    (re.compile(r"critical[_\s-]?illness|\bci\b", re.I), "critical_illness_standalone"),
    (re.compile(r"medigap|medicare[_\s-]?supplement|plan[_\s-]?[afgn]\b", re.I), "medicare_supplement"),
    (re.compile(r"medicare[_\s-]?advantage|part[_\s-]?c", re.I), "medicare_advantage"),
    (re.compile(r"small[_\s-]?group", re.I), "small_group_health"),
    (re.compile(r"large[_\s-]?group|self[_\s-]?funded|erisa", re.I), "large_group_health"),
    (re.compile(r"super[_\s-]?top.?up|super[_\s-]?gap", re.I), "supplemental_gap_coverage"),
    (re.compile(r"top.?up|gap[_\s-]?coverage", re.I), "supplemental_gap_coverage"),
    (re.compile(r"add\b|accidental[_\s-]?death|dismemberment|personal[_\s-]?accident|\bpa\b", re.I), "add_accident_indemnity"),
    (re.compile(r"short[_\s-]?term[_\s-]?disability|\bstd\b", re.I), "short_term_disability"),
    (re.compile(r"long[_\s-]?term[_\s-]?disability|\bltd\b|disability[_\s-]?income", re.I), "long_term_disability"),
]


def normalize_id(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


@lru_cache(maxsize=None)
def _load_builder(module_path: str) -> Callable[[HealthProductContext], Any] | None:
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


def run_product_logic(ctx: HealthProductContext) -> QuoteResult | None:
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
    return cast(QuoteResult, builder(ctx))
