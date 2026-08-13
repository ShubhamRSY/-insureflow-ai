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

# ISO CGL: rate per $1,000 gross sales / receipts (not TIV)
GL_RATE_PER_1K_SALES = 0.42
GL_LCM = 2.25
GL_MIN = 750.0
GL_ILF: dict[float, float] = {
    300_000.0: 1.00,
    500_000.0: 1.15,
    1_000_000.0: 1.35,
    2_000_000.0: 1.55,
    5_000_000.0: 1.85,
}

# Umbrella: percent of underlying GL + per-million excess
UMBRELLA_PCT_OF_UNDERLYING = 0.18
UMBRELLA_PER_MILLION = 850.0
UMBRELLA_MIN = 1_250.0

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
        InsuranceLine.GENERAL_LIABILITY,
        InsuranceLine.UMBRELLA,
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


def _ineligible(bundle: SubmissionBundle, line: InsuranceLine, reasons: list[str], *, meta: dict[str, Any] | None = None) -> QuoteResult:
    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=line,
        base_premium=0.0,
        adjusted_premium=0.0,
        eligible=False,
        ineligibility_reasons=list(reasons),
        metadata={"invented_exposure": False, "exposure_unknown": True, **(meta or {})},
    )


def _employees(bundle: SubmissionBundle) -> int | None:
    if bundle.structured and bundle.structured.financial:
        n = getattr(bundle.structured.financial, "employee_count", None)
        if n:
            return max(int(n), 1)
    blob = _blob(bundle)
    m = re.search(r"(?:employees?|fte|headcount)\s*[:=]?\s*(\d{1,5})", blob, re.I)
    if m:
        return max(int(m.group(1)), 1)
    return None


def _payroll(bundle: SubmissionBundle) -> float | None:
    if bundle.structured and bundle.structured.financial:
        fin = bundle.structured.financial
        for attr in ("payroll", "annual_payroll", "total_payroll"):
            v = getattr(fin, attr, None)
            if v and float(v) > 0:
                return float(v)
    blob = _blob(bundle)
    v = _money(blob, "payroll", "annual payroll", "total payroll", "remuneration")
    if v > 0:
        return v
    return None


def _sales(bundle: SubmissionBundle) -> float | None:
    if bundle.structured and bundle.structured.financial:
        rev = float(bundle.structured.financial.annual_revenue or 0)
        if rev > 0:
            return rev
    blob = _blob(bundle)
    v = _money(blob, "gross sales", "annual sales", "gross receipts", "receipts", "annual revenue", "revenue")
    return v if v > 0 else None


def _class_code(bundle: SubmissionBundle) -> str | None:
    if bundle.structured and bundle.structured.risk_profile:
        code = (bundle.structured.risk_profile.ncci_class_code or "").strip()
        if code:
            digits = re.sub(r"\D", "", code)
            if len(digits) >= 4:
                return digits[:4]
    blob = _blob(bundle)
    m = re.search(r"(?:ncci|class\s*code|class)\s*[#:=]?\s*(\d{4})", blob, re.I)
    if m:
        return m.group(1)
    return None


def _emod(bundle: SubmissionBundle, oracle_emod: float | None = None) -> tuple[float | None, str]:
    """Experience modification — package or NCCI oracle only. Never invent from LR."""
    if oracle_emod is not None:
        try:
            val = float(oracle_emod)
            if 0.5 <= val <= 2.5:
                return val, "ncci_oracle"
        except (TypeError, ValueError):
            pass
    blob = _blob(bundle)
    m = re.search(r"(?:e-?mod|experience\s*mod(?:ification)?|x-?mod)\s*[:=]?\s*(\d+\.?\d*)", blob, re.I)
    if m:
        try:
            val = float(m.group(1))
            if 0.5 <= val <= 2.5:
                return val, "package"
        except ValueError:
            pass
    if re.search(r"new venture|no experience(?:\s+mod)?|unrated\s+risk|emod\s*(?:is|=|:)\s*1\.00", blob, re.I):
        return 1.0, "new_venture_unity"
    return None, ""


