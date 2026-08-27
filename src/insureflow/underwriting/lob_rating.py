"""Per-LOB underwriting rating — exposure bases, credibility, coverage modifiers, UW worksheet."""

from __future__ import annotations

from typing import Any

from insureflow.ml.lob_profiles import lob_profile
from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent

# Coverage-level premium allocation factors (property product)
COVERAGE_FACTORS: dict[str, float] = {
    "building_structure": 1.00,
    "building": 1.00,
    "bpp": 0.72,
    "business_personal_property": 0.72,
    "tenant_improvements": 0.65,
    "replacement_cost_acv": 0.08,
    "named_perils_all_risk": 0.05,
    "bi_gross_earnings": 0.85,
    "bi_extra_expense": 0.45,
    "contingent_bi": 0.55,
    "civil_authority": 0.25,
    "employee_dishonesty": 0.35,
    "forgery_alteration": 0.20,
    "burglary_robbery": 0.40,
    "computer_fraud": 0.30,
}

# NCCI-style manual rates per $100 payroll (representative class blends)
WC_CLASS_RATE = 3.25  # blended manual rate
WC_EXP_MOD_BASE = 1.0

# GL exposure: per $1,000 sales
GL_RATE_PER_1K_SALES = 0.42


def _estimate_payroll(bundle: SubmissionBundle) -> float:
    if bundle.structured and bundle.structured.financial:
        fin = bundle.structured.financial
        for attr in ("payroll", "annual_payroll", "total_payroll"):
            v = getattr(fin, attr, None)
            if v and float(v) > 0:
                return float(v)
    return 0.0


def _estimate_sales(bundle: SubmissionBundle) -> float:
    if bundle.structured and bundle.structured.financial:
        rev = float(bundle.structured.financial.annual_revenue or 0)
        if rev > 0:
            return rev
    return 0.0


def _estimate_tiv(bundle: SubmissionBundle) -> float:
    total = 0.0
    if bundle.structured:
        for loc in bundle.structured.locations:
            total += float(loc.building_value or 0) + float(loc.contents_value or 0) + float(loc.bi_value or 0)
        for sov in bundle.structured.schedule_of_values or []:
            for item in sov.items or []:
                total += float(item.value or 0)
    return max(total, 0.0)


def _loss_ratio(bundle: SubmissionBundle) -> float:
    from insureflow.underwriting.loss_ratio import loss_ratio_from_bundle

    result = loss_ratio_from_bundle(bundle)
    return result.ratio if result.known else 0.0


def _credibility_mod(prior_claims: int, raw_mod: float, *, k: float = 8.0) -> tuple[float, float]:
    """Bühlmann-style credibility: Z = n / (n + k)."""
    n = max(prior_claims, 0)
    z = n / (n + k) if (n + k) > 0 else 0.0
    blended = (1.0 - z) * 1.0 + z * raw_mod
    return round(blended, 4), round(z, 4)


def _coverage_factor(coverage_id: str | None) -> float:
    if not coverage_id:
        return 1.0
    key = coverage_id.strip().lower()
    if key in COVERAGE_FACTORS:
        return COVERAGE_FACTORS[key]
    for pattern, factor in COVERAGE_FACTORS.items():
        if pattern in key or key in pattern:
            return factor
    return 1.0


