"""Health rating.

Tries the dedicated US-market LOB/Product/Coverage logic paths
(insureflow.health.lobs) first — one explicit module per product with its
own state-rule table, mirroring the life insurance architecture. Falls back
to the legacy flat filed-manual engine below for any product not (yet)
registered there.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.personal.manuals import _band_factor, general_health_manual
from insureflow.underwriting.general_uw import _claims_severity
from insureflow.underwriting.health_product import is_filed_health_product
from insureflow.underwriting.health_uw import health_product_terms
from insureflow.underwriting.personal_lines import _blob, _int_field, _money, annual_income, applicant_age

logger = logging.getLogger(__name__)

_AGE_LABELS = ("applicant age", "insured age", "proposer age", "principal member age")
_BENEFIT_LABELS = ("sum insured", "coverage amount", "benefit amount", "lump sum", "principal sum", "monthly benefit", "weekly benefit", "face amount", "deductible")


_TOTAL_COUNT_LABELS = (
    "household size",
    "family size",
    "employee count",
    "number of employees",
    "number of covered employees",
    "total covered employees",
    "covered employees",
    "eligible employees",
    "enrolled employees",
    "employees enrolled",
    "total employees",
    "covered lives",
    "group size",
    "headcount",
)
_DEPENDENT_COUNT_LABELS = ("number of dependents", "number of covered dependents", "number of children", "dependents")


def _stated_household_members(blob: str) -> int | None:
    """Total covered lives as stated: an explicit total wins; a dependents count is additive to the primary applicant. None when nothing is stated."""
    total = _int_field(blob, *_TOTAL_COUNT_LABELS)
    if total is not None:
        return max(1, total)
    # Filler words between label and number ("covered employees across all members: 180"), or the number first ("200 employees enrolled").
    loose = re.search(
        r"(?:covered employees|employees enrolled|covered lives|employee count|number of employees|group size)[^\d\n]{0,40}?(\d{1,3}(?:,\d{3})+|\d{1,7})"
        r"|\b(\d{1,3}(?:,\d{3})+|\d{1,7})\s+(?:employees|covered lives|lives)\b",
        blob,
        re.I,
    )
    if loose:
        return max(1, int((loose.group(1) or loose.group(2)).replace(",", "")))
    dependents = _int_field(blob, *_DEPENDENT_COUNT_LABELS)
    return 1 + dependents if dependents is not None else None


def _household_members(blob: str) -> int:
    return _stated_household_members(blob) or 1


# A benefit label that means something else for a product must never be read as its rating base
# (a "Deductible" is not a CI lump sum; a "Sum insured" is not a gap plan's deductible).
_PRODUCT_BENEFIT_LABELS: dict[str, tuple[str, ...]] = {
    "hospital_indemnity": ("daily benefit amount", "daily benefit", "daily cash", "benefit amount"),
    "short_term_disability": ("weekly benefit", "monthly benefit", "benefit amount"),
    "long_term_disability": ("monthly benefit", "benefit amount"),
    "supplemental_gap_coverage": ("base plan deductible", "base deductible", "deductible"),
    "critical_illness_standalone": ("lump sum", "critical illness benefit", "sum insured", "benefit amount", "coverage amount"),
    "disease_specific_critical_illness": ("lump sum", "critical illness benefit", "sum insured", "benefit amount", "coverage amount"),
    "critical_illness_rider": ("lump sum", "critical illness benefit", "sum insured", "benefit amount", "coverage amount"),
    "critical_illness_multistage": ("lump sum", "critical illness benefit", "sum insured", "benefit amount", "coverage amount"),
    "add_accident_indemnity": ("principal sum", "sum insured", "benefit amount", "coverage amount"),
    "standalone_add": ("principal sum", "sum insured", "benefit amount", "coverage amount"),
    "disability_ptd": ("principal sum", "lump sum", "benefit amount", "sum insured"),
    "disability_ppd": ("principal sum", "lump sum", "benefit amount", "sum insured"),
}

_MODAL_FACTORS = {"monthly": 1 / 12, "quarterly": 1 / 4, "semiannual": 1 / 2}


def _modal(blob: str) -> str:
    if re.search(r"\bmonthly premium\b|\bmodal:\s*m\b|\bpay(?:ing|ment)?\s+monthly\b", blob):
        return "monthly"
    if re.search(r"\bquarterly (?:premium|payment)\b", blob):
        return "quarterly"
    if re.search(r"\bsemi[- ]?annual (?:premium|payment)\b", blob):
        return "semiannual"
    return "annual"


def _require_declared_inputs(result: QuoteResult, *, age_declared: bool, count_declared: bool) -> QuoteResult:
    """A quote built on an assumed age (or an assumed one-life group) must not stay bindable."""
    family = result.metadata.get("product_family")
    reasons: list[str] = []
    if family == "group":
        if not count_declared:
            reasons.append("Employee / covered-lives count not declared — cannot rate a group")
    elif not age_declared:
        reasons.append("Applicant age not declared or not readable — cannot rate")
    if not reasons or not result.eligible:
        return result
    result.eligible = False
    result.ineligibility_reasons = [*result.ineligibility_reasons, *reasons]
    result.base_premium = 0.0
    result.adjusted_premium = 0.0
    result.rate_per_100_tiv = 0.0
    result.metadata["modal_premium"] = 0.0
    result.metadata["outcome"] = "refer"
    return result


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
        parsed_age = applicant_age(blob, *_AGE_LABELS)
        modal = _modal(blob)
        from insureflow.health.lobs import resolve_product_id

        benefit_labels = _PRODUCT_BENEFIT_LABELS.get(resolve_product_id(product_id, coverage_id, coverage_name) or "", _BENEFIT_LABELS)
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
            income=annual_income(blob),
            benefit_amount=_money(blob, *benefit_labels),
            household_members=_household_members(blob),
            modal=modal,
            modal_f=_MODAL_FACTORS.get(modal, 1.0),
        )
        lob_result = run_product_logic(health_ctx)
        if lob_result is not None:
            return _require_declared_inputs(lob_result, age_declared=parsed_age is not None, count_declared=_stated_household_members(blob) is not None)
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

    age = applicant_age(blob, *_AGE_LABELS)
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
