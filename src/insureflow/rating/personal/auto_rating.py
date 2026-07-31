"""Personal auto PP filing-style rating."""

from __future__ import annotations

from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.personal.manuals import _band_factor, auto_manual
from insureflow.underwriting.personal_lines import extract_auto_factors


def _driver_factor(manual: dict[str, Any], age: int | None, years: int | None) -> float:
    age_v = age if age is not None else 35
    years_v = years if years is not None else 5
    chosen = 1.0
    for band in manual.get("driver_class") or []:
        max_age = band.get("max_age")
        min_years = int(band.get("min_years") or 0)
        if max_age is not None and age_v > int(max_age):
            continue
        if years_v < min_years:
            continue
        chosen = float(band.get("factor", 1.0))
        # Prefer tighter match: keep last matching band in ordered list
    return chosen


def rate_personal_auto(bundle: SubmissionBundle, *, state: str = "") -> QuoteResult:
    manual = auto_manual()
    factors = extract_auto_factors(bundle)
    elig = manual.get("eligibility") or {}
    reasons: list[str] = []
    eligible = True

    blob_viol = factors.violations
    if bool(elig.get("dui_decline")) and blob_viol >= 0:
        # DUI detected in extract via violation count patterns; check findings text
        if any("dui" in (f.description or "").lower() or "dui" in (f.title or "").lower() for f in factors.findings):
            eligible = False
            reasons.append("DUI/DWI — declined per filing")
    # Also check raw for dui
    from insureflow.underwriting.personal_lines import _blob

    if bool(elig.get("dui_decline")) and ("dui" in _blob(bundle) or "dwi" in _blob(bundle)):
        eligible = False
        if "DUI/DWI — declined per filing" not in reasons:
            reasons.append("DUI/DWI — declined per filing")

    if factors.driver_age is not None and factors.driver_age < int(elig.get("min_driver_age", 18)):
        eligible = False
        reasons.append("Driver under minimum age")
    if factors.violations > int(elig.get("max_violations", 3)):
        eligible = False
        reasons.append("Violation count exceeds eligibility")

    coverages = manual.get("coverages") or {}
    bi = float((coverages.get("bi_pd") or {}).get("base", 420))
    comp = float((coverages.get("comp") or {}).get("base", 180))
    coll = float((coverages.get("coll") or {}).get("base", 320))
    um = float((coverages.get("um_uim") or {}).get("base", 0))
    med = float((coverages.get("medpay") or {}).get("base", 0))
    package_base = bi + comp + coll + um + med

    terr = (manual.get("territory") or {}).get(state.upper() if state else "", None)
    terr = float(terr if terr is not None else (manual.get("territory") or {}).get("DEFAULT", 1.06))

    driver_f = _driver_factor(manual, factors.driver_age, factors.years_licensed)
    symbol_f = _band_factor(manual.get("vehicle_symbol") or [], factors.vehicle_value or 25000, "max_value")
    miles = factors.annual_mileage if factors.annual_mileage is not None else 12000
    mileage_f = _band_factor(manual.get("mileage") or [], float(miles), "max")
    use = factors.intended_use if factors.intended_use in (manual.get("use_factors") or {}) else "personal"
    use_f = float((manual.get("use_factors") or {}).get(use, 1.0))
    perf_f = float(manual.get("high_performance_factor", 1.35)) if factors.high_performance else 1.0

    viol_pts = min(factors.violations * float((manual.get("violation_points") or {}).get("each", 0.12)), float((manual.get("violation_points") or {}).get("cap", 0.60)))
    af_pts = min(
        factors.at_fault_accidents * float((manual.get("at_fault_points") or {}).get("each", 0.18)),
        float((manual.get("at_fault_points") or {}).get("cap", 0.72)),
    )
    record_f = 1.0 + viol_pts + af_pts

    base_premium = package_base
    adjusted = package_base * terr * driver_f * symbol_f * mileage_f * use_f * perf_f * record_f
    adjusted += float(manual.get("expense_constant", 55.0))
    adjusted = max(adjusted, float(manual.get("minimum_premium", 650.0)))
    adjusted = round(adjusted, 2)

    if factors.rideshare and elig.get("rideshare_refer"):
        reasons.append("Rideshare use — underwriter referral")

    exposure = factors.vehicle_value or 25000.0
    components = [
        RateComponent(name="bi_pd_base", amount=bi, basis="liability"),
        RateComponent(name="comp_base", amount=comp, basis="physical"),
        RateComponent(name="coll_base", amount=coll, basis="physical"),
    ]
    if um:
        components.append(RateComponent(name="um_uim_base", amount=um, basis="liability"))
    if med:
        components.append(RateComponent(name="medpay_base", amount=med, basis="medical"))
    components.extend(
        [
            RateComponent(name="territory", amount=terr, basis=state or "DEFAULT"),
            RateComponent(name="driver_class", amount=driver_f, basis=f"age={factors.driver_age}"),
            RateComponent(name="vehicle_symbol", amount=symbol_f, basis=f"value={exposure}"),
            RateComponent(name="mileage", amount=mileage_f, basis=str(miles)),
            RateComponent(name="use", amount=use_f, basis=use),
            RateComponent(
                name="driving_record",
                amount=round(record_f, 3),
                basis=f"v={factors.violations},af={factors.at_fault_accidents}",
            ),
        ]
    )
    if factors.high_performance:
        components.append(RateComponent(name="high_performance", amount=perf_f, basis="vehicle"))

    state_min = (manual.get("state_minimum_bi") or {}).get(state.upper() if state else "", None) or (manual.get("state_minimum_bi") or {}).get("DEFAULT", "25/50")

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.PERSONAL_AUTO,
        base_premium=round(base_premium, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / (exposure / 100.0), 4) if exposure else 0.0,
        eligible=eligible,
        ineligibility_reasons=reasons if not eligible else [r for r in reasons if "referral" in r.lower()],
        metadata={
            "filing_id": manual.get("filing_id"),
            "product": manual.get("product"),
            "serff_tracking": manual.get("serff_tracking"),
            "rating_engine": "auto_filing",
            "state_minimum_bi": state_min,
            "personal_factors": {k: v for k, v in factors.__dict__.items() if k != "findings"},
            "referral_flags": [r for r in reasons if eligible],
            "tiv": exposure,
            "insurance_line": InsuranceLine.PERSONAL_AUTO.value,
            "personal_lines": True,
        },
    )