def apply_lob_rating(
    quote: QuoteResult,
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    *,
    line: InsuranceLine,
    insurance_line: str | None = None,
    commercial_coverage_id: str | None = None,
    commercial_product_id: str | None = None,
) -> QuoteResult:
    """Adjust indicated premium using LOB-appropriate exposure bases and coverage context."""
    meta = dict(quote.metadata or {})
    # Dedicated actuarial manuals already applied in InsuranceRatingEngine — do not overwrite.
    engine = str(meta.get("rating_engine") or "")
    if line == InsuranceLine.LIFE or engine in {
        "life_filing",
        "ncci_class_emod",
        "package_section_rating",
        "cyber_manual",
        "commercial_auto_manual",
        "inland_marine_manual",
        "crime_fidelity_manual",
        "builders_risk_manual",
        "surety_rate_manual",
        "carrier_leaf_filing",
        "iso_gl_sales",
        "iso_umbrella",
        "catalog_only",
    }:
        if commercial_coverage_id:
            cov_factor = _coverage_factor(commercial_coverage_id)
            if cov_factor != 1.0 and line == InsuranceLine.COMMERCIAL_PROPERTY:
                quote.adjusted_premium = round(float(quote.adjusted_premium) * cov_factor, 2)
                meta["coverage_premium_factor"] = cov_factor
                quote.metadata = meta
        return quote

    prof = lob_profile(insurance_line or line.value)
    prior_claims = 0
    if bundle.structured and bundle.structured.risk_profile:
        prior_claims = len(bundle.structured.risk_profile.prior_claims or [])

    from insureflow.underwriting.loss_ratio import loss_ratio_from_bundle

    lr_result = loss_ratio_from_bundle(bundle)
    lr = lr_result.ratio if lr_result.known else 0.0
    if lr_result.known:
        raw_exp_mod = 1.0 + min(max((lr - 0.55) * 0.35, -0.25), 0.45)
        exp_mod, credibility_z = _credibility_mod(prior_claims, raw_exp_mod)
    else:
        exp_mod, credibility_z = 1.0, 0.0

    cov_factor = _coverage_factor(commercial_coverage_id)
    meta["lob_profile"] = {
        "insurance_line": insurance_line or line.value,
        "category_id": prof.get("category_id"),
        "coverage_id": commercial_coverage_id,
        "coverage_factor": cov_factor,
    }

    base = float(quote.base_premium or 0)
    adjusted = float(quote.adjusted_premium or 0)
    components = list(quote.schedule_modifications or [])

    if line == InsuranceLine.GENERAL_LIABILITY and engine != "iso_gl_sales":
        sales = _estimate_sales(bundle)
        base = round((sales / 1000.0) * GL_RATE_PER_1K_SALES, 2)
        adjusted = round(base * exp_mod * float(prof.get("premium_load", 1.0)), 2)
        meta["exposure_basis"] = "gross_sales"
        meta["sales"] = sales
        meta["rating_engine"] = "iso_gl_sales"
        components.append(RateComponent(name="gl_sales_rate", amount=GL_RATE_PER_1K_SALES, basis="per_1k_sales", modifier_pct=0.0))
    elif commercial_coverage_id and cov_factor != 1.0:
        adjusted = round(adjusted * cov_factor, 2)
        meta["coverage_premium_factor"] = cov_factor
        components.append(
            RateComponent(
                name=f"coverage_{commercial_coverage_id}",
                amount=cov_factor,
                basis="coverage_allocation",
                modifier_pct=(cov_factor - 1.0) * 100,
            )
        )

    min_prem = float(meta.get("minimum_premium") or 500.0)
    adjusted = max(adjusted, min_prem)

    quote.base_premium = base if base > 0 else quote.base_premium
    quote.adjusted_premium = adjusted
    quote.schedule_modifications = components
    meta["credibility_z"] = credibility_z
    meta["loss_ratio_input"] = lr
    meta["loss_ratio_known"] = lr_result.known
    meta["loss_ratio_basis"] = lr_result.basis
    meta["experience_mod_blended"] = exp_mod
    quote.metadata = meta
    return quote


# RateComponent.amount means different things per component: for these names
# it's a multiplicative factor centered on 1.0 (0.82 = -18% off baseline), so a
# "percentage swing" is meaningful. For the rest (mortality_per_1000, flat
# dollar amounts like flat_extras/riders/policy_fee, or actuarial net-premium
# breakdowns) amount is a rate or dollar figure, not a factor away from 1.0 —
# computing (amount - 1) * 100 there would be nonsense, not a real percentage.
_MULTIPLICATIVE_FACTOR_NAMES = {
    "underwriting_class",
    "sex_factor",
    "tobacco_factor",
    "band_discount",
    "term_duration",
    "product_family",
    "state_relativity",
    "modal_factor",
}


def _derived_modifier_pct(c: RateComponent) -> float | None:
    """Real percentage swing from baseline for a rating component.

    Life-insurance schedule_modifications store multiplicative factors in
    ``amount`` with ``modifier_pct`` left at its 0.0 default (commercial lines
    use the reverse convention). Derive the real percentage for factor-style
    components instead of showing a flat, misleading 0.0% for every row; for
    components where "percent swing" isn't a meaningful concept, return None
    so the UI can show "not applicable" instead of a fake number.
    """
    if c.modifier_pct:
        return c.modifier_pct
    if c.name in _MULTIPLICATIVE_FACTOR_NAMES and c.amount is not None:
        return round((c.amount - 1.0) * 100.0, 2)
    return None


