"""Commercial actuarial rating — dedicated manuals for cyber, auto, marine, crime,
builders risk, surety, NCCI WC, and multi-section packages (BOP/CPP).

Exposure bases and factor tables are representative ISO/NCCI-style manuals for
production UW worksheets (not TIV+COPE proxies).
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.insurance.commercial_lobs import get_commercial_line
from insureflow.models.agents import UnderwritingMemo
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.underwriting.personal_lines import _blob, parse_insurance_line

# ---------------------------------------------------------------------------
# Manual tables
# ---------------------------------------------------------------------------

# Cyber: rate per $100 of limit (first-party + third-party blend)
CYBER_LOSS_COST = 0.85
CYBER_LCM = 2.20
CYBER_MIN = 2_500.0

# Commercial auto: rate per power unit + liability CSL
AUTO_LIABILITY_PER_UNIT = 1_850.0
AUTO_PD_PER_UNIT = 620.0
AUTO_MIN = 1_200.0

# Inland marine: rate per $100 of scheduled values
INLAND_MARINE_LOSS_COST = 0.55
INLAND_MARINE_LCM = 2.00
INLAND_MARINE_MIN = 750.0

# Crime: rate per $100 of employee count * fidelity limit proxy
CRIME_PER_EMPLOYEE = 18.0
CRIME_LIMIT_RATE = 0.12  # per $100 of fidelity limit
CRIME_LCM = 2.15
CRIME_MIN = 500.0

# Builders risk: rate per $100 of completed value (course of construction)
BUILDERS_RISK_LOSS_COST = 0.42
BUILDERS_RISK_LCM = 2.05
BUILDERS_RISK_MIN = 1_000.0

# Surety: rate as % of bond penalty (contract surety)
SURETY_RATE_PCT = 1.5  # of bond amount
SURETY_MIN = 250.0

# NCCI WC: class code → manual rate per $100 payroll
WC_CLASS_RATES: dict[str, float] = {
    "8810": 0.35,  # clerical
    "8742": 0.55,  # sales
    "8017": 1.85,  # retail
    "8380": 3.20,  # auto service
    "5403": 8.50,  # carpentry
    "5606": 5.40,  # contractor executive
    "7219": 6.80,  # trucking
    "8829": 1.10,  # nursing home
    "8832": 0.95,  # physician
    "9015": 2.40,  # buildings — operations
    "0042": 4.10,  # landscaping
    "5183": 3.60,  # plumbing
    "5190": 2.90,  # electrical
    "5221": 7.20,  # concrete
    "5474": 9.10,  # painting
}
WC_DEFAULT_CLASS = "9015"
WC_DEFAULT_RATE = 3.25
WC_EXPENSE_CONSTANT = 160.0
WC_MIN = 1_000.0

# Package section weights (BOP / CPP)
BOP_SECTIONS = (
    ("property", 0.55, InsuranceLine.COMMERCIAL_PROPERTY),
    ("general_liability", 0.35, InsuranceLine.GENERAL_LIABILITY),
    ("business_income", 0.10, InsuranceLine.COMMERCIAL_PROPERTY),
)
CPP_SECTIONS = (
    ("property", 0.40, InsuranceLine.COMMERCIAL_PROPERTY),
    ("general_liability", 0.30, InsuranceLine.GENERAL_LIABILITY),
    ("crime", 0.10, InsuranceLine.CRIME),
    ("commercial_auto", 0.20, InsuranceLine.COMMERCIAL_AUTO),
)

EXTENDED_COMMERCIAL_LINES = frozenset(
    {
        InsuranceLine.CYBER,
        InsuranceLine.COMMERCIAL_AUTO,
        InsuranceLine.INLAND_MARINE,
        InsuranceLine.CRIME,
        InsuranceLine.BUILDERS_RISK,
        InsuranceLine.SURETY,
    }
)


def resolve_quote_line(
    *,
    commercial_product_id: str | None = None,
    insurance_line: str | None = None,
    product_hint: str | None = None,
    text_blob: str = "",
) -> InsuranceLine:
    """Prefer UW picker (product id / insurance_line / rating_line) over re-detection."""
    # 1) Explicit commercial product from cascading picker
    if commercial_product_id:
        line = get_commercial_line(commercial_product_id)
        if line:
            for key in (line.get("rating_line"), line.get("insurance_line"), line.get("checklist_lob")):
                parsed = parse_insurance_line(str(key or ""))
                if parsed is not None:
                    return parsed

    # 2) Explicit insurance_line from request
    if insurance_line:
        parsed = parse_insurance_line(insurance_line)
        if parsed is not None:
            return parsed
        line = get_commercial_line(insurance_line)
        if line:
            for key in (line.get("rating_line"), line.get("insurance_line")):
                parsed = parse_insurance_line(str(key or ""))
                if parsed is not None:
                    return parsed

    # 3) product_hint
    if product_hint:
        parsed = parse_insurance_line(product_hint)
        if parsed is not None:
            return parsed

    # 4) Fall back to content detection
    from insureflow.underwriting.personal_lines import detect_insurance_line

    return detect_insurance_line(text_blob, insurance_line or product_hint or "")


def _money(blob: str, *labels: str) -> float:
    for label in labels:
        m = re.search(rf"{re.escape(label)}\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)", blob, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return 0.0


def _employees(bundle: SubmissionBundle) -> int:
    if bundle.structured and bundle.structured.financial:
        n = getattr(bundle.structured.financial, "employee_count", None)
        if n:
            return max(int(n), 1)
    blob = _blob(bundle)
    m = re.search(r"(?:employees?|fte|headcount)\s*[:=]?\s*(\d{1,5})", blob, re.I)
    if m:
        return max(int(m.group(1)), 1)
    return 25


def _payroll(bundle: SubmissionBundle) -> float:
    if bundle.structured and bundle.structured.financial:
        fin = bundle.structured.financial
        for attr in ("payroll", "annual_payroll", "total_payroll"):
            v = getattr(fin, attr, None)
            if v and float(v) > 0:
                return float(v)
        rev = float(getattr(fin, "annual_revenue", 0) or 0)
        emp = _employees(bundle)
        if rev > 0:
            return max(rev * 0.35, emp * 45_000.0)
    blob = _blob(bundle)
    v = _money(blob, "payroll", "annual payroll", "total payroll", "remuneration")
    if v > 0:
        return v
    return float(_employees(bundle) * 55_000.0)


def _class_code(bundle: SubmissionBundle) -> str:
    if bundle.structured and bundle.structured.risk_profile:
        code = (bundle.structured.risk_profile.ncci_class_code or "").strip()
        if code:
            # take first 4 digits
            digits = re.sub(r"\D", "", code)
            if len(digits) >= 4:
                return digits[:4]
    blob = _blob(bundle)
    m = re.search(r"(?:ncci|class\s*code|class)\s*[#:=]?\s*(\d{4})", blob, re.I)
    if m:
        return m.group(1)
    return WC_DEFAULT_CLASS


def _emod(bundle: SubmissionBundle) -> float:
    """Experience modification factor — from package or credibility-blended proxy."""
    blob = _blob(bundle)
    m = re.search(r"(?:e-?mod|experience\s*mod(?:ification)?|x-?mod)\s*[:=]?\s*(\d+\.?\d*)", blob, re.I)
    if m:
        try:
            val = float(m.group(1))
            if 0.5 <= val <= 2.5:
                return val
        except ValueError:
            pass
    # Credibility-blended proxy from loss ratio
    lr = 0.55
    claims_n = 0
    if bundle.structured and bundle.structured.financial and bundle.structured.financial.loss_run:
        lr_map = bundle.structured.financial.loss_run.loss_ratios or {}
        if lr_map:
            lr = max(lr_map.values())
        claims_n = int(bundle.structured.financial.loss_run.total_claims or 0)
    if bundle.structured and bundle.structured.risk_profile:
        claims_n = max(claims_n, len(bundle.structured.risk_profile.prior_claims or []))
    raw = 1.0 + min(max((lr - 0.55) * 0.4, -0.25), 0.50)
    z = claims_n / (claims_n + 8.0) if claims_n else 0.0
    return round((1.0 - z) * 1.0 + z * raw, 3)


def _vehicle_count(bundle: SubmissionBundle) -> int:
    blob = _blob(bundle)
    m = re.search(r"(?:vehicles?|power\s*units?|fleet\s*size)\s*[:=]?\s*(\d{1,4})", blob, re.I)
    if m:
        return max(int(m.group(1)), 1)
    # VIN count heuristic
    vins = re.findall(r"\b[A-HJ-NPR-Z0-9]{17}\b", blob.upper())
    if vins:
        return max(len(set(vins)), 1)
    return 5


def _tiv(bundle: SubmissionBundle) -> float:
    total = 0.0
    if bundle.structured:
        for loc in bundle.structured.locations or []:
            total += float(loc.building_value or 0) + float(loc.contents_value or 0) + float(loc.bi_value or 0)
        for sov in bundle.structured.schedule_of_values or []:
            for item in sov.items or []:
                total += float(item.value or 0)
        if total <= 0:
            for cov in bundle.structured.coverages or []:
                total = max(total, float(cov.limit_amount or 0))
    if total <= 0:
        total = _money(_blob(bundle), "total insurable value", "tiv", "completed value", "contract value", "bond amount")
    return max(total, 0.0)


def _limit(bundle: SubmissionBundle, default: float = 1_000_000.0) -> float:
    if bundle.structured:
        for cov in bundle.structured.coverages or []:
            if (cov.limit_amount or 0) > 0:
                return float(cov.limit_amount)
    v = _money(_blob(bundle), "aggregate limit", "policy limit", "limit of liability", "cyber limit")
    return v if v > 0 else default


def rate_extended_commercial(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    line: InsuranceLine,
    *,
    state: str = "",
    schedule_mod_pct: float = 0.0,
    market_mod_pct: float = 0.0,
) -> QuoteResult | None:
    """Rate cyber / commercial auto / inland marine / crime / builders risk / surety."""
    if line not in EXTENDED_COMMERCIAL_LINES:
        return None

    components: list[RateComponent] = []
    meta: dict[str, Any] = {"insurance_line": line.value, "state": state}

    if line == InsuranceLine.CYBER:
        exposure = _limit(bundle, 2_000_000.0)
        base = (exposure / 100.0) * CYBER_LOSS_COST * CYBER_LCM
        components += [
            RateComponent("cyber_loss_cost", CYBER_LOSS_COST, "per_100_limit"),
            RateComponent("cyber_lcm", CYBER_LCM, "expense_profit"),
        ]
        meta.update({"exposure_basis": "cyber_limit", "exposure": exposure, "rating_engine": "cyber_manual"})
        min_p = CYBER_MIN

    elif line == InsuranceLine.COMMERCIAL_AUTO:
        units = _vehicle_count(bundle)
        liab = units * AUTO_LIABILITY_PER_UNIT
        pd = units * AUTO_PD_PER_UNIT
        base = liab + pd
        components += [
            RateComponent("auto_liability", round(liab, 2), "per_power_unit", 0.0),
            RateComponent("auto_physical_damage", round(pd, 2), "per_power_unit", 0.0),
            RateComponent("fleet_units", float(units), "count", 0.0),
        ]
        meta.update({"exposure_basis": "power_units", "units": units, "rating_engine": "commercial_auto_manual"})
        min_p = AUTO_MIN
        # Apply guide surcharges additively (capped)
        try:
            from insureflow.rating.surcharges import SurchargeBasis, builtin_commercial_auto_surcharges, evaluate_surcharges

            sur = evaluate_surcharges(
                builtin_commercial_auto_surcharges(),
                premium_by_basis={SurchargeBasis.LIABILITY: liab, SurchargeBasis.PREMIUM: base},
            )
            if sur.total_surcharge:
                base += sur.total_surcharge
                meta["surcharges"] = sur.to_dict()
                components.append(RateComponent("auto_surcharges", sur.total_surcharge, "guide_surcharge", 0.0))
        except Exception:
            pass

    elif line == InsuranceLine.INLAND_MARINE:
        exposure = _tiv(bundle) or 500_000.0
        base = (exposure / 100.0) * INLAND_MARINE_LOSS_COST * INLAND_MARINE_LCM
        components += [
            RateComponent("inland_marine_loss_cost", INLAND_MARINE_LOSS_COST, "per_100_values"),
            RateComponent("inland_marine_lcm", INLAND_MARINE_LCM, "expense_profit"),
        ]
        meta.update({"exposure_basis": "scheduled_values", "exposure": exposure, "rating_engine": "inland_marine_manual"})
        min_p = INLAND_MARINE_MIN

    elif line == InsuranceLine.CRIME:
        emp = _employees(bundle)
        fidelity_limit = _limit(bundle, 250_000.0)
        base = emp * CRIME_PER_EMPLOYEE + (fidelity_limit / 100.0) * CRIME_LIMIT_RATE * CRIME_LCM
        components += [
            RateComponent("crime_per_employee", CRIME_PER_EMPLOYEE, "employees"),
            RateComponent("crime_fidelity_rate", CRIME_LIMIT_RATE, "per_100_limit"),
            RateComponent("employee_count", float(emp), "count"),
        ]
        meta.update(
            {
                "exposure_basis": "employees_x_fidelity",
                "employees": emp,
                "fidelity_limit": fidelity_limit,
                "rating_engine": "crime_fidelity_manual",
            }
        )
        min_p = CRIME_MIN

    elif line == InsuranceLine.BUILDERS_RISK:
        exposure = _tiv(bundle) or _money(_blob(bundle), "completed value", "contract value", "project value") or 2_000_000.0
        base = (exposure / 100.0) * BUILDERS_RISK_LOSS_COST * BUILDERS_RISK_LCM
        components += [
            RateComponent("builders_risk_loss_cost", BUILDERS_RISK_LOSS_COST, "per_100_completed_value"),
            RateComponent("builders_risk_lcm", BUILDERS_RISK_LCM, "expense_profit"),
        ]
        meta.update({"exposure_basis": "completed_value", "exposure": exposure, "rating_engine": "builders_risk_manual"})
        min_p = BUILDERS_RISK_MIN

    elif line == InsuranceLine.SURETY:
        bond = _money(_blob(bundle), "bond amount", "bond penalty", "contract amount", "penal sum") or _tiv(bundle) or 500_000.0
        base = bond * (SURETY_RATE_PCT / 100.0)
        components += [
            RateComponent("surety_rate_pct", SURETY_RATE_PCT, "pct_of_bond"),
            RateComponent("bond_penalty", bond, "bond_amount"),
        ]
        meta.update({"exposure_basis": "bond_penalty", "bond_amount": bond, "rating_engine": "surety_rate_manual"})
        min_p = SURETY_MIN

    else:
        return None

    adjusted = base * (1 + market_mod_pct / 100.0) * (1 + schedule_mod_pct / 100.0)
    adjusted = max(round(adjusted, 2), min_p)
    if market_mod_pct:
        components.append(RateComponent("market_cycle", market_mod_pct, "market", market_mod_pct))
    if schedule_mod_pct:
        components.append(RateComponent("uw_schedule", schedule_mod_pct, "uw_discretion", schedule_mod_pct))

    exposure_for_rate = float(meta.get("exposure") or meta.get("bond_amount") or meta.get("fidelity_limit") or _tiv(bundle) or 100_000.0)
    if line == InsuranceLine.COMMERCIAL_AUTO:
        exposure_for_rate = float(meta.get("units") or 1) * 50_000.0

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=line,
        base_premium=round(base, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / max(exposure_for_rate / 100.0, 1), 4),
        eligible=True,
        metadata=meta,
    )


def rate_workers_comp_ncci(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    *,
    state: str = "",
    schedule_mod_pct: float = 0.0,
    market_mod_pct: float = 0.0,
) -> QuoteResult:
    """NCCI-style WC: (payroll/100) × class rate × e-mod × LCM factors."""
    payroll = _payroll(bundle)
    class_code = _class_code(bundle)
    manual_rate = WC_CLASS_RATES.get(class_code, WC_DEFAULT_RATE)
    emod = _emod(bundle)
    state_rel = {"CA": 1.15, "NY": 1.10, "FL": 1.00, "TX": 0.95, "IL": 0.92}.get(state.upper(), 1.0) if state else 1.0

    manual_premium = (payroll / 100.0) * manual_rate
    subject = manual_premium * emod * state_rel
    adjusted = subject * (1 + market_mod_pct / 100.0) * (1 + schedule_mod_pct / 100.0) + WC_EXPENSE_CONSTANT
    adjusted = max(round(adjusted, 2), WC_MIN)

    components = [
        RateComponent("ncci_class_rate", manual_rate, f"class_{class_code}"),
        RateComponent("payroll", payroll, "annual_payroll"),
        RateComponent("experience_mod", emod, "ncci_emod", (emod - 1.0) * 100),
        RateComponent("state_relativity", state_rel, "state"),
        RateComponent("expense_constant", WC_EXPENSE_CONSTANT, "flat"),
    ]
    if schedule_mod_pct:
        components.append(RateComponent("uw_schedule", schedule_mod_pct, "uw_discretion", schedule_mod_pct))

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.WORKERS_COMP,
        base_premium=round(manual_premium, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / max(payroll / 100.0, 1), 4),
        eligible=True,
        metadata={
            "exposure_basis": "payroll",
            "payroll": payroll,
            "ncci_class_code": class_code,
            "manual_rate": manual_rate,
            "experience_mod": emod,
            "state_relativity": state_rel,
            "rating_engine": "ncci_class_emod",
            "insurance_line": "workers_comp",
        },
    )


def rate_package_policy(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    line: InsuranceLine,
    *,
    state: str = "",
    schedule_mod_pct: float = 0.0,
    market_mod_pct: float = 0.0,
    section_rater: Any = None,
) -> QuoteResult:
    """BOP / CPP: price as sum of coverage sections, not a single blob."""
    sections_def = BOP_SECTIONS if line == InsuranceLine.BOP else CPP_SECTIONS
    section_rows: list[dict[str, Any]] = []
    total_base = 0.0
    total_adj = 0.0
    components: list[RateComponent] = []

    tiv = _tiv(bundle) or 1_500_000.0
    sales = 0.0
    if bundle.structured and bundle.structured.financial:
        sales = float(bundle.structured.financial.annual_revenue or 0)
    if sales <= 0:
        sales = max(tiv * 0.4, 500_000.0)

    for section_id, weight, section_line in sections_def:
        if section_line == InsuranceLine.COMMERCIAL_PROPERTY:
            # Property section: TIV × loss cost × LCM × weight
            section_prem = (tiv / 100.0) * 0.28 * 2.10 * weight
        elif section_line == InsuranceLine.GENERAL_LIABILITY:
            section_prem = (sales / 1000.0) * 0.42 * weight
        elif section_line == InsuranceLine.CRIME:
            section_prem = _employees(bundle) * CRIME_PER_EMPLOYEE * weight * 2
        elif section_line == InsuranceLine.COMMERCIAL_AUTO:
            section_prem = _vehicle_count(bundle) * (AUTO_LIABILITY_PER_UNIT * 0.5) * weight
        else:
            section_prem = (tiv / 100.0) * 0.20 * weight

        section_adj = section_prem * (1 + market_mod_pct / 100.0) * (1 + schedule_mod_pct / 100.0)
        total_base += section_prem
        total_adj += section_adj
        section_rows.append(
            {
                "section": section_id,
                "line": section_line.value,
                "weight": weight,
                "base_premium": round(section_prem, 2),
                "adjusted_premium": round(section_adj, 2),
            }
        )
        components.append(
            RateComponent(
                name=f"section_{section_id}",
                amount=round(section_adj, 2),
                basis=section_line.value,
                modifier_pct=weight * 100,
            )
        )

    package_min = 1_500.0 if line == InsuranceLine.BOP else 2_500.0
    adjusted = max(round(total_adj, 2), package_min)

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=line,
        base_premium=round(total_base, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / max(tiv / 100.0, 1), 4),
        eligible=True,
        metadata={
            "exposure_basis": "multi_section",
            "rating_engine": "package_section_rating",
            "insurance_line": line.value,
            "package_sections": section_rows,
            "tiv": tiv,
            "sales": sales,
        },
    )


def is_extended_commercial(line: InsuranceLine) -> bool:
    return line in EXTENDED_COMMERCIAL_LINES


def is_package_line(line: InsuranceLine) -> bool:
    return line in (InsuranceLine.BOP, InsuranceLine.COMMERCIAL_PACKAGE)
