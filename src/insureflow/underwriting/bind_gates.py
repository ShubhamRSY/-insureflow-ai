"""Shared quote-issuance and bind gates (eligibility, OFAC, APS, E&S, facultative)."""

from __future__ import annotations

from typing import Any

from insureflow.billing.plan import current_plan
from insureflow.models.submissions import SubmissionBundle
from insureflow.underwriting.personal_lines import _blob


def quote_issuance_error(
    summary: dict[str, Any] | None,
    *,
    action: str,
    override_reason: str = "",
) -> str | None:
    """Block Quote/Approve when the system quote is ineligible / unfiled."""
    if str(action or "").lower() not in {"quote", "approve"}:
        return None
    quote = (summary or {}).get("quote") or {}
    if quote.get("eligible", True) is not False:
        return None
    plan = current_plan()
    reasons = quote.get("ineligibility_reasons") or quote.get("ineligible_reasons") or []
    detail = "; ".join(str(r) for r in reasons[:4]) if reasons else "quote marked ineligible"
    if plan.require_carrier_book:
        return f"Cannot quote an ineligible or unfiled premium on this plan ({detail})"
    if not (override_reason or "").strip():
        return f"Quote is ineligible ({detail}). Choose No quote, or provide override_reason on Pilot only."
    return None


def _doc_types(bundle: SubmissionBundle) -> set[str]:
    types: set[str] = set()
    for doc in list(bundle.unstructured or []) + list(bundle.supplemental or []):
        types.add(str(getattr(doc, "document_type", "") or "").lower())
    return types


def life_evidence_holds(bundle: SubmissionBundle, quote_meta: dict[str, Any] | None) -> list[str]:
    meta = dict(quote_meta or {})
    medical = dict(meta.get("medical") or {})
    blob = _blob(bundle)
    types = _doc_types(bundle)
    holds: list[str] = []
    if medical.get("require_aps"):
        if "aps_records" not in types and not re_search(blob, r"aps\s+(?:received|complete|on file)|attending physician statement\s+(?:received|attached)"):
            holds.append("APS required before bind — not on file (flag is not an order)")
    if medical.get("require_paramed"):
        if "medical_exam" not in types and not re_search(blob, r"paramed(?:ical)?\s+(?:complete|received|done)|examone\s+complete"):
            holds.append("Paramedical exam required before bind — not fulfilled")
    if meta.get("facultative_required") or (meta.get("life_reinsurance") or {}).get("facultative_required"):
        if not re_search(blob, r"facultative\s+(?:placed|bound|accepted)|reinsurer\s+accepted"):
            holds.append("Facultative reinsurance not placed — cannot bind jumbo")
    ofac = meta.get("ofac") or {}
    if ofac.get("ofac_hits") or meta.get("ofac_hits"):
        holds.append("OFAC hit — cannot bind")
    elif ofac.get("ofac_incomplete") or (ofac.get("ofac_cleared") is False and not ofac.get("ofac_hits") and meta.get("ofac_cleared") is False):
        if ofac.get("ofac_incomplete"):
            holds.append("OFAC not run — named insured / applicant missing")
    sl = meta.get("surplus_lines") or {}
    if sl.get("can_bind") is False:
        missing = sl.get("missing_stamping_docs") or []
        holds.append("E&S/stamping documents missing: " + ", ".join(str(m) for m in missing[:4]))
    return holds


def commercial_bind_holds(quote_meta: dict[str, Any] | None) -> list[str]:
    meta = dict(quote_meta or {})
    holds: list[str] = []
    ofac = meta.get("ofac") or {}
    if ofac.get("ofac_hits") or meta.get("ofac_hits"):
        holds.append("OFAC hit — cannot bind")
    sl = meta.get("surplus_lines") or {}
    if sl.get("can_bind") is False:
        missing = sl.get("missing_stamping_docs") or []
        holds.append("E&S/stamping documents missing: " + ", ".join(str(m) for m in missing[:4]))
    if meta.get("mvr_required") and meta.get("mvr_cleared") is False:
        from insureflow.billing.plan import current_plan

        if current_plan().require_live_oracles:
            holds.append("Commercial auto MVR not cleared — cannot bind")
    return holds


def re_search(blob: str, pattern: str) -> bool:
    import re

    return bool(re.search(pattern, blob or "", re.I))