def _vehicle_count(bundle: SubmissionBundle) -> int | None:
    blob = _blob(bundle)
    m = re.search(r"(?:vehicles?|power\s*units?|fleet\s*size)\s*[:=]?\s*(\d{1,4})", blob, re.I)
    if m:
        return max(int(m.group(1)), 1)
    vins = re.findall(r"\b[A-HJ-NPR-Z0-9]{17}\b", blob.upper())
    if vins:
        return max(len(set(vins)), 1)
    return None


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


def _limit(bundle: SubmissionBundle, *extra_labels: str) -> float | None:
    if bundle.structured:
        for cov in bundle.structured.coverages or []:
            if (cov.limit_amount or 0) > 0:
                return float(cov.limit_amount)
    labels = ("aggregate limit", "policy limit", "limit of liability", "cyber limit", "occurrence limit", *extra_labels)
    v = _money(_blob(bundle), *labels)
    return v if v > 0 else None


def _ilf(limit: float) -> float:
    chosen = 1.0
    for threshold, factor in sorted(GL_ILF.items()):
        if limit >= threshold:
            chosen = factor
    return chosen


def rate_general_liability_iso(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    *,
    state: str = "",
    schedule_mod_pct: float = 0.0,
    market_mod_pct: float = 0.0,
) -> QuoteResult:
    """ISO CGL: (sales / 1,000) × loss cost × LCM × ILF. Never TIV+COPE."""
    sales = _sales(bundle)
    limit = _limit(bundle, "gl limit", "cgl limit")
    if not sales:
        return _ineligible(
            bundle,
            InsuranceLine.GENERAL_LIABILITY,
            ["Gross sales/receipts missing — cannot rate CGL (TIV is not a GL exposure)"],
            meta={"rating_engine": "iso_gl_sales", "insurance_line": "general_liability", "state": state},
        )
    if not limit:
        return _ineligible(
            bundle,
            InsuranceLine.GENERAL_LIABILITY,
            ["CGL occurrence/aggregate limit missing — cannot apply increased-limits factor"],
            meta={"rating_engine": "iso_gl_sales", "insurance_line": "general_liability", "sales": sales, "state": state},
        )
    ilf = _ilf(limit)
    base = (sales / 1000.0) * GL_RATE_PER_1K_SALES * GL_LCM * ilf
    components = [
        RateComponent("gl_rate_per_1k_sales", GL_RATE_PER_1K_SALES, "iso_sales"),
        RateComponent("gl_lcm", GL_LCM, "expense_profit"),
        RateComponent("increased_limits_factor", ilf, f"limit={limit:,.0f}"),
        RateComponent("gross_sales", sales, "receipts"),
    ]
    adjusted = base * (1 + market_mod_pct / 100.0) * (1 + schedule_mod_pct / 100.0)
    adjusted = max(round(adjusted, 2), GL_MIN)
    if market_mod_pct:
        components.append(RateComponent("market_cycle", market_mod_pct, "market", market_mod_pct))
    if schedule_mod_pct:
        components.append(RateComponent("uw_schedule", schedule_mod_pct, "uw_discretion", schedule_mod_pct))
    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.GENERAL_LIABILITY,
        base_premium=round(base, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / max(sales / 100.0, 1), 4),
        eligible=True,
        metadata={
            "exposure_basis": "gross_sales",
            "sales": sales,
            "gl_limit": limit,
            "ilf": ilf,
            "rating_engine": "iso_gl_sales",
            "insurance_line": "general_liability",
            "state": state,
        },
    )


