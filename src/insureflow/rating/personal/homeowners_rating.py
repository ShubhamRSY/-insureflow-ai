"""HO-3 filing-style homeowners rating."""

from __future__ import annotations

from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.personal.manuals import _band_factor, homeowners_manual
from insureflow.underwriting.personal_lines import extract_home_factors


def rate_homeowners(
    bundle: SubmissionBundle,
    *,
    state: str = "",
    deductible: float = 1000.0,
) -> QuoteResult:
    manual = homeowners_manual()
    factors = extract_home_factors(bundle)
    dwelling = factors.dwelling_limit
    eligible = True
    reasons: list[str] = []

    if dwelling <= 0:
        return QuoteResult(
            bundle_id=bundle.bundle_id,
            line=InsuranceLine.PERSONAL_HOMEOWNERS,
            base_premium=0.0,
            adjusted_premium=0.0,
            eligible=False,
            ineligibility_reasons=["Dwelling coverage amount missing — cannot rate"],
            metadata={"filing_id": manual.get("filing_id"), "tiv_unknown": True},
        )
    elig = manual.get("eligibility") or {}
    if factors.prior_claims > int(elig.get("max_claims_5yr", 3)):
        eligible = False
        reasons.append("Claims history exceeds filing eligibility")
    if dwelling > float(elig.get("max_dwelling", 2_500_000)):
        eligible = False
        reasons.append("Dwelling above maximum for this filing")

    construction = factors.construction or "frame"
    if construction not in ("frame", "masonry", "superior"):
        construction = "masonry" if construction in ("brick", "steel") else "frame"
    ppc = str(min(max(factors.protection_class or 5, 1), 10))
    base_table = (manual.get("base_rate_per_1000") or {}).get(construction) or {}
    base_rate = float(base_table.get(ppc) or base_table.get("5") or 3.0)

    terr = (manual.get("territory") or {}).get(state.upper() if state else "", None)
    if terr is None:
        terr = float((manual.get("territory") or {}).get("DEFAULT", 1.05))
    else:
        terr = float(terr)

    aoi = _band_factor(manual.get("amount_of_insurance_relativity") or [], dwelling, "max")
    year_f = 1.0
    if factors.year_built:
        year_f = _band_factor(manual.get("year_built_factors") or [], float(factors.year_built), "max_year")

    ded_key = "1000"
    for cand in ("500", "1000", "2500", "5000", "10000", "25000"):
        if deductible <= float(cand):
            ded_key = cand
            break
    else:
        ded_key = "25000"
    ded_f = float((manual.get("deductible_factors") or {}).get(ded_key, 1.0))

    feature_f = 1.0
    loads = manual.get("feature_loads") or {}
    feature_parts: list[str] = []
    if factors.has_pool:
        feature_f += float(loads.get("swimming_pool", 0))
        feature_parts.append("pool")
    if factors.has_wood_stove:
        feature_f += float(loads.get("wood_stove", 0))
        feature_parts.append("wood_stove")
    if factors.coastal_or_cat:
        feature_f += float(loads.get("coastal_or_cat", 0))
        feature_parts.append("cat")
    if factors.high_crime_area:
        feature_f += float(loads.get("high_crime", 0))
        feature_parts.append("crime")
    if factors.renovations_recent:
        feature_f += float(loads.get("renovations_credit", 0))
        feature_parts.append("renovation_credit")

    claims_f = 1.0
    for band in sorted(manual.get("claims_surcharge") or [], key=lambda b: int(b.get("min_claims", 0))):
        if factors.prior_claims >= int(band.get("min_claims", 0)):
            claims_f = float(band.get("factor", 1.0))

    base_premium = (dwelling / 1000.0) * base_rate
    adjusted = base_premium * terr * aoi * year_f * ded_f * feature_f * claims_f
    adjusted += float(manual.get("expense_constant", 65.0))
    adjusted = max(adjusted, float(manual.get("minimum_premium", 450.0)))
    adjusted = round(adjusted, 2)

    if factors.coastal_or_cat and dwelling > float(elig.get("refer_coastal_above", 1_500_000)):
        reasons.append("High-value coastal — facultative referral recommended")

    components = [
        RateComponent(name="ho3_base_rate_per_1000", amount=base_rate, basis=f"{construction}/PPC{ppc}"),
        RateComponent(name="territory", amount=terr, basis=state or "DEFAULT"),
        RateComponent(name="amount_of_insurance", amount=aoi, basis="relativity"),
        RateComponent(name="year_built", amount=year_f, basis=str(factors.year_built or "")),
        RateComponent(name="deductible", amount=ded_f, basis=ded_key),
        RateComponent(name="feature_loads", amount=round(feature_f, 3), basis=",".join(feature_parts) or "none"),
        RateComponent(name="claims_surcharge", amount=claims_f, basis=f"{factors.prior_claims}_claims"),
    ]

    meta: dict[str, Any] = {
        "filing_id": manual.get("filing_id"),
        "product": manual.get("product"),
        "rating_engine": "homeowners_filing",
        "construction": construction,
        "protection_class": ppc,
        "dwelling_limit": dwelling,
        "personal_factors": {k: v for k, v in factors.__dict__.items() if k != "findings"},
        "referral_flags": list(reasons),
        "tiv": dwelling,
        "insurance_line": InsuranceLine.PERSONAL_HOMEOWNERS.value,
        "personal_lines": True,
    }

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.PERSONAL_HOMEOWNERS,
        base_premium=round(base_premium, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / (dwelling / 100.0), 4) if dwelling else 0.0,
        eligible=eligible,
        ineligibility_reasons=reasons if not eligible else [],
        metadata=meta,
    )
