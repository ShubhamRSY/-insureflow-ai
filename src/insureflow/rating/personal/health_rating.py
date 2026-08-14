"""Health rating — filed retail health manual (mediclaim, floater, CI, senior, group, PA, disability)."""

from __future__ import annotations

from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.personal.manuals import _band_factor, general_health_manual
from insureflow.underwriting.general_uw import _claims_severity
from insureflow.underwriting.health_product import is_filed_health_product
from insureflow.underwriting.health_uw import health_product_terms
from insureflow.underwriting.personal_lines import _blob, _int_field, _money

_AGE_LABELS = ("age", "insured age", "applicant age", "proposer age", "principal member age")


def _sum_insured(blob: str, conf: dict[str, Any]) -> float:
    if conf.get("daily_basis"):
        daily = _money(blob, *(conf.get("daily_labels") or ["daily cash", "daily benefit"]))
        if daily <= 0:
            return 0.0
        return daily * float(conf.get("annualization_factor", 365))
    if conf.get("income_basis"):
        monthly = _money(blob, *(conf.get("income_labels") or ["monthly income"]))
        if monthly <= 0:
            annual = _money(blob, *(conf.get("annual_income_labels") or ["annual income"]))
            if annual > 0:
                monthly = annual / 12.0
        if monthly <= 0:
            return 0.0
        ratio = float(conf.get("coverage_ratio", 0.75))
        benefit = min(monthly * ratio, float(conf.get("max_benefit_per_month", 200_000)))
        months = float(conf.get("benefit_months", 24))
        return benefit * months
    from insureflow.underwriting.general_uw import _scaled_money

    labels = conf.get("si_labels") or ["sum insured", "cover amount", "sum assured", "annual limit"]
    return _scaled_money(blob, *labels)


def rate_health(
    bundle: SubmissionBundle,
    *,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
    product_id: str | None = None,
    state: str = "",
) -> QuoteResult:
    """Rate a filed retail health product from the carrier health manual."""
    pid = str(product_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    terms = health_product_terms(pid, coverage_id)
    manual = general_health_manual()
    conf = (manual.get("products") or {}).get(pid)
    if not conf:
        return QuoteResult(
            bundle_id=bundle.bundle_id,
            line=InsuranceLine.HEALTH,
            base_premium=0.0,
            adjusted_premium=0.0,
            eligible=False,
            ineligibility_reasons=[
                f"{terms.get('benefit_type') or 'health'} is catalog-only until a filed health rate manual is imported — will not invent premium",
            ],
            metadata={
                "rating_engine": "catalog_only",
                "insurance_line": "health",
                "product_id": pid,
                "coverage_id": coverage_id or "",
                "coverage_name": coverage_name or "",
                "state": state,
                "filed": is_filed_health_product(pid),
                **terms,
            },
        )

    blob = _blob(bundle)
    elig = manual.get("eligibility") or {}
    min_si = float(elig.get("min_sum_insured", 100_000))
    max_si = float(elig.get("max_sum_insured", 100_000_000))
    min_age = float(elig.get("min_age", 18))
    max_age = float(elig.get("max_age", 75))

    age = _int_field(blob, *_AGE_LABELS)
    si = _sum_insured(blob, conf)
    deductible = _money(blob, "deductible", "excess")
    severity = _claims_severity(blob) or "none"

    base_rate = float(conf.get("base_rate", 0.0))
    min_premium = float(conf.get("min_premium", 0.0))
    expense_constant = float(conf.get("expense_constant", 0.0))

    reasons: list[str] = []
    eligible = True
    if age is None:
        eligible = False
        reasons.append("Attained age not declared — cannot rate health")
    else:
        p_min = float(conf.get("min_age") or 0) or min_age
        p_max = float(conf.get("max_age") or 0) or max_age
        if age < p_min:
            eligible = False
            reasons.append(f"Attained age {age} below the {p_min:,.0f} minimum for this plan")
        if age > p_max:
            eligible = False
            reasons.append(f"Attained age {age} above the {p_max:,.0f} maximum for this plan")
    if si <= 0:
        eligible = False
        reasons.append("Sum insured not declared — cannot rate health")
    if si < min_si:
        eligible = False
        reasons.append(f"Sum insured below the {min_si:,.0f} filing minimum")
    if si > max_si:
        eligible = False
        reasons.append("Sum insured above filed maximum")

    if not eligible:
        return QuoteResult(
            bundle_id=bundle.bundle_id,
            line=InsuranceLine.HEALTH,
            base_premium=0.0,
            adjusted_premium=0.0,
            eligible=False,
            ineligibility_reasons=reasons,
            metadata={
                "filing_id": manual.get("filing_id"),
                "rating_engine": "health_filing",
                "insurance_line": "health",
                "product_id": pid,
                "coverage_id": coverage_id or "",
                "coverage_name": coverage_name or "",
                "state": state,
                "filed": True,
                "age": age,
                "sum_insured": si,
                "claims_severity": severity,
                **terms,
            },
        )

    age_f = _band_factor(manual.get("age_factors") or [], float(age or 0), "max_age")
    si_f = _band_factor(manual.get("sum_insured_factors") or [], si, "max_sum_insured")
    ded_f = _band_factor(manual.get("deductible_factors") or [], deductible, "max_deductible")
    claims_f = float((manual.get("claims_factors") or {}).get(severity, 1.0))

    base_premium = round(base_rate * (si / 1000.0), 2)
    adjusted = base_premium * age_f * si_f * ded_f * claims_f + expense_constant
    adjusted = max(adjusted, min_premium)
    adjusted = round(adjusted, 2)
    components = [
        RateComponent(name="health_base", amount=base_premium, basis=f"₹{si:,.0f} sum insured"),
        RateComponent(name="attained_age", amount=age_f, basis=f"age={age or 0}"),
        RateComponent(name="sum_insured_band", amount=si_f, basis=f"si={si:,.0f}"),
        RateComponent(name="deductible_band", amount=ded_f, basis=f"deductible={deductible:,.0f}"),
        RateComponent(name="claims_record", amount=claims_f, basis=severity),
        RateComponent(name="expense_constant", amount=expense_constant, basis="per policy"),
    ]
    rate_per_1000 = round(adjusted / (si / 1000.0), 4)

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.HEALTH,
        base_premium=base_premium,
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=rate_per_1000,
        eligible=True,
        ineligibility_reasons=[],
        metadata={
            "filing_id": manual.get("filing_id"),
            "serff_tracking": manual.get("serff_tracking"),
            "rating_engine": manual.get("rating_engine") or "health_filing",
            "insurance_line": "health",
            "product_id": pid,
            "coverage_id": coverage_id or "",
            "coverage_name": coverage_name or "",
            "state": state,
            "filed": True,
            "age": age,
            "sum_insured": si,
            "deductible": deductible,
            "claims_severity": severity,
            **terms,
        },
    )