def rate_umbrella(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    *,
    state: str = "",
    schedule_mod_pct: float = 0.0,
    market_mod_pct: float = 0.0,
) -> QuoteResult:
    """Umbrella/excess: % of underlying GL + per-million excess. Not property TIV."""
    umb_limit = _limit(bundle, "umbrella limit", "excess limit")
    underlying = _money(_blob(bundle), "underlying premium", "primary gl premium", "underlying gl premium")
    gl = rate_general_liability_iso(bundle, memo, state=state, schedule_mod_pct=0.0, market_mod_pct=0.0)
    if underlying <= 0 and gl.eligible:
        underlying = float(gl.adjusted_premium or 0)
    if not umb_limit:
        return _ineligible(
            bundle,
            InsuranceLine.UMBRELLA,
            ["Umbrella/excess limit missing — cannot rate attachment"],
            meta={"rating_engine": "iso_umbrella", "insurance_line": "umbrella", "state": state},
        )
    if underlying <= 0:
        return _ineligible(
            bundle,
            InsuranceLine.UMBRELLA,
            ["Underlying GL premium/sales missing — umbrella is not rated on property TIV"],
            meta={"rating_engine": "iso_umbrella", "insurance_line": "umbrella", "umbrella_limit": umb_limit, "state": state},
        )
    millions = max(umb_limit / 1_000_000.0, 1.0)
    base = max(underlying * UMBRELLA_PCT_OF_UNDERLYING, millions * UMBRELLA_PER_MILLION)
    components = [
        RateComponent("underlying_premium", underlying, "primary_gl"),
        RateComponent("umbrella_pct", UMBRELLA_PCT_OF_UNDERLYING, "of_underlying"),
        RateComponent("per_million_excess", UMBRELLA_PER_MILLION, f"{millions:.1f}m"),
    ]
    adjusted = base * (1 + market_mod_pct / 100.0) * (1 + schedule_mod_pct / 100.0)
    adjusted = max(round(adjusted, 2), UMBRELLA_MIN)
    if market_mod_pct:
        components.append(RateComponent("market_cycle", market_mod_pct, "market", market_mod_pct))
    if schedule_mod_pct:
        components.append(RateComponent("uw_schedule", schedule_mod_pct, "uw_discretion", schedule_mod_pct))
    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.UMBRELLA,
        base_premium=round(base, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / max(umb_limit / 100.0, 1), 4),
        eligible=True,
        metadata={
            "exposure_basis": "underlying_gl",
            "underlying_premium": underlying,
            "umbrella_limit": umb_limit,
            "rating_engine": "iso_umbrella",
            "insurance_line": "umbrella",
            "state": state,
            "underlying_gl": {
                "eligible": gl.eligible,
                "premium": gl.adjusted_premium,
                "ineligibility_reasons": list(gl.ineligibility_reasons or []),
            },
        },
    )


