"""General / non-life rating — filed manuals for liability + cyber + marine + fire + travel + home + motor + specialty; the hub is fully live."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.personal.manuals import (
    _band_factor,
    general_cyber_manual,
    general_fire_manual,
    general_home_manual,
    general_liability_manual,
    general_marine_manual,
    general_motor_manual,
    general_specialty_manual,
    general_travel_manual,
)
from insureflow.underwriting.general_product import is_filed_general_product
from insureflow.underwriting.general_uw import (
    _CAR_COMP_RISK_TABLE,
    _CAR_TP_RISK_TABLE,
    _CONCERT_EVENT_RISK_TABLE,
    _CROP_WEATHER_RISK_TABLE,
    _CROP_YIELD_RISK_TABLE,
    _CV_COMP_RISK_TABLE,
    _CV_TP_RISK_TABLE,
    _CYBER_BREACH_RISK_TABLE,
    _CYBER_RANSOM_RISK_TABLE,
    _FIRE_COMM_RISK_TABLE,
    _FIRE_RES_RISK_TABLE,
    _HOME_COMP_RISK_TABLE,
    _HOME_CONTENTS_RISK_TABLE,
    _HOME_STRUCTURE_RISK_TABLE,
    _INSURER_PRIVATE_RISK_TABLE,
    _INSURER_PSU_RISK_TABLE,
    _LIVESTOCK_RISK_TABLE,
    _MARINE_CARGO_RISK_TABLE,
    _MARINE_HULL_RISK_TABLE,
    _MORTGAGE_RISK_TABLE,
    _PET_RISK_TABLE,
    _PI_RISK_TABLE,
    _PRODUCT_RISK_TABLE,
    _PUBLIC_HAZARD_TABLE,
    _REINSURANCE_RISK_TABLE,
    _TITLE_RISK_TABLE,
    _TRAVEL_DOM_RISK_TABLE,
    _TRAVEL_INTL_RISK_TABLE,
    _TW_COMP_RISK_TABLE,
    _TW_TP_RISK_TABLE,
    _WEDDING_RISK_TABLE,
    _claims_severity,
    _risk_class,
    _scaled_money,
    general_product_terms,
)
from insureflow.underwriting.personal_lines import _blob, _int_field

_RISK_TABLES: dict[str, Sequence[tuple[str, float, tuple[str, ...]]]] = {
    "professional_indemnity_gi": _PI_RISK_TABLE,
    "public_liability_gi": _PUBLIC_HAZARD_TABLE,
    "product_liability_gi": _PRODUCT_RISK_TABLE,
    "cyber_data_breach": _CYBER_BREACH_RISK_TABLE,
    "cyber_ransomware": _CYBER_RANSOM_RISK_TABLE,
    "marine_cargo": _MARINE_CARGO_RISK_TABLE,
    "marine_hull": _MARINE_HULL_RISK_TABLE,
    "fire_residential": _FIRE_RES_RISK_TABLE,
    "fire_commercial": _FIRE_COMM_RISK_TABLE,
    "travel_domestic": _TRAVEL_DOM_RISK_TABLE,
    "travel_international": _TRAVEL_INTL_RISK_TABLE,
    "home_structure": _HOME_STRUCTURE_RISK_TABLE,
    "home_contents": _HOME_CONTENTS_RISK_TABLE,
    "home_comprehensive": _HOME_COMP_RISK_TABLE,
    "car_tp": _CAR_TP_RISK_TABLE,
    "car_comprehensive": _CAR_COMP_RISK_TABLE,
    "tw_tp": _TW_TP_RISK_TABLE,
    "tw_comprehensive": _TW_COMP_RISK_TABLE,
    "cv_tp": _CV_TP_RISK_TABLE,
    "cv_comprehensive": _CV_COMP_RISK_TABLE,
    "crop_yield": _CROP_YIELD_RISK_TABLE,
    "crop_weather": _CROP_WEATHER_RISK_TABLE,
    "livestock_cattle": _LIVESTOCK_RISK_TABLE,
    "pet_insurance": _PET_RISK_TABLE,
    "wedding_insurance": _WEDDING_RISK_TABLE,
    "concert_event_insurance": _CONCERT_EVENT_RISK_TABLE,
    "title_insurance_gi": _TITLE_RISK_TABLE,
    "mortgage_insurance_gi": _MORTGAGE_RISK_TABLE,
    "insurer_psu": _INSURER_PSU_RISK_TABLE,
    "insurer_private": _INSURER_PRIVATE_RISK_TABLE,
    "reinsurance_treaty": _REINSURANCE_RISK_TABLE,
}

_GENERAL_MANUALS: tuple[dict[str, Any], ...] = (
    general_liability_manual(),
    general_cyber_manual(),
    general_marine_manual(),
    general_fire_manual(),
    general_travel_manual(),
    general_home_manual(),
    general_motor_manual(),
    general_specialty_manual(),
)


def _rate_filed(
    bundle: SubmissionBundle,
    product_id: str,
    coverage_id: str | None,
    coverage_name: str | None,
    state: str,
    deductible: float,
    terms: dict[str, Any],
    manual: dict[str, Any],
) -> QuoteResult | None:
    """Rate a product that has a filed entry in the general liability manual."""
    conf = (manual.get("products") or {}).get(product_id)
    if not conf:
        return None
    blob = _blob(bundle)
    elig = manual.get("eligibility") or {}
    min_limit = float(elig.get("min_limit", 1_000_000))
    max_limit = float(elig.get("max_limit", 50_000_000))
    min_exposure = float(elig.get("min_declared_exposure", 100_000))
    unit = float(conf.get("unit", 1_000_000))
    rate_basis = conf.get("rate_basis") or "limit"

    limit = _scaled_money(blob, *(conf.get("limit_labels") or []))
    exposure = _scaled_money(blob, *(conf.get("exposure_labels") or []))
    risk_table = _RISK_TABLES.get(product_id)
    risk_class = _risk_class(blob, risk_table)[0] if risk_table else "low"
    severity = _claims_severity(blob) or "none"
    cov_conf = ((conf.get("coverages") or {}).get(coverage_id or "default")) or ((conf.get("coverages") or {}).get("default")) or {}
    base_rate = float(cov_conf.get("base_rate", 0.0))
    expense_constant = float(cov_conf.get("expense_constant", 0.0))
    min_premium = float(cov_conf.get("min_premium", 0.0))
    duration = (
        _int_field(blob, "trip duration", "duration days", "trip days", "number of days", "duration")
        if conf.get("duration_factors")
        else None
    )
    duration_f = _band_factor(conf.get("duration_factors") or [], float(duration or 0.0), "max_days")

    reasons: list[str] = []
    eligible = True
    if limit <= 0:
        eligible = False
        reasons.append("Indemnity limit not declared — cannot rate")
    if exposure < min_exposure:
        eligible = False
        reasons.append(f"{conf.get('exposure_label', 'Declared exposure')} below {min_exposure:,.0f} minimum")
    if limit > max_limit:
        eligible = False
        reasons.append("Indemnity limit above filed maximum")
    if limit < min_limit:
        eligible = False
        reasons.append("Indemnity limit below filed minimum")
    cap = float(conf.get("limit_exposure_ratio_cap") or 0.0)
    ratio = limit / exposure if limit > 0 and exposure > 0 else 0.0
    if cap > 0 and ratio > cap:
        eligible = False
        reasons.append(f"Indemnity limit {ratio:.2f}x exposure exceeds the {cap:.1f}x filing cap")

    if not eligible or limit <= 0:
        base_premium = 0.0
        adjusted_premium = 0.0
        components: list[RateComponent] = []
        rate_100 = 0.0
    else:
        basis_units = limit / unit if rate_basis == "limit" else exposure / unit
        base_premium = round(base_rate * basis_units, 2)
        risk_f = float((conf.get("risk_class_factors") or {}).get(risk_class, 1.0))
        limit_f = _band_factor(conf.get("limit_factors") or [], limit, "max_limit")
        ded_f = _band_factor(conf.get("deductible_factors") or [], deductible, "max_deductible")
        claims_f = float((conf.get("claims_factors") or {}).get(severity, 1.0))
        adjusted_premium = base_premium * risk_f * limit_f * claims_f * ded_f * duration_f + expense_constant
        adjusted_premium = max(adjusted_premium, min_premium)
        adjusted_premium = round(adjusted_premium, 2)
        components = [
            RateComponent(name="liability_base", amount=base_premium, basis=f"{rate_basis} {basis_units:,.1f} units"),
            RateComponent(name="risk_class", amount=risk_f, basis=risk_class),
            RateComponent(name="limit_band", amount=limit_f, basis=f"limit={limit:,.0f}"),
            RateComponent(name="deductible", amount=ded_f, basis=f"deductible={deductible:,.0f}"),
            RateComponent(name="claims_record", amount=claims_f, basis=severity),
            RateComponent(name="expense_constant", amount=expense_constant, basis="per policy"),
        ]
        if conf.get("duration_factors"):
            components.insert(5, RateComponent(name="trip_duration", amount=duration_f, basis=f"days={duration or 0}"))
        rate_100 = round(adjusted_premium / (exposure / 100.0), 4) if exposure > 0 else 0.0

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.GENERAL,
        base_premium=base_premium,
        adjusted_premium=adjusted_premium,
        schedule_modifications=components,
        rate_per_100_tiv=rate_100,
        eligible=eligible,
        ineligibility_reasons=reasons if not eligible else [r for r in reasons if "referral" in r.lower()],
        metadata={
            "filing_id": manual.get("filing_id"),
            "product": manual.get("product"),
            "serff_tracking": manual.get("serff_tracking"),
            "rating_engine": manual.get("rating_engine") or "general_filing",
            "insurance_line": "general",
            "product_id": product_id,
            "coverage_id": coverage_id or "",
            "coverage_name": coverage_name or "",
            "state": state,
            "filed": True,
            "risk_class": risk_class,
            "exposure": exposure,
            "exposure_key": conf.get("exposure_key"),
            "exposure_label": conf.get("exposure_label"),
            "indemnity_limit": limit,
            "exposure_limit_ratio": round(ratio, 3) if ratio else None,
            "claims_severity": severity,
            "duration_days": duration,
            **terms,
        },
    )


def rate_general(
    bundle: SubmissionBundle,
    *,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
    product_id: str | None = None,
    state: str = "",
    deductible: float = 0.0,
) -> QuoteResult:
    pid = str(product_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    terms = general_product_terms(pid, coverage_id)
    for manual in _GENERAL_MANUALS:
        filed_result = _rate_filed(bundle, pid, coverage_id, coverage_name, state, deductible, terms, manual)
        if filed_result is not None:
            return filed_result
    meta: dict[str, Any] = {
        "rating_engine": "catalog_only",
        "insurance_line": "general",
        "product_id": pid,
        "coverage_id": coverage_id or "",
        "coverage_name": coverage_name or "",
        "state": state,
        "filed": is_filed_general_product(pid),
        **terms,
    }
    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.GENERAL,
        base_premium=0.0,
        adjusted_premium=0.0,
        eligible=False,
        ineligibility_reasons=[
            f"{terms.get('benefit_type') or 'general'} is catalog-only until a filed general rate manual is imported — will not invent premium",
        ],
        metadata=meta,
    )
