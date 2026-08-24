"""Term life filing-style premium calculation."""

from __future__ import annotations

import logging
import re
from typing import Any

from insureflow.decisions import is_decline, normalize_decision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.personal.manuals import life_manual, nearest_key
from insureflow.underwriting.life_financial import evaluate_life_financial
from insureflow.underwriting.life_medical import underwrite_life
from insureflow.underwriting.life_product import classify_life_family, is_filed_term_product
from insureflow.underwriting.life_reinsurance import evaluate_life_reinsurance
from insureflow.underwriting.personal_lines import _blob, extract_life_factors

logger = logging.getLogger(__name__)

# Permanent products price via whole-life actuarial equivalence (A_x / ä_x)
# instead of a flat family multiplier on one-year term mortality.
PERMANENT_ACTUARIAL_FAMILIES = {"whole_life", "universal", "variable_universal"}


def _term_duration_years(coverage_id: str | None, coverage_name: str | None = None) -> int | None:
    blob = f"{coverage_id or ''} {coverage_name or ''}".lower()
    match = re.search(r"(?:^|[_\s-])(10|15|20|25|30)(?:\s*-?\s*year|_year|yr)?(?:$|[_\s-])", blob)
    if match:
        return int(match.group(1))
    match = re.search(r"(10|15|20|25|30)\s*-?\s*year", blob)
    if match:
        return int(match.group(1))
    return None


def _modal_from_blob(blob: str) -> str:
    if re.search(r"\bmonthly\b|\bmodal:\s*m\b", blob, re.I):
        return "monthly"
    if re.search(r"\bquarterly\b", blob, re.I):
        return "quarterly"
    if re.search(r"\bsemi[- ]?annual\b", blob, re.I):
        return "semiannual"
    return "annual"


