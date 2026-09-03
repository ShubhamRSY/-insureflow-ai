"""Commercial Property & Business Interruption — dedicated logic path.

Unlike the other five products, property's pricing is a well-tested
multi-factor COPE/ISO/territory-relativity engine shared by every
non-specialty commercial line in ``insureflow.rating.engine`` — not a
simple table lookup. Re-deriving that math here would risk exactly the
divergence the life/health dedicated paths warn about (the same submission
silently pricing differently depending on which path runs). Instead this
module owns two real overlays applied to the already-computed,
already-trusted QuoteResult:

1. State law: valued policy law, named storm percentage deductibles, and
   wind-pool availability — three genuine state doctrines the generic
   engine has never applied to any commercial property quote.
2. The real property coinsurance penalty clause
   (``insureflow.underwriting.policy_architecture.coinsurance_penalty``,
   already implemented elsewhere in this codebase but never actually
   computed against a submission's declared property value vs. its
   purchased limit) — genuine, quantified underinsurance exposure, not a
   qualitative flag.
"""

from __future__ import annotations

from insureflow.commercial.lobs.state_law import property_state_row
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import QuoteResult
from insureflow.underwriting.personal_lines import _money, _pct_field

PRODUCT_ID = "property_bi"
LOGIC_PATH = "insureflow.commercial.lobs.property_bi"
PRODUCT_LABEL = "Commercial Property & Business Interruption"

# ISO-standard commercial property coinsurance clause, used only when the
# submission doesn't state its own coinsurance percentage.
DEFAULT_COINSURANCE_PCT = 80.0


def _declared_property_value(bundle: SubmissionBundle) -> float:
    if not bundle.structured:
        return 0.0
    total = 0.0
    for loc in bundle.structured.locations or []:
        total += float(loc.building_value or 0.0) + float(loc.contents_value or 0.0)
    return total


def _purchased_limit(bundle: SubmissionBundle) -> tuple[float, float | None]:
    """Returns (insured_limit, coinsurance_pct or None) from structured coverages."""
    if bundle.structured:
        limit_total = 0.0
        coinsurance_pct: float | None = None
        for cov in bundle.structured.coverages or []:
            if cov.limit_amount and cov.limit_amount > 0:
                limit_total += float(cov.limit_amount)
            if coinsurance_pct is None and cov.coinsurance_pct is not None:
                coinsurance_pct = float(cov.coinsurance_pct)
        if limit_total > 0:
            return limit_total, coinsurance_pct
    blob = " ".join(u.raw_text or "" for u in (bundle.unstructured or []))
    limit = _money(blob, "coverage limit", "insured limit", "limit of insurance", "policy limit", "building limit")
    pct = _pct_field(blob, "coinsurance")
    return limit, pct


def apply_coinsurance_check(result: QuoteResult, bundle: SubmissionBundle) -> QuoteResult:
    """Compute and surface the real coinsurance penalty, when computable.

    Never invents a property value or purchased limit — a submission that
    doesn't state both is left untouched (no fabricated underinsurance
    finding).
    """
    from insureflow.underwriting.policy_architecture import coinsurance_penalty

    property_value = _declared_property_value(bundle)
    insured_limit, coinsurance_pct = _purchased_limit(bundle)
    if property_value <= 0 or insured_limit <= 0:
        return result

    assumed_default = coinsurance_pct is None
    pct = coinsurance_pct if coinsurance_pct is not None else DEFAULT_COINSURANCE_PCT
    check = coinsurance_penalty(insured_limit=insured_limit, coinsurance_pct=pct, property_value=property_value)
    result.metadata["coinsurance_check"] = {**check, "coinsurance_pct_assumed": assumed_default, "coinsurance_pct_used": pct}

    conditions = list(result.metadata.get("conditions") or [])
    if check["penalty_applies"]:
        note = " (ISO-standard 80% clause assumed — no coinsurance percentage stated)" if assumed_default else ""
        conditions.append(
            f"Coinsurance penalty: insured to {check['compliance_ratio']:.0%} of the required "
            f"${check['required_coverage']:,.0f} ({pct:.0f}% coinsurance value) — {check['penalty_pct']:.0%} "
            f"of every loss would be uninsured{note}"
        )
        result.metadata["conditions"] = conditions
    return result


def apply_state_law_overlay(result: QuoteResult, issue_state: str) -> QuoteResult:
    """Stamp property state-law facts onto an already-priced QuoteResult.

    Mutates and returns `result` in place; safe to call unconditionally —
    a no-op state (no VPL/named-storm/wind-pool facts) leaves the quote
    untouched beyond the (empty) state_rules_applied stamp.
    """
    state = (issue_state or "").upper()[:2]
    row = property_state_row(state)
    result.metadata["lob_logic_path"] = LOGIC_PATH
    result.metadata["state_rules_applied"] = {"issue_state": state, **row}

    conditions = list(result.metadata.get("conditions") or [])
    if row.get("valued_policy_law"):
        conditions.append(
            f"{state} is a Valued Policy Law state — a total loss of covered real property pays the full stated policy value, regardless of a lower actual-cash-value appraisal at time of loss"
        )
    if row.get("named_storm_pct_deductible"):
        lo, hi = row.get("named_storm_pct_range", (1.0, 5.0))
        conditions.append(
            f"{state} applies a named-storm/hurricane percentage deductible ({lo:.0f}%-{hi:.0f}% of building value, carrier-filed) in wind-exposed counties, in place of the standard peril deductible"
        )
    if row.get("wind_pool_available"):
        conditions.append(f"{state} operates a residual-market wind pool/FAIR Plan — available as a market of last resort if this risk cannot be placed voluntarily")
    result.metadata["conditions"] = conditions
    return result