def build_uw_worksheet(
    quote: QuoteResult,
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    *,
    line: InsuranceLine,
    insurance_line: str | None = None,
    commercial_product_name: str | None = None,
    commercial_coverage_name: str | None = None,
    commercial_coverage_id: str | None = None,
) -> dict[str, Any]:
    """UW-facing rate worksheet — formulas and indicated terms, no internal eval scores."""
    tiv = _estimate_tiv(bundle)
    payroll = _estimate_payroll(bundle)
    sales = _estimate_sales(bundle)
    lr = _loss_ratio(bundle)
    prof = lob_profile(insurance_line or line.value)
    meta = quote.metadata or {}
    is_life = (insurance_line or line.value) == "life"

    exposure_label = meta.get("exposure_basis") or "tiv"
    exposure_value = {
        "payroll": payroll,
        "gross_sales": sales,
        "tiv": tiv,
    }.get(exposure_label, tiv)

    components = [
        {
            "step": c.name.replace("_", " ").title(),
            "basis": c.basis,
            "factor": c.amount,
            "modifier_pct": _derived_modifier_pct(c),
        }
        for c in (quote.schedule_modifications or [])
    ]

    indicated = float(quote.adjusted_premium or 0)

    # Life vs P&C worksheets are not the same shape: deductible, exposure/TIV,
    # rate-per-$100, and loss-ratio/credibility are P&C (or renewal-experience)
    # concepts that don't apply to new-business individual life — showing a
    # hardcoded $5,000 deductible or $0 TIV on a life case reads as broken
    # data rather than "not applicable". `applicable_fields` tells the UI
    # which of these to render at all; life gets its own fields instead.
    if is_life:
        limit = float(meta.get("face_amount") or 0)
        deductible = None
        rate_per_100 = None
        loss_experience: dict[str, Any] = {
            "loss_ratio": None,
            "known": False,
            "basis": "not applicable — new business individual life (loss ratio applies at renewal)",
            "formula": None,
            "credibility_z": None,
            "experience_mod": None,
        }
        mortality_component = next((c for c in (quote.schedule_modifications or []) if c.name == "mortality_per_1000"), None)
        reinsurance_meta = meta.get("life_reinsurance") or {}
        cession = float(reinsurance_meta.get("cession_amount") or 0)
        life_terms = {
            "net_amount_at_risk": round(float(meta.get("face_amount") or 0), 2),
            "mortality_rate_per_1000": mortality_component.amount if mortality_component else None,
            "reinsurance_cession_status": (
                f"Facultative required — cede ${cession:,.0f} above retention"
                if reinsurance_meta.get("facultative_required")
                else f"Automatic treaty cession ${cession:,.0f}"
                if cession > 0
                else "Within retention — no cession"
                if reinsurance_meta
                else None
            ),
        }
        applicable_fields = {
            "deductible": False,
            "exposure_tiv": False,
            "rate_per_100": False,
            "policy_limit": True,
            "loss_ratio": False,
            "credibility_z": False,
            "net_amount_at_risk": True,
            "mortality_rate_per_1000": True,
            "reinsurance_cession": True,
        }
    else:
        limit = tiv if tiv > 0 else float(memo.recommendation.suggested_limit or 0) if memo.recommendation else 0
        if limit <= 0 and bundle.structured and bundle.structured.coverages:
            limit = max(float(c.limit_amount or 0) for c in bundle.structured.coverages)

        deductible = 0.0
        if bundle.structured and bundle.structured.coverages:
            deds = [float(c.deductible or 0) for c in bundle.structured.coverages if c.deductible]
            deductible = max(deds) if deds else 2500.0
        if deductible <= 0:
            deductible = 2500.0 if line in (InsuranceLine.COMMERCIAL_PROPERTY, InsuranceLine.BOP) else 5000.0

        rate_per_100 = round(indicated / (exposure_value / 100.0), 4) if exposure_value > 0 else 0.0
        loss_experience = {
            "loss_ratio": round(lr, 4),
            "known": bool(meta.get("loss_ratio_known", lr > 0)),
            "basis": meta.get("loss_ratio_basis") or ("stored" if lr > 0 else "unknown"),
            "formula": "incurred_losses / earned_premium",
            "credibility_z": meta.get("credibility_z"),
            "experience_mod": meta.get("experience_mod_blended"),
        }
        life_terms = None
        applicable_fields = {
            "deductible": True,
            "exposure_tiv": True,
            "rate_per_100": True,
            "policy_limit": True,
            "loss_ratio": True,
            "credibility_z": True,
            "net_amount_at_risk": False,
            "mortality_rate_per_1000": False,
            "reinsurance_cession": False,
        }

    return {
        "product": commercial_product_name or prof.get("name") or line.value.replace("_", " ").title(),
        "coverage": commercial_coverage_name or "",
        "coverage_id": commercial_coverage_id,
        "insurance_line": insurance_line or line.value,
        "applicable_fields": applicable_fields,
        "life_terms": life_terms,
        "exposure": {
            "label": exposure_label.replace("_", " ").upper(),
            "value": round(exposure_value, 2),
            "tiv": round(tiv, 2),
            "payroll": round(payroll, 2),
            "sales": round(sales, 2),
        },
        "loss_experience": loss_experience,
        "indicated_terms": {
            "premium": indicated,
            "base_premium": float(quote.base_premium or 0),
            "limit": round(limit, 2),
            "deductible": round(deductible, 2) if deductible is not None else None,
            "rate_per_100_exposure": rate_per_100,
        },
        "premium_buildup": components,
        "uw_focus": prof.get("uw_focus", ""),
        "decision": memo.decision.value if hasattr(memo.decision, "value") else str(memo.decision),
        "conditions": list(memo.conditions or [])[:12],
        "rating_method": meta.get("rating_engine") or "iso_loss_cost_lcm",
        "eligible": quote.eligible,
    }