def rate_extended_commercial(
    bundle: SubmissionBundle,
    memo: UnderwritingMemo,
    line: InsuranceLine,
    *,
    state: str = "",
    schedule_mod_pct: float = 0.0,
    market_mod_pct: float = 0.0,
) -> QuoteResult | None:
    """Rate cyber / auto / marine / crime / BR / surety / CGL / umbrella. Fail-closed on missing bases."""
    if line not in EXTENDED_COMMERCIAL_LINES:
        return None

    if line == InsuranceLine.GENERAL_LIABILITY:
        return rate_general_liability_iso(bundle, memo, state=state, schedule_mod_pct=schedule_mod_pct, market_mod_pct=market_mod_pct)
    if line == InsuranceLine.UMBRELLA:
        return rate_umbrella(bundle, memo, state=state, schedule_mod_pct=schedule_mod_pct, market_mod_pct=market_mod_pct)

    components: list[RateComponent] = []
    meta: dict[str, Any] = {"insurance_line": line.value, "state": state, "invented_exposure": False}

    if line == InsuranceLine.CYBER:
        exposure = _limit(bundle, "cyber limit")
        if not exposure:
            return _ineligible(bundle, line, ["Cyber limit missing — will not invent $1M"], meta={**meta, "rating_engine": "cyber_manual"})
        base = (exposure / 100.0) * CYBER_LOSS_COST * CYBER_LCM
        components += [
            RateComponent("cyber_loss_cost", CYBER_LOSS_COST, "per_100_limit"),
            RateComponent("cyber_lcm", CYBER_LCM, "expense_profit"),
        ]
        meta.update({"exposure_basis": "cyber_limit", "exposure": exposure, "rating_engine": "cyber_manual"})
        min_p = CYBER_MIN

    elif line == InsuranceLine.COMMERCIAL_AUTO:
        units = _vehicle_count(bundle)
        if not units:
            return _ineligible(
                bundle,
                line,
                ["Power units / fleet size missing — will not invent vehicle count"],
                meta={**meta, "rating_engine": "commercial_auto_manual"},
            )
        liab = units * AUTO_LIABILITY_PER_UNIT
        pd = units * AUTO_PD_PER_UNIT
        base = liab + pd
        components += [
            RateComponent("auto_liability", round(liab, 2), "per_power_unit", 0.0),
            RateComponent("auto_physical_damage", round(pd, 2), "per_power_unit", 0.0),
            RateComponent("fleet_units", float(units), "count", 0.0),
        ]
        meta.update({"exposure_basis": "power_units", "units": units, "rating_engine": "commercial_auto_manual", "mvr_required": True})
        min_p = AUTO_MIN
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
        exposure = _tiv(bundle)
        if exposure <= 0:
            return _ineligible(
                bundle,
                line,
                ["Scheduled values / TIV missing — will not invent inland marine exposure"],
                meta={**meta, "rating_engine": "inland_marine_manual"},
            )
        base = (exposure / 100.0) * INLAND_MARINE_LOSS_COST * INLAND_MARINE_LCM
        components += [
            RateComponent("inland_marine_loss_cost", INLAND_MARINE_LOSS_COST, "per_100_values"),
            RateComponent("inland_marine_lcm", INLAND_MARINE_LCM, "expense_profit"),
        ]
        meta.update({"exposure_basis": "scheduled_values", "exposure": exposure, "rating_engine": "inland_marine_manual"})
        min_p = INLAND_MARINE_MIN

    elif line == InsuranceLine.CRIME:
        emp = _employees(bundle)
        fidelity_limit = _limit(bundle, "fidelity limit", "crime limit")
        if not emp:
            return _ineligible(bundle, line, ["Employee count missing — will not invent headcount"], meta={**meta, "rating_engine": "crime_fidelity_manual"})
        if not fidelity_limit:
            return _ineligible(
                bundle,
                line,
                ["Fidelity / crime limit missing — will not invent $250k"],
                meta={**meta, "rating_engine": "crime_fidelity_manual", "employees": emp},
            )
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
        exposure = _tiv(bundle) or _money(_blob(bundle), "completed value", "contract value", "project value")
        if not exposure:
            return _ineligible(
                bundle,
                line,
                ["Completed / contract value missing — will not invent $2M builders risk"],
                meta={**meta, "rating_engine": "builders_risk_manual"},
            )
        base = (exposure / 100.0) * BUILDERS_RISK_LOSS_COST * BUILDERS_RISK_LCM
        components += [
            RateComponent("builders_risk_loss_cost", BUILDERS_RISK_LOSS_COST, "per_100_completed_value"),
            RateComponent("builders_risk_lcm", BUILDERS_RISK_LCM, "expense_profit"),
        ]
        meta.update({"exposure_basis": "completed_value", "exposure": exposure, "rating_engine": "builders_risk_manual"})
        min_p = BUILDERS_RISK_MIN

    elif line == InsuranceLine.SURETY:
        bond = _money(_blob(bundle), "bond amount", "bond penalty", "contract amount", "penal sum") or _tiv(bundle)
        if not bond:
            return _ineligible(
                bundle,
                line,
                ["Bond penalty / contract amount missing — will not invent surety exposure"],
                meta={**meta, "rating_engine": "surety_rate_manual"},
            )
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

    exposure_for_rate = float(meta.get("exposure") or meta.get("bond_amount") or meta.get("fidelity_limit") or _tiv(bundle) or 0)
    if line == InsuranceLine.COMMERCIAL_AUTO:
        exposure_for_rate = float(meta.get("units") or 1) * 50_000.0

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=line,
        base_premium=round(base, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / max(exposure_for_rate / 100.0, 1), 4) if exposure_for_rate else 0.0,
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
    experience_mod: float | None = None,
) -> QuoteResult:
    """NCCI-style WC: (payroll/100) × class rate × e-mod. No invented payroll or e-mod."""
    payroll = _payroll(bundle)
    class_code = _class_code(bundle)
    emod, emod_source = _emod(bundle, oracle_emod=experience_mod)
    missing: list[str] = []
    if not payroll:
        missing.append("Annual payroll / remuneration missing — will not invent from headcount")
    if not class_code:
        missing.append("NCCI class code missing — will not invent a default class")
    if emod is None:
        missing.append("Experience modification missing — NCCI e-mod or worksheet required (will not invent from loss ratio)")
    if missing or payroll is None or not class_code or emod is None:
        return _ineligible(
            bundle,
            InsuranceLine.WORKERS_COMP,
            missing or ["Workers comp exposure incomplete"],
            meta={
                "rating_engine": "ncci_class_emod",
                "insurance_line": "workers_comp",
                "payroll": payroll or 0,
                "ncci_class_code": class_code or "",
                "experience_mod": emod,
                "emod_source": emod_source,
                "state": state,
            },
        )

    pay = float(payroll)
    klass = str(class_code)
    exp_mod = float(emod)
    manual_rate = WC_CLASS_RATES.get(klass, WC_DEFAULT_RATE)
    state_rel = {"CA": 1.15, "NY": 1.10, "FL": 1.00, "TX": 0.95, "IL": 0.92}.get((state or "").upper(), 1.0)

    manual_premium = (pay / 100.0) * manual_rate
    subject = manual_premium * exp_mod * state_rel
    adjusted = subject * (1 + market_mod_pct / 100.0) * (1 + schedule_mod_pct / 100.0) + WC_EXPENSE_CONSTANT
    adjusted = max(round(adjusted, 2), WC_MIN)

    components = [
        RateComponent("ncci_class_rate", manual_rate, f"class_{klass}"),
        RateComponent("payroll", pay, "annual_payroll"),
        RateComponent("experience_mod", exp_mod, emod_source or "ncci_emod", (exp_mod - 1.0) * 100),
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
        rate_per_100_tiv=round(adjusted / max(pay / 100.0, 1), 4),
        eligible=True,
        metadata={
            "exposure_basis": "payroll",
            "payroll": pay,
            "ncci_class_code": klass,
            "manual_rate": manual_rate,
            "experience_mod": exp_mod,
            "emod_source": emod_source,
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
    """BOP / CPP: price as sum of coverage sections. Skip sections with unknown exposure."""
    sections_def = BOP_SECTIONS if line == InsuranceLine.BOP else CPP_SECTIONS
    section_rows: list[dict[str, Any]] = []
    total_base = 0.0
    total_adj = 0.0
    components: list[RateComponent] = []
    skipped: list[str] = []

    tiv = _tiv(bundle)
    sales = _sales(bundle) or 0.0
    employees = _employees(bundle)
    vehicles = _vehicle_count(bundle)

    required_missing: list[str] = []
    if tiv <= 0:
        required_missing.append("TIV/SOV missing — cannot rate property section")
    if sales <= 0:
        required_missing.append("Gross sales missing — cannot rate GL section (will not invent sales from TIV)")
    if required_missing:
        return _ineligible(
            bundle,
            line,
            required_missing,
            meta={"rating_engine": "package_section_rating", "insurance_line": line.value, "tiv": tiv, "sales": sales},
        )

    for section_id, weight, section_line in sections_def:
        if section_line == InsuranceLine.COMMERCIAL_PROPERTY:
            section_prem = (tiv / 100.0) * 0.28 * 2.10 * weight
        elif section_line == InsuranceLine.GENERAL_LIABILITY:
            section_prem = (sales / 1000.0) * GL_RATE_PER_1K_SALES * weight
        elif section_line == InsuranceLine.CRIME:
            if not employees:
                skipped.append("crime: employee count missing")
                continue
            section_prem = employees * CRIME_PER_EMPLOYEE * weight * 2
        elif section_line == InsuranceLine.COMMERCIAL_AUTO:
            if not vehicles:
                skipped.append("commercial_auto: power units missing")
                continue
            section_prem = vehicles * (AUTO_LIABILITY_PER_UNIT * 0.5) * weight
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
            "skipped_sections": skipped,
            "tiv": tiv,
            "sales": sales,
        },
    )


def is_extended_commercial(line: InsuranceLine) -> bool:
    return line in EXTENDED_COMMERCIAL_LINES


def is_package_line(line: InsuranceLine) -> bool:
    return line in (InsuranceLine.BOP, InsuranceLine.COMMERCIAL_PACKAGE)