def rate_life(
    bundle: SubmissionBundle,
    *,
    coverage_id: str | None = None,
    coverage_name: str | None = None,
    product_id: str | None = None,
    state: str = "",
) -> QuoteResult:
    manual = life_manual()
    factors = extract_life_factors(bundle)
    medical = underwrite_life(bundle)
    financial = evaluate_life_financial(bundle, factors=factors, product_id=product_id, coverage_id=coverage_id, coverage_name=coverage_name)
    reinsurance = evaluate_life_reinsurance(bundle, face_amount=factors.face_amount)
    family = classify_life_family(product_id, coverage_id, coverage_name)
    if family == "unknown" and not product_id and not coverage_id and not coverage_name:
        # No explicit product selection — sniff the submission text so
        # consideration-based products (annuities) reach their paths.
        import re as _re

        if _re.search(r"\bannuit", _blob(bundle), _re.I):
            family = "annuity"
    term_years_hint = _term_duration_years(coverage_id, coverage_name)
    if term_years_hint and family in {"unknown", "term"}:
        family = "term"
    filed_term = is_filed_term_product(product_id, coverage_id, coverage_name) or family == "term"

    face = factors.face_amount
    reasons: list[str] = []

    if family == "annuity":
        annuity_meta: dict[str, Any] = {
            "filing_id": manual.get("filing_id"),
            "rating_engine": "catalog_only",
            "product_family": family,
            "product_id": product_id or "",
            "medical": medical.to_metadata(),
            "financial": financial.to_metadata(),
            "life_reinsurance": reinsurance.to_metadata(),
        }
        try:
            from insureflow.rating.personal.annuity_rating import rate_annuity

            illustration = rate_annuity(
                bundle,
                product_id=product_id,
                coverage_id=coverage_id,
                coverage_name=coverage_name,
            )
            annuity_meta["annuity_illustration"] = illustration.metadata.get("illustrative_payout", {})
            annuity_meta["annuity_subtype"] = illustration.metadata.get("annuity_subtype", "fixed")
        except Exception:
            pass
        generic_annuity_meta = annuity_meta  # returned AFTER the LOB dispatch below

    age = factors.age or 40
    sex = factors.sex if factors.sex in ("male", "female") else "unknown"
    sex_key = "female" if sex == "female" else "male"
    unisex_states = {s.upper() for s in (manual.get("unisex_states") or ["MT"])}
    issue_state = (state or getattr(factors, "state", "") or "").upper()[:2]
    if issue_state in unisex_states:
        sex_key = "male"
        sex = "unisex"
    mort_table = (manual.get("mortality_per_1000") or {}).get(sex_key if sex_key in ("male", "female") else "male") or {}
    q = float(mort_table.get(nearest_key(mort_table, age), 1.5))

    class_factors = manual.get("underwriting_class_factors") or {}
    class_f = float(class_factors.get(medical.underwriting_class, class_factors.get("standard", 1.0)))
    sex_f = 1.0 if sex == "unisex" else float((manual.get("sex_factors") or {}).get(sex, 1.0))
    tobacco_f = float(manual.get("tobacco_factor", 1.85)) if medical.tobacco else 1.0
    band_f = 1.0
    for band in sorted(manual.get("band_discounts") or [], key=lambda b: float(b.get("min_face") or 0)):
        if face >= float(band.get("min_face") or 0):
            band_f = float(band.get("factor", 1.0))

    term_years = _term_duration_years(coverage_id, coverage_name)
    term_factors = manual.get("term_duration_factors") or {}
    term_f = float(term_factors.get(str(term_years), 1.0)) if term_years else 1.0

    product_families = manual.get("product_families") or {}
    product_f = float(product_families.get(family) or 1.0) if family != "term" else 1.0

    # ── Permanent products: actuarial whole-life pricing ──────────────
    # Net level premium P_x = A_x / ä_x at the manual's interest rate, with
    # expense loading; sex/tobacco are already inside the sex/smoker mortality
    # so only the UW class, band, and state factors apply on top.
    wl_interest = float(manual.get("whole_life_interest_rate", 0.04))
    wl_loading = float(manual.get("whole_life_expense_loading", 0.30))
    actuarial: dict[str, Any] | None = None
    if family in PERMANENT_ACTUARIAL_FAMILIES:
        try:
            from insureflow.life.whole_life_formulas import compute_full_whole_life_quote

            wl_quote = compute_full_whole_life_quote(
                age=age,
                sex=sex_key,
                smoker=bool(medical.tobacco),
                face_amount=face,
                interest_rate=wl_interest,
                expense_loading_pct=wl_loading,
                policy_fee=0.0,  # manual policy fee applied once below
            )
            actuarial = wl_quote.to_metadata()
            actuarial["interest_rate"] = wl_interest
            actuarial["expense_loading_pct"] = wl_loading
        except Exception as exc:
            logger.warning("Whole life actuarial pricing failed: %s", exc)
            actuarial = None

    blob = _blob(bundle)
    modal = _modal_from_blob(blob)
    modal_f = float((manual.get("modal_factors") or {}).get(modal) or 1.0)
    state_rel = float((manual.get("state_relativities") or {}).get(issue_state) or 1.0)
    filing_state = str(manual.get("state_of_filing") or "IL").upper()
    state_filed = (not issue_state) or issue_state == filing_state or issue_state in (manual.get("state_relativities") or {})

    # ── Dedicated LOB/Product/Coverage logic paths ────────────────────
    # Each registered product owns its own underwriting rules, rating math,
    # and state-rule table (see insureflow.life.lobs). Unregistered combos
    # fall through to the generic family pricing below.
    try:
        from insureflow.life.lobs import LifeProductContext, run_product_logic

        lob_ctx = LifeProductContext(
            bundle=bundle,
            state_code=issue_state,
            product_id=product_id or "",
            coverage_id=coverage_id or "",
            coverage_name=coverage_name or "",
            manual=manual,
            factors=factors,
            medical=medical,
            financial=financial,
            reinsurance=reinsurance,
            age=age,
            sex_key=sex_key,
            unisex_forced=(sex == "unisex"),
            face=face,
            modal=modal,
            modal_f=modal_f,
        )
        lob_result = run_product_logic(lob_ctx)
        if lob_result is not None:
            return lob_result
    except Exception as exc:
        logger.warning("LOB logic path failed for %s/%s: %s", product_id, coverage_id, exc)

    # Unregistered annuity combos fall back to the generic illustration.
    if family == "annuity":
        return QuoteResult(
            bundle_id=bundle.bundle_id,
            line=InsuranceLine.LIFE,
            base_premium=0.0,
            adjusted_premium=0.0,
            eligible=False,
            ineligibility_reasons=["Annuity requires payout / consideration factors — not rated on term mortality"],
            metadata=generic_annuity_meta,
        )

    # Face-driven products: without a face amount nothing can be rated.
    # (Annuity paths above read the purchase price / consideration instead.)
    if face <= 0:
        return QuoteResult(
            bundle_id=bundle.bundle_id,
            line=InsuranceLine.LIFE,
            base_premium=0.0,
            adjusted_premium=0.0,
            eligible=False,
            ineligibility_reasons=["Face amount missing — cannot rate"],
            metadata={"filing_id": manual.get("filing_id"), "tiv_unknown": True, "medical": medical.to_metadata()},
        )

    if actuarial and float(actuarial.get("gross_premium") or 0) > 0:
        base_premium = float(actuarial["gross_premium"])
        adjusted = base_premium * class_f * band_f * state_rel
    else:
        base_premium = (face / 1000.0) * q
        adjusted = base_premium * class_f * sex_f * tobacco_f * band_f * term_f * product_f * state_rel
    adjusted += (face / 1000.0) * medical.flat_extras_per_1000
    adjusted += (face / 1000.0) * financial.rider_load_per_1000
    annual = adjusted + float(manual.get("policy_fee", 60.0))
    modal_premium = round(annual * modal_f, 2) if modal != "annual" else round(max(annual, float(manual.get("minimum_premium", 250.0))), 2)
    adjusted = round(max(annual, float(manual.get("minimum_premium", 250.0))), 2)

    eligible = not is_decline(medical.decision)
    reasons = list(medical.reasons)
    reasons.extend(financial.reasons)
    reasons.extend(reinsurance.reasons)

    if not filed_term:
        eligible = False
        if actuarial:
            reasons.append(f"{family.replace('_', ' ')} priced on actuarial equivalence (A_x / ä_x) — illustrative only, no {filing_state}-filed permanent rates")
        else:
            reasons.append(f"{family.replace('_', ' ')} has no filed rates — illustrative load only, not an issueable premium")
    if issue_state and issue_state != filing_state:
        reasons.append(f"IL pilot exhibit applied — not a {issue_state} state-of-issue filing")
        if not state_filed:
            eligible = False

    if actuarial:
        net_prem = float(actuarial.get("level_net_premium") or 0.0)
        components = [
            RateComponent(name="whole_life_net_premium", amount=round(net_prem, 2), basis=f"A_x/ä_x @ {wl_interest:.0%} age={age}/{sex_key}"),
            RateComponent(name="expense_loading", amount=round(base_premium - net_prem, 2), basis=f"{float(actuarial.get('expense_loading_pct', 0) or 0):.0%} of net"),
            RateComponent(name="underwriting_class", amount=class_f, basis=medical.underwriting_class),
            RateComponent(name="band_discount", amount=band_f, basis=f"face={face}"),
            RateComponent(name="state_relativity", amount=state_rel, basis=issue_state or filing_state),
            RateComponent(name="modal_factor", amount=modal_f, basis=modal),
            RateComponent(name="flat_extras", amount=medical.flat_extras_per_1000, basis="per_1000"),
            RateComponent(name="riders", amount=financial.rider_load_per_1000, basis="per_1000"),
            RateComponent(name="policy_fee", amount=float(manual.get("policy_fee", 60.0)), basis="policy"),
        ]
    else:
        components = [
            RateComponent(name="mortality_per_1000", amount=q, basis=f"age={age}/{sex_key}"),
            RateComponent(name="underwriting_class", amount=class_f, basis=medical.underwriting_class),
            RateComponent(name="sex_factor", amount=sex_f, basis=sex),
            RateComponent(name="tobacco_factor", amount=tobacco_f, basis="tobacco" if medical.tobacco else "non_tobacco"),
            RateComponent(name="band_discount", amount=band_f, basis=f"face={face}"),
            RateComponent(name="term_duration", amount=term_f, basis=f"{term_years}yr" if term_years else "default"),
            RateComponent(name="product_family", amount=product_f, basis=family),
            RateComponent(name="state_relativity", amount=state_rel, basis=issue_state or filing_state),
            RateComponent(name="modal_factor", amount=modal_f, basis=modal),
            RateComponent(name="flat_extras", amount=medical.flat_extras_per_1000, basis="per_1000"),
            RateComponent(name="riders", amount=financial.rider_load_per_1000, basis="per_1000"),
            RateComponent(name="policy_fee", amount=float(manual.get("policy_fee", 60.0)), basis="policy"),
        ]

    product_label = manual.get("product")
    if filed_term and term_years:
        product_label = f"{term_years}-Year Level Term"
    elif actuarial:
        product_label = f"Illustrative {family.replace('_', ' ').title()} — Actuarial Basis (not filed)"
    elif not filed_term:
        product_label = f"Illustrative {family.replace('_', ' ')} (not filed)"

    meta: dict[str, Any] = {
        "filing_id": manual.get("filing_id"),
        "product": product_label,
        "product_id": product_id or "",
        "product_family": family,
        "filed_term": filed_term,
        "illustrative": not filed_term,
        "life_coverage_id": coverage_id or "",
        "term_years": term_years,
        "modal": modal,
        "modal_premium": modal_premium,
        "issue_state": issue_state,
        "state_of_filing": filing_state,
        "serff_tracking": manual.get("serff_tracking"),
        "rating_engine": "life_whole_life_actuarial" if actuarial else ("life_filing" if filed_term else "catalog_only"),
        "actuarial": actuarial,
        "face_amount": face,
        "medical": medical.to_metadata(),
        "financial": financial.to_metadata(),
        "life_reinsurance": reinsurance.to_metadata(),
        "facultative_required": reinsurance.facultative_required,
        "personal_factors": {k: v for k, v in factors.__dict__.items() if k != "findings"},
        "tiv": face,
        "insurance_line": InsuranceLine.LIFE.value,
        "personal_lines": True,
        "uw_decision_hint": medical.decision.value,
        "outcome": normalize_decision(medical.decision).value,
        "conditions": [],
    }
    if medical.require_aps:
        meta["conditions"].append("APS (attending physician statement) required before bind")
    if medical.require_paramed:
        meta["conditions"].append("Paramedical exam required")
    if reinsurance.facultative_required:
        meta["conditions"].append("Facultative reinsurance must be placed before bind")
    if financial.riders:
        meta["conditions"].append("Riders: " + ", ".join(financial.riders))

    if not eligible:
        ineligibility = [r for r in reasons if r] or ["Life quote ineligible"]
    else:
        ineligibility = []

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.LIFE,
        base_premium=round(base_premium, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / (face / 100.0), 4),
        eligible=eligible,
        ineligibility_reasons=ineligibility,
        metadata=meta,
    )
