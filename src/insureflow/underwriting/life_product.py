"""Life product family classification — term vs permanent vs annuity."""

from __future__ import annotations

import re

LIVE_TERM_PRODUCT_IDS = frozenset(
    {
        "level_term",
        "decreasing_term",
        "mortgage_life",
        "increasing_term",
        "renewable_term",
        "convertible_term",
        "rop_term",
        "group_term_life",
        "credit_life",
    }
)

_FAMILY_BY_ID: dict[str, str] = {
    "level_term": "term",
    "decreasing_term": "term",
    "mortgage_life": "term",
    "increasing_term": "term",
    "renewable_term": "term",
    "convertible_term": "term",
    "rop_term": "term",
    "group_term_life": "term",
    "credit_life": "term",
    "traditional_whole_life": "whole_life",
    "limited_pay_whole_life": "whole_life",
    "single_premium_whole_life": "whole_life",
    "participating_whole_life": "whole_life",
    "non_participating_whole_life": "whole_life",
    "modified_whole_life": "whole_life",
    "graded_guaranteed_issue_whole_life": "whole_life",
    "guaranteed_universal_life": "universal",
    "indexed_universal_life": "universal",
    "variable_universal_life": "variable_universal",
    "current_assumption_universal_life": "universal",
    "pure_endowment": "endowment",
    "full_endowment": "endowment",
    "guaranteed_fixed_endowment": "endowment",
    "single_premium_ulip": "ulip",
    "regular_premium_ulip": "ulip",
    "ulip_type_i": "ulip",
    "ulip_type_ii": "ulip",
    "pension_ulip": "ulip",
    "child_ulip": "ulip",
    "traditional_money_back": "money_back",
    "with_profit_money_back": "money_back",
    "children_money_back": "money_back",
    "immediate_annuity": "annuity",
    "deferred_annuity": "annuity",
    "fixed_annuity": "annuity",
    "variable_annuity": "annuity",
    "indexed_annuity": "annuity",
    "life_annuity": "annuity",
    "joint_survivor_annuity": "annuity",
    "qlac": "annuity",
    "structured_settlement_annuity": "annuity",
    # Bare family ids — callers may select a whole product family without a
    # specific product/coverage. Without these, the regex fallback below sees
    # e.g. "universal_20" and its term-duration pattern matches the "20",
    # misclassifying permanent products as "term" and pricing universal/whole
    # life / etc. as 20-year term (life hard-test H4).
    "term": "term",
    "whole_life": "whole_life",
    "universal": "universal",
    "variable_universal": "variable_universal",
    "endowment": "endowment",
    "ulip": "ulip",
    "money_back": "money_back",
    "annuity": "annuity",
}


def normalize_life_id(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


def classify_life_family(product_id: str | None = None, coverage_id: str | None = None, coverage_name: str | None = None) -> str:
    pid = normalize_life_id(product_id)
    if pid in _FAMILY_BY_ID:
        return _FAMILY_BY_ID[pid]
    blob = f"{pid} {normalize_life_id(coverage_id)} {coverage_name or ''}".lower()
    if re.search(r"\bannuit", blob):
        return "annuity"
    if re.search(r"\bvul\b|variable\s+universal", blob):
        return "variable_universal"
    if re.search(r"\biul\b|indexed\s+universal|\bul\b|universal\s+life", blob):
        return "universal"
    if re.search(r"whole\s+life|ordinary\s+life", blob):
        return "whole_life"
    if re.search(r"endowment", blob):
        return "endowment"
    if re.search(r"ulip|unit.?linked", blob):
        return "ulip"
    if re.search(r"money.?back", blob):
        return "money_back"
    if re.search(r"\bterm\b|(?:^|[_\s-])(?:10|15|20|25|30)(?:$|[_\s-]|\s*-?\s*year|_year)", blob):
        return "term"
    return "unknown"


def is_filed_term_product(product_id: str | None = None, coverage_id: str | None = None, coverage_name: str | None = None) -> bool:
    pid = normalize_life_id(product_id)
    if pid in LIVE_TERM_PRODUCT_IDS:
        return True
    return classify_life_family(product_id, coverage_id, coverage_name) == "term"
