"""Underwriting gates for commercial products that still rate on a leaf filing.

The leaf filing is the rate. This module decides whether that rate is
writable. A missing exposure basis declines the file. A disclosed hazard
that is not itself a decline becomes a bind condition. Nothing here
invents a second loss cost.
"""

from __future__ import annotations

from collections.abc import Callable

from insureflow.commercial.lobs.base import CommercialProductContext
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import QuoteResult
from insureflow.underwriting.personal_lines import _blob

LOGIC_PATH = "insureflow.commercial.lobs.gates"


def _text(bundle: SubmissionBundle) -> str:
    return _blob(bundle).lower()


def _revenue(bundle: SubmissionBundle) -> float:
    fin = bundle.structured.financial if bundle.structured else None
    return float(getattr(fin, "annual_revenue", 0) or 0)


def _employees(bundle: SubmissionBundle) -> int:
    fin = bundle.structured.financial if bundle.structured else None
    n = int(getattr(fin, "employee_count", 0) or 0)
    if n > 0:
        return n
    import re

    m = re.search(r"(?:employees?|fte|headcount)\s*[:=]?\s*(\d{1,6})", _text(bundle))
    return int(m.group(1)) if m else 0


def _locs(bundle: SubmissionBundle):
    return list(bundle.structured.locations or []) if bundle.structured else []


def _has(text: str, *needles: str) -> bool:
    return any(n in text for n in needles)


def _decline(quote: QuoteResult, reason: str) -> None:
    quote.eligible = False
    quote.base_premium = 0.0
    quote.adjusted_premium = 0.0
    quote.rate_per_100_tiv = 0.0
    reasons = list(quote.ineligibility_reasons or [])
    if reason not in reasons:
        reasons.append(reason)
    quote.ineligibility_reasons = reasons


def _condition(quote: QuoteResult, note: str) -> None:
    meta = dict(quote.metadata or {})
    conds = list(meta.get("conditions") or [])
    if note not in conds:
        conds.append(note)
    meta["conditions"] = conds
    quote.metadata = meta


