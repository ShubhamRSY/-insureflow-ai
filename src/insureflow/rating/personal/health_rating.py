"""Health rating.

Tries the dedicated US-market LOB/Product/Coverage logic paths
(insureflow.health.lobs) first — one explicit module per product with its
own state-rule table, mirroring the life insurance architecture. Falls back
to the legacy flat filed-manual engine below for any product not (yet)
registered there.
"""

from __future__ import annotations

import logging
from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.personal.manuals import _band_factor, general_health_manual
from insureflow.underwriting.general_uw import _claims_severity
from insureflow.underwriting.health_product import is_filed_health_product
from insureflow.underwriting.health_uw import health_product_terms
from insureflow.underwriting.personal_lines import _blob, _int_field, _money

logger = logging.getLogger(__name__)

_AGE_LABELS = ("age", "insured age", "applicant age", "proposer age", "principal member age")
_BENEFIT_LABELS = ("sum insured", "coverage amount", "benefit amount", "lump sum", "principal sum", "monthly benefit", "weekly benefit", "face amount", "deductible")


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
    # ── Dedicated LOB/Product/Coverage logic paths (US market) ──────────
    # Dispatches BEFORE the legacy catalog lookup below (unlike life's
    # dispatch, which runs after its generic pre-computation) because the
    # legacy general_health_rate_manual.json has no entries at all for the
    # new US product ids — falling through to it first would always return
    # a false "catalog_only" ineligible quote for every one of them.
    try:
        from insureflow.health.lobs import HealthProductContext, run_product_logic
        from insureflow.health.lobs.base import _extract_sex, _extract_tobacco
        from insureflow.rating.personal.manuals import health_manual_us
        from insureflow.underwriting.health_uw import underwrite_health

        us_manual = health_manual_us()
        blob = _blob(bundle)
        parsed_age = _int_field(blob, *_AGE_LABELS)
        health_ctx = HealthProductContext(
            bundle=bundle,
            state_code=state,
            product_id=product_id or "",
            coverage_id=coverage_id or "",
            coverage_name=coverage_name or "",
            manual=us_manual,
            uw=underwrite_health(bundle),
            # `parsed_age or 40` would silently rewrite a genuine age-0
            # newborn dependent (a real primary applicant on the several
            # MIN_ISSUE_AGE=0 family/HDHP/hospital-indemnity products) to 40,
            # since 0 is falsy in Python — an explicit None-check is required.
            age=parsed_age if parsed_age is not None else 40,
            sex_key=_extract_sex(blob),
            tobacco=_extract_tobacco(blob),
            income=_money(blob, "income", "annual income", "salary"),
            benefit_amount=_money(blob, *_BENEFIT_LABELS),
            household_members=_int_field(blob, "household size", "number of dependents", "family size", "employee count", "number of employees") or 1,
            modal="monthly" if "monthly premium" in blob or "modal: m" in blob else "annual",
        )
        lob_result = run_product_logic(health_ctx)
        if lob_result is not None:
            return lob_result
    except Exception as exc:
        logger.error(
            "Health LOB logic path failed for product_id=%s coverage_id=%s (%s: %s) — falling back to legacy health pricing, which may produce a materially different premium",
            product_id,
            coverage_id,
            type(exc).__name__,
            exc,
            exc_info=True,
        )

    # ── Legacy flat filed-manual engine (unregistered products only) ────
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

    # Morbidity-table incidence + covered-lives exposure base + network structure
    # enrich the metadata without disturbing the filed rate calculation.
    morbidity = 0.0
    covered_lives = 0.0
    network = None
    benefit = str(terms.get("benefit_type") or "").lower()
    if age is not None:
        from insureflow.rating.personal.morbidity import morbidity_rate

        benefit_type = "critical_illness" if "critical" in benefit or "ci" in benefit else "disability"
        morbidity = morbidity_rate(age=age, sex="male", benefit_type=benefit_type)
    from insureflow.underwriting.health_exposure import covered_lives as _covered_lives

    if bundle.structured is not None and bundle.structured.financial is not None:
        covered_lives = _covered_lives(employee_count=bundle.structured.financial.employee_count)
    from insureflow.underwriting.health_network import network_assessment_from_bundle

    network = network_assessment_from_bundle(bundle)

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
            "morbidity_rate_per_1000": morbidity,
            "covered_lives": covered_lives,
            "network": network,
            **terms,
        },
    )