def _bi(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    bi = sum(float(loc.bi_value or 0) for loc in _locs(bundle))
    if bi <= 0 and _revenue(bundle) <= 0 and not _has(text, "gross earnings", "business income", "indemnity"):
        _decline(quote, "Business-income exposure missing — will not rate business interruption on building value")
        return
    if not _has(text, "12 month", "18 month", "24 month", "indemnity period", "period of restoration"):
        _condition(quote, "Indemnity period not stated — confirm the period of restoration before bind")


def _ocean(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "vessel", "hull", "cargo", "p&i", "p & i"):
        _decline(quote, "No vessel, cargo, or P&I exposure — ocean marine cannot be rated on a building TIV")


def _equipment(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "boiler", "machinery", "equipment breakdown", "inspection certificate", "jurisdictional inspection"):
        _decline(quote, "No scheduled equipment or inspection — equipment breakdown cannot be rated on building TIV")


def _flood(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if _has(text, "severe repetitive", "repetitive loss"):
        _decline(quote, "Severe repetitive flood loss disclosed — outside flood appetite")
        return
    if not _has(text, "flood zone", "zone ae", "zone ve", "zone x", "elevation certificate", "bfe"):
        _condition(quote, "FEMA flood zone not on the submission — order the current zone and elevation before bind")


def _quake(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    construction = " ".join((loc.construction_type or "") for loc in _locs(bundle)).lower()
    blob = f"{construction} {text}"
    if _has(blob, "unreinforced", "urm", "masonry unreinforced"):
        _decline(quote, "Unreinforced masonry disclosed — earthquake appetite requires a retrofit or a different construction class")
        return
    if not construction.strip() and not _has(text, "retrofit", "seismic"):
        _condition(quote, "Construction and seismic retrofit not stated — earthquake pricing is not bindable until they are")


def _ordinance(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    years = [loc.year_built for loc in _locs(bundle) if loc.year_built]
    if not years and not _has(text, "year built", "ordinance"):
        _condition(quote, "Year built not stated — undamaged-portion and increased-cost-of-construction exposure cannot be sized")


def _rent(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "rent roll", "rental income", "monthly rent", "loss of rents"):
        _decline(quote, "No rent roll or rental income — loss-of-rents cannot be rated on building value")


def _dic(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "attachment", "underlying", "primary policy", "excess flood", "excess quake"):
        _decline(quote, "No primary policy or attachment point — DIC / excess flood is not writable without the underlying")


def _pollution(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if _has(text, "superfund", "npl site", "known release", "open remediation"):
        _decline(quote, "Known contamination or an open remediation disclosed — pollution is a refer-to-decline until the site is closed")
        return
    if not _has(text, "phase i", "phase ii", "esa", "underground storage", "ust"):
        _condition(quote, "No Phase I/II or tank inventory — pollution cannot be bound on an unassessed site")


def _liquor(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "alcohol", "liquor", "dram", "bar sales", "on-premises"):
        _decline(quote, "No alcohol exposure disclosed — liquor liability will not be rated on premises GL")
        return
    if not _has(text, "tips", "servsafe", "server training"):
        _condition(quote, "No server-training program (TIPS or equivalent) disclosed — confirm before bind")


def _media(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "publisher", "broadcast", "content", "defamation", "intellectual property clearance"):
        _decline(quote, "No content or publication exposure — media liability cannot be rated as premises GL")


def _census(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if _employees(bundle) <= 0 and not _has(text, "census", "enrolled", "participants"):
        _decline(quote, "No employee census — group benefits cannot be rated on revenue")


def _overhead(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "overhead", "fixed expense", "continuing expense"):
        _decline(quote, "No fixed-expense schedule — business overhead expense is not writable")


def _political(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "host country", "country of risk", "political risk"):
        _decline(quote, "No host country — political risk cannot be rated on domestic TIV")


def _rw(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "enterprise value", "deal value", "acquisition", "transaction"):
        _decline(quote, "No transaction — representations and warranties insurance is not writable without a deal")


def _legal(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if _revenue(bundle) <= 0 and not _has(text, "legal expense", "matter"):
        _decline(quote, "No revenue or matter — legal expense has no exposure basis")
        return
    if not _has(text, "matter", "claim type", "defense"):
        _condition(quote, "Matter type not stated — legal-expense appetite depends on the class of dispute")


def _construction(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "contract value", "project value", "completed value", "ocip", "ccip", "wrap-up"):
        _decline(quote, "No project or contract value — course-of-construction cannot be rated on an existing building")


def _aviation(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "aircraft", "hull", "n-number", "faa", "airport"):
        _decline(quote, "No aircraft schedule — aviation cannot be rated on a building TIV")


def _event(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "event date", "attendance", "concert", "venue", "cancellation"):
        _decline(quote, "No event — event cancellation cannot be rated on annual revenue")


def _ip(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "patent", "trademark", "copyright", "ip schedule"):
        _decline(quote, "No scheduled intellectual property — IP insurance has no exposure")


def _kidnap(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if _employees(bundle) <= 0:
        _decline(quote, "No headcount — kidnap and ransom is rated on people, not revenue")
        return
    if not _has(text, "travel", "expat", "foreign"):
        _condition(quote, "Foreign-travel pattern not stated — K&R limit should follow the people actually exposed")


def _terrorism(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    tiv = sum(float(loc.building_value or 0) + float(loc.contents_value or 0) for loc in _locs(bundle))
    if tiv <= 0 and not _has(text, "tria", "terrorism limit"):
        _decline(quote, "No property values or terrorism limit")
        return
    _condition(quote, "Confirm the TRIA disclosure and the certified-act sublimit before bind")


def _recall(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "recall", "sku", "product line", "batch"):
        _decline(quote, "No product identified — product recall has no exposure")


def _supply(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "supplier", "tier 1", "tier-1", "contingent"):
        _decline(quote, "No supplier dependency — supply-chain coverage is not writable on the insured's own building")


def _crop(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "acre", "crop", "bushel", "yield"):
        _decline(quote, "No acreage or crop — crop insurance cannot be rated on commercial TIV")


def _livestock(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "cattle", "head", "herd", "livestock", "bloodstock"):
        _decline(quote, "No animals scheduled — livestock coverage has no exposure")


def _captive(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "captive", "domicile", "feasibility"):
        _decline(quote, "No captive domicile or feasibility study — a captive is not a monoline property quote")


def _fronting(quote: QuoteResult, bundle: SubmissionBundle, text: str) -> None:
    if not _has(text, "self-insured retention", "sir", "fronting"):
        _decline(quote, "No retention or fronting agreement — SIR/fronting cannot be rated as a primary policy")


Rule = Callable[[QuoteResult, SubmissionBundle, str], None]

RULES: dict[str, Rule] = {
    "business_interruption": _bi,
    "ocean_marine": _ocean,
    "equipment_breakdown": _equipment,
    "flood_commercial": _flood,
    "earthquake_commercial": _quake,
    "ordinance_or_law": _ordinance,
    "rent_loss_of_rents": _rent,
    "dic_excess_flood": _dic,
    "pollution": _pollution,
    "liquor_liability": _liquor,
    "media_liability": _media,
    "group_health": _census,
    "group_life": _census,
    "group_disability": _census,
    "voluntary_benefits": _census,
    "business_overhead": _overhead,
    "political_risk": _political,
    "representations_warranties": _rw,
    "legal_expense": _legal,
    "construction": _construction,
    "aviation": _aviation,
    "event_insurance": _event,
    "intellectual_property": _ip,
    "kidnap_ransom": _kidnap,
    "terrorism": _terrorism,
    "product_recall": _recall,
    "supply_chain": _supply,
    "crop_insurance": _crop,
    "livestock_bloodstock": _livestock,
    "captive_insurance": _captive,
    "sir_fronting": _fronting,
}

PRODUCT_IDS = frozenset(RULES)


def apply_leaf_underwriting(quote: QuoteResult, bundle: SubmissionBundle, product_id: str | None) -> QuoteResult:
    pid = (product_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    rule = RULES.get(pid)
    if rule is None:
        return quote
    meta = dict(quote.metadata or {})
    meta["lob_logic_path"] = LOGIC_PATH
    meta["product_id"] = pid
    quote.metadata = meta
    if quote.eligible:
        rule(quote, bundle, _text(bundle))
    return quote


def build_quote(ctx: CommercialProductContext) -> QuoteResult:
    from insureflow.rating.leaf_filings import rate_leaf_filing

    rated = rate_leaf_filing(
        ctx.bundle,
        ctx.memo,
        ctx.product_id,
        state=ctx.issue_state,
        schedule_mod_pct=ctx.schedule_mod_pct,
        market_mod_pct=ctx.market_mod_pct,
    )
    if rated is None:
        return QuoteResult(
            bundle_id=ctx.bundle.bundle_id,
            line=ctx.line,
            eligible=False,
            ineligibility_reasons=[f"No leaf filing for {ctx.product_id}"],
            metadata={"lob_logic_path": LOGIC_PATH, "product_id": ctx.product_id},
        )
    return apply_leaf_underwriting(rated, ctx.bundle, ctx.product_id)
