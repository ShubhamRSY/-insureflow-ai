"""Commercial lines underwriting checklists and combined-risk scenario engine.

Each commercial line of business (LOB) is evaluated against a structured checklist
of discrete risk flags extracted from submission text (via ``_blob``) and structured
fields. Individual flags may trigger targeted underwriting actions — premium
debits/credits, deductible changes, documentation requests, exclusions, or referral.

*Combined-risk scenarios* fire when multiple related flags align into a known loss
pattern. For example, unsprinklered occupancy with poor protection class and flammable
storage triggers ``PROP_FIRE_SCENARIO``, bundling mitigation requirements, a higher
deductible, a rate debit, and staff referral into one coherent hit.

The public entry point ``evaluate_commercial_checklist`` runs the LOB-specific
evaluator, aggregates flags and scenario hits into actions and an overall
``UWDecision``, computes a net premium modification, materializes ``Finding``
records for agents and worksheets, and builds a human-readable *decision story*
that explains what was seen and why the underwriter should act.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from insureflow.models.agents import Finding, RiskSeverity, UWDecision
from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine
from insureflow.underwriting.personal_lines import _blob


class UWActionType(str, Enum):
    PRICE_UP = "price_up"
    PRICE_DOWN = "price_down"
    HIGHER_DEDUCTIBLE = "higher_deductible"
    REQUIRE_MITIGATION = "require_mitigation"
    ADD_EXCLUSION = "add_exclusion"
    CAP_COVERAGE = "cap_coverage"
    REQUIRE_DOC = "require_doc"
    ENHANCED_REVIEW = "enhanced_review"
    REFER = "refer"
    DECLINE = "decline"


@dataclass
class ChecklistFlag:
    code: str
    label: str
    detail: str
    severity: RiskSeverity = RiskSeverity.MODERATE
    category: str = ""


@dataclass
class UWAction:
    action_type: UWActionType
    reason: str
    premium_mod_pct: float = 0.0
    detail: str = ""


@dataclass
class ScenarioHit:
    code: str
    name: str
    description: str
    flag_codes: list[str] = field(default_factory=list)
    actions: list[UWAction] = field(default_factory=list)
    decision_hint: UWDecision | None = None


@dataclass
class CommercialUWResult:
    line: InsuranceLine
    decision: UWDecision
    flags: list[ChecklistFlag] = field(default_factory=list)
    scenarios: list[ScenarioHit] = field(default_factory=list)
    actions: list[UWAction] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    premium_mod_pct: float = 0.0
    story: str = ""

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "line": self.line.value,
            "decision": self.decision.value,
            "premium_mod_pct": round(self.premium_mod_pct, 2),
            "flag_count": len(self.flags),
            "flag_codes": [f.code for f in self.flags],
            "scenario_codes": [s.code for s in self.scenarios],
            "action_types": [a.action_type.value for a in self.actions],
            "finding_count": len(self.findings),
            "story": self.story,
        }


_DECISION_RANK: dict[UWDecision, int] = {
    UWDecision.ACCEPT: 0,
    UWDecision.CONDITIONAL_ACCEPT: 1,
    UWDecision.REFER: 2,
    UWDecision.DECLINE: 3,
}


def _num(blob: str, *labels: str) -> float | None:
    """Extract the first numeric field matching any label."""
    for label in labels:
        m = re.search(
            rf"{re.escape(label)}\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)",
            blob,
            re.I,
        )
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _pct(blob: str, *labels: str) -> float | None:
    """Extract a percentage field matching any label."""
    for label in labels:
        m = re.search(
            rf"{re.escape(label)}\s*[:=]?\s*(\d{{1,3}}(?:\.\d+)?)\s*%",
            blob,
            re.I,
        )
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def _has(blob: str, *terms: str) -> bool:
    """Substring match with common negations stripped (e.g. non-combustible ≠ combustible)."""
    import re

    cleaned = re.sub(r"\bnon[-\s]?combustible\b", " ", blob)
    cleaned = re.sub(r"\bnon[-\s]?flammable\b", " ", cleaned)
    return any(term in cleaned for term in terms)


def _neg(blob: str, *terms: str) -> bool:
    """True when a term is explicitly negated (e.g. 'no elevation certificate')."""
    for term in terms:
        if re.search(rf"(?:no |without |missing |lack of |absent |none |not ){re.escape(term)}", blob):
            return True
    return False


def _add_flag(
    flags: list[ChecklistFlag],
    code: str,
    label: str,
    detail: str,
    *,
    severity: RiskSeverity = RiskSeverity.MODERATE,
    category: str = "",
) -> None:
    flags.append(
        ChecklistFlag(
            code=code,
            label=label,
            detail=detail,
            severity=severity,
            category=category,
        )
    )


def _flag_codes(flags: list[ChecklistFlag]) -> set[str]:
    return {f.code for f in flags}


def _worst(*decisions: UWDecision) -> UWDecision:
    if not decisions:
        return UWDecision.ACCEPT
    return max(decisions, key=lambda d: _DECISION_RANK[d])


def _system_age_flags(
    blob: str,
    flags: list[ChecklistFlag],
    *,
    category: str,
) -> None:
    """Flag building systems at or beyond 20 years."""
    systems: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        ("PROP_ROOF_AGE", "Aged roof (≥20 years)", ("roof age", "roof replaced", "roof year", "year roof")),
        ("PROP_HVAC_AGE", "Aged HVAC (≥20 years)", ("hvac age", "hvac year", "heating age", "cooling age")),
        (
            "PROP_ELECTRICAL_AGE",
            "Aged electrical (≥20 years)",
            ("electrical age", "electrical updated", "wiring age", "panel age"),
        ),
        (
            "PROP_PLUMBING_AGE",
            "Aged plumbing (≥20 years)",
            ("plumbing age", "plumbing updated", "pipe age"),
        ),
    )
    for code, label, labels in systems:
        age = _num(blob, *labels)
        if age is not None and age >= 20:
            _add_flag(
                flags,
                code,
                label,
                f"System age {age:.0f} years — schedule inspection / update documentation.",
                severity=RiskSeverity.MODERATE,
                category=category,
            )
            continue
        for lbl in labels:
            m = re.search(rf"{re.escape(lbl)}[^\n]{{0,40}}?(\d{{2,3}})\s*(?:years?|yrs?)", blob, re.I)
            if m and int(m.group(1)) >= 20:
                _add_flag(
                    flags,
                    code,
                    label,
                    f"System age ~{m.group(1)} years — schedule inspection / update documentation.",
                    severity=RiskSeverity.MODERATE,
                    category=category,
                )
                break


def _eval_property(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "commercial_property"

    _system_age_flags(blob, flags, category=category)

    hydrant_ft = _num(blob, "hydrant distance", "distance to hydrant", "nearest hydrant")
    station_mi = _num(blob, "fire station distance", "distance to fire station", "nearest fire station")
    if hydrant_ft is not None and hydrant_ft > 1_000:
        _add_flag(
            flags,
            "PROP_HYDRANT_DISTANCE",
            "Hydrant distance exceeds 1,000 ft",
            f"Hydrant reported at {hydrant_ft:.0f} ft — ISO protection concern.",
            severity=RiskSeverity.HIGH,
            category=category,
        )
    elif _has(blob, "no hydrant", "no public hydrant", "hydrant: none"):
        _add_flag(
            flags,
            "PROP_HYDRANT_DISTANCE",
            "No public hydrant nearby",
            "No hydrant access disclosed — elevated fire suppression response time.",
            severity=RiskSeverity.HIGH,
            category=category,
        )
    if station_mi is not None and station_mi > 5:
        _add_flag(
            flags,
            "PROP_STATION_DISTANCE",
            "Fire station >5 miles",
            f"Nearest fire station {station_mi:.1f} mi — extended response time.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    in_flood = _has(
        blob,
        "flood zone",
        "zone ae",
        "zone ve",
        "zone a ",
        "special flood",
        "sfha",
    )
    has_elev_cert = _has(
        blob,
        "elevation certificate",
        "elevation cert",
        "fema elevation",
        "ec date",
    )
    if in_flood and not has_elev_cert:
        _add_flag(
            flags,
            "PROP_FLOOD_NO_ELEV",
            "Flood zone without elevation certificate",
            "SFHA / flood zone indicated but no elevation certificate on file.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(
        blob,
        "manufacturing",
        "warehouse",
        "flammable",
        "combustible storage",
        "paint shop",
        "woodworking",
        "restaurant",
        "cooking exposure",
    ):
        _add_flag(
            flags,
            "PROP_OCCUPANCY_HAZARD",
            "Higher-hazard occupancy",
            "Occupancy or operations suggest elevated fire or liability exposure.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    prior_claims = len(re.findall(r"prior claim|date of loss|loss history|fire loss|water damage claim", blob))
    if prior_claims >= 2:
        _add_flag(
            flags,
            "PROP_PRIOR_CLAIMS",
            "Prior property claims",
            f"{prior_claims} prior-claim signal(s) in submission — experience rate review.",
            severity=RiskSeverity.HIGH if prior_claims >= 3 else RiskSeverity.MODERATE,
            category=category,
        )

    unsprinklered = _has(
        blob,
        "no sprinkler",
        "unsprinklered",
        "without sprinkler",
        "sprinkler: no",
        "sprinklers: none",
    )
    if unsprinklered:
        _add_flag(
            flags,
            "PROP_UNSPRINKLERED",
            "No sprinkler system",
            "Premises disclosed as unsprinklered — fire protection deficiency.",
            severity=RiskSeverity.HIGH,
            category=category,
        )
    pc = _num(blob, "protection class", "iso ppc", "ppc")
    poor_pc = pc is not None and pc >= 8
    if poor_pc:
        _add_flag(
            flags,
            "PROP_POOR_PC",
            "Poor protection class (≥8)",
            f"ISO / PPC {pc:.0f} — elevated fire response risk.",
            severity=RiskSeverity.HIGH,
            category=category,
        )
    flammables = _has(
        blob,
        "flammable",
        "combustible",
        "solvent",
        "paint storage",
        "chemical storage",
        "propane",
        "lp gas",
        "stored improperly",
    )
    if flammables:
        _add_flag(
            flags,
            "PROP_FLAMMABLES",
            "Flammable / combustible storage",
            "Flammable or combustible materials disclosed on premises.",
            severity=RiskSeverity.HIGH,
            category=category,
        )
    recent_fire = _has(
        blob,
        "recent fire",
        "fire loss",
        "prior fire",
        "fire claim",
        "incendiary",
    )
    if recent_fire:
        _add_flag(
            flags,
            "PROP_RECENT_FIRE",
            "Recent fire loss / claim",
            "Fire claim or loss history disclosed.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    # Combined fire pattern: (unsprinklered OR poor PC OR flammables) with fire history,
    # or unsprinklered/poor PC with flammables — matches UW fire accumulation review.
    fire_combo = ((unsprinklered or poor_pc) and (flammables or recent_fire)) or (flammables and recent_fire)
    if fire_combo:
        hit_flags = _flag_codes(flags)
        scenario_flags = sorted(
            c
            for c in hit_flags
            if c
            in {
                "PROP_UNSPRINKLERED",
                "PROP_POOR_PC",
                "PROP_FLAMMABLES",
                "PROP_RECENT_FIRE",
                "PROP_OCCUPANCY_HAZARD",
                "PROP_PRIOR_CLAIMS",
                "PROP_HYDRANT_DISTANCE",
                "PROP_STATION_DISTANCE",
            }
        )

        scenarios.append(
            ScenarioHit(
                code="PROP_FIRE_SCENARIO",
                name="Combined fire accumulation",
                description=("Unsprinklered or poorly protected occupancy with flammable materials and/or recent fire history — bundled fire scenario."),
                flag_codes=scenario_flags,
                decision_hint=UWDecision.REFER,
                actions=[
                    UWAction(
                        UWActionType.REQUIRE_MITIGATION,
                        "PROP_FIRE_SCENARIO",
                        detail="Require sprinkler retrofit plan or combustible storage controls.",
                    ),
                    UWAction(
                        UWActionType.HIGHER_DEDUCTIBLE,
                        "PROP_FIRE_SCENARIO",
                        detail="Apply minimum $25K property deductible or AOP increase.",
                    ),
                    UWAction(
                        UWActionType.PRICE_UP,
                        "PROP_FIRE_SCENARIO",
                        premium_mod_pct=18.0,
                        detail="Fire accumulation debit.",
                    ),
                    UWAction(
                        UWActionType.REFER,
                        "PROP_FIRE_SCENARIO",
                        detail="Refer to property CUO for occupancy + protection review.",
                    ),
                ],
            )
        )

    return flags, scenarios


def _eval_do(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "directors_and_officers"

    runway = _num(blob, "runway", "cash runway", "months runway")
    burn = _num(blob, "burn rate", "monthly burn", "cash burn")
    if runway is not None and runway < 12:
        _add_flag(
            flags,
            "DO_SHORT_RUNWAY",
            "Short cash runway (<12 months)",
            f"Runway {runway:.0f} months — insolvency / securities exposure.",
            severity=RiskSeverity.HIGH,
            category=category,
        )
    if burn is not None and burn > 0 and (runway is None or runway < 18):
        _add_flag(
            flags,
            "DO_BURN_RATE",
            "Elevated burn rate",
            f"Burn rate ${burn:,.0f}/mo with limited runway cushion.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "board turnover", "director turnover", "board change", "new directors"):
        _add_flag(
            flags,
            "DO_BOARD_TURNOVER",
            "Board turnover",
            "Recent board turnover — governance and D&O continuity review.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(blob, "vacant board seat", "vacant director", "open board seat", "unfilled seat"):
        _add_flag(
            flags,
            "DO_VACANT_SEATS",
            "Vacant board seats",
            "Vacant director seats weaken governance controls.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(blob, "related party", "related-party", "insider transaction", "self-dealing"):
        _add_flag(
            flags,
            "DO_RELATED_PARTY",
            "Related-party transactions",
            "Related-party dealings increase fiduciary litigation exposure.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    down_round = _has(
        blob,
        "down round",
        "down-round",
        "valuation decrease",
        "409a down",
        "flat round",
        "cram down",
    )
    if down_round:
        _add_flag(
            flags,
            "DO_DOWN_ROUND",
            "Down round / valuation reset",
            "Recent down round signals investor / shareholder friction.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    layoffs = _has(blob, "layoff", "layoffs", "reduction in force", "rif ", "workforce reduction")
    if layoffs:
        _add_flag(
            flags,
            "DO_LAYOFFS",
            "Recent layoffs",
            "Workforce reductions elevate wrongful termination / securities claims.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(
        blob,
        "industry litigation",
        "sector litigation",
        "peer litigation",
        "industry-wide investigation",
        "sector investigation",
    ):
        _add_flag(
            flags,
            "DO_INDUSTRY_LITIGATION",
            "Industry litigation trend",
            "Sector-wide litigation or investigation activity disclosed.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(
        blob,
        "pending litigation",
        "securities class action",
        "shareholder lawsuit",
        "sec investigation",
        "doj investigation",
        "material litigation",
    ):
        _add_flag(
            flags,
            "DO_PENDING_LITIGATION",
            "Pending litigation / investigation",
            "Material litigation or regulatory investigation on file.",
            severity=RiskSeverity.CRITICAL,
            category=category,
        )

    codes = _flag_codes(flags)
    governance_signals = {"DO_VACANT_SEATS", "DO_BOARD_TURNOVER", "DO_SHORT_RUNWAY", "DO_BURN_RATE"}
    if down_round and layoffs and bool(governance_signals & codes):
        scenarios.append(
            ScenarioHit(
                code="DO_DISTRESS_SCENARIO",
                name="Financial distress + governance stress",
                description=("Down round and layoffs combined with runway, burn, or board instability — classic insolvency / securities scenario."),
                flag_codes=sorted({"DO_DOWN_ROUND", "DO_LAYOFFS"} | (governance_signals & codes)),
                decision_hint=UWDecision.REFER,
                actions=[
                    UWAction(
                        UWActionType.PRICE_UP,
                        "DO_DISTRESS_SCENARIO",
                        premium_mod_pct=25.0,
                        detail="Distress loading for D&O.",
                    ),
                    UWAction(
                        UWActionType.ADD_EXCLUSION,
                        "DO_DISTRESS_SCENARIO",
                        detail="Add insolvency / bankruptcy exclusion endorsement.",
                    ),
                    UWAction(
                        UWActionType.REFER,
                        "DO_DISTRESS_SCENARIO",
                        detail="Refer to management liability senior underwriter.",
                    ),
                ],
            )
        )

    return flags, scenarios


def _eval_wc(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "workers_comp"

    emod = _num(blob, "e-mod", "emod", "experience mod", "experience modification", "x-mod")
    if emod is None:
        m = re.search(r"experience\s+mod(?:ification)?\s*[:=]?\s*(\d\.\d{2,3})", blob, re.I)
        if m:
            emod = float(m.group(1))
    high_emod = emod is not None and emod > 1.0
    if high_emod:
        _add_flag(
            flags,
            "WC_HIGH_EMOD",
            "Experience mod > 1.0",
            f"E-mod {emod:.2f} — adverse experience rating.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "injury trend", "injury frequency", "lost time trend", "increasing claims", "rising claims"):
        _add_flag(
            flags,
            "WC_INJURY_TREND",
            "Adverse injury trend",
            "Injury frequency or severity trend is deteriorating.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    open_claims = _num(blob, "open claims", "open wc claims", "open workers comp claims")
    has_open = open_claims is not None and open_claims > 0
    if has_open:
        _add_flag(
            flags,
            "WC_OPEN_CLAIMS",
            "Open workers comp claims",
            f"{open_claims:.0f} open claim(s) — reserve / RTW review.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )
    elif _has(blob, "open claim", "open wc", "unresolved claim"):
        has_open = True
        _add_flag(
            flags,
            "WC_OPEN_CLAIMS",
            "Open workers comp claims",
            "Open claim activity disclosed — reserve / RTW review.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    rtw_missing = not _has(
        blob,
        "return to work",
        "rtw program",
        "return-to-work",
        "modified duty",
        "transitional duty",
    )
    if rtw_missing:
        _add_flag(
            flags,
            "WC_RTW_MISSING",
            "Return-to-work program missing",
            "No RTW / modified duty program documented.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    turnover = _pct(blob, "employee turnover", "turnover rate", "staff turnover", "annual turnover")
    if turnover is not None and turnover >= 30:
        _add_flag(
            flags,
            "WC_HIGH_TURNOVER",
            "Employee turnover ≥30%",
            f"Turnover {turnover:.0f}% — training and injury frequency concern.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )
    elif _has(blob, "turnover 30", "turnover: 3", "high turnover"):
        _add_flag(
            flags,
            "WC_HIGH_TURNOVER",
            "Employee turnover ≥30%",
            "High turnover disclosed — training and injury frequency concern.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    safety_missing = not _has(
        blob,
        "safety program",
        "safety manual",
        "osha compliance",
        "safety committee",
        "loss control",
        "safety plan",
    )
    if safety_missing:
        _add_flag(
            flags,
            "WC_SAFETY_MISSING",
            "Safety program not documented",
            "No formal safety / loss control program referenced.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    codes = _flag_codes(flags)
    if high_emod and has_open and (safety_missing or rtw_missing):
        scenario_flags = sorted(c for c in codes if c in {"WC_HIGH_EMOD", "WC_OPEN_CLAIMS", "WC_SAFETY_MISSING", "WC_RTW_MISSING"})
        scenarios.append(
            ScenarioHit(
                code="WC_SAFETY_SCENARIO",
                name="Experience mod + open claims + weak safety",
                description=("High experience modification with open claims and no documented safety or return-to-work program."),
                flag_codes=scenario_flags,
                decision_hint=UWDecision.REFER,
                actions=[
                    UWAction(
                        UWActionType.PRICE_UP,
                        "WC_SAFETY_SCENARIO",
                        premium_mod_pct=20.0,
                        detail="Experience and safety debit.",
                    ),
                    UWAction(
                        UWActionType.REQUIRE_MITIGATION,
                        "WC_SAFETY_SCENARIO",
                        detail="Require written safety plan and RTW program within 30 days.",
                    ),
                    UWAction(
                        UWActionType.REFER,
                        "WC_SAFETY_SCENARIO",
                        detail="Refer to WC line underwriter for loss control follow-up.",
                    ),
                ],
            )
        )

    return flags, scenarios


def _eval_trade_credit(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "trade_credit"

    concentration = _pct(
        blob,
        "top buyer concentration",
        "top customer concentration",
        "buyer concentration",
        "customer concentration",
        "concentration",
    )
    if concentration is None:
        m = re.search(r"top\s*(?:buyer|customer)\s*(?:concentration|share)?\s*[:=]?\s*(\d{1,3})\s*%", blob)
        if m:
            concentration = float(m.group(1))
    high_conc = concentration is not None and concentration >= 40
    if high_conc:
        _add_flag(
            flags,
            "TC_HIGH_CONCENTRATION",
            "Buyer concentration ≥40%",
            f"Top buyer/customer concentration {concentration:.0f}%.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "buyer rating downgrade", "credit rating downgrade", "deteriorating buyer", "weak buyer rating"):
        _add_flag(
            flags,
            "TC_BUYER_RATING",
            "Buyer credit deterioration",
            "Buyer ratings or credit quality appear weakened.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    dso = _num(blob, "dso", "days sales outstanding", "average collection period")
    if dso is not None and dso >= 60:
        _add_flag(
            flags,
            "TC_HIGH_DSO",
            "DSO ≥60 days",
            f"Days sales outstanding {dso:.0f} — collection / credit stress.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    geo_risk = _has(
        blob,
        "political risk",
        "country risk",
        "sanctions",
        "emerging market",
        "export credit risk",
        "geopolitical",
        "trade embargo",
        "high-risk country",
    )
    if geo_risk:
        _add_flag(
            flags,
            "TC_GEO_RISK",
            "Geographic / political risk",
            "Cross-border or political risk factors disclosed.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    ar_missing = not _has(blob, "accounts receivable", "a/r aging", "ar aging", "receivables aging", "aging report")
    if ar_missing:
        _add_flag(
            flags,
            "TC_AR_MISSING",
            "AR aging missing",
            "No current accounts receivable aging on file.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    codes = _flag_codes(flags)
    if high_conc:
        scenarios.append(
            ScenarioHit(
                code="TC_CONCENTRATION_SCENARIO",
                name="Buyer concentration",
                description=f"Single-buyer concentration at {concentration:.0f}% exceeds guideline.",
                flag_codes=["TC_HIGH_CONCENTRATION"],
                decision_hint=UWDecision.REFER,
                actions=[
                    UWAction(
                        UWActionType.ENHANCED_REVIEW,
                        "TC_CONCENTRATION_SCENARIO",
                        detail="Credit committee review of top buyer exposure.",
                    ),
                    UWAction(
                        UWActionType.REFER,
                        "TC_CONCENTRATION_SCENARIO",
                        detail="Refer to trade credit underwriter.",
                    ),
                ],
            )
        )

    if high_conc and geo_risk:
        scenarios.append(
            ScenarioHit(
                code="TC_CONCENTRATION_GEO_SCENARIO",
                name="Concentration + geographic risk",
                description="High buyer concentration combined with geographic or political risk.",
                flag_codes=sorted({"TC_HIGH_CONCENTRATION", "TC_GEO_RISK"} & codes),
                decision_hint=UWDecision.CONDITIONAL_ACCEPT,
                actions=[
                    UWAction(
                        UWActionType.CAP_COVERAGE,
                        "TC_CONCENTRATION_GEO_SCENARIO",
                        detail="Cap per-buyer limit and aggregate to reflect concentration.",
                    ),
                    UWAction(
                        UWActionType.REQUIRE_DOC,
                        "TC_CONCENTRATION_GEO_SCENARIO",
                        detail="Require quarterly buyer exposure updates and aging reports.",
                    ),
                    UWAction(
                        UWActionType.PRICE_UP,
                        "TC_CONCENTRATION_GEO_SCENARIO",
                        premium_mod_pct=12.0,
                        detail="Concentration + geo risk debit.",
                    ),
                ],
            )
        )

    return flags, scenarios


def _eval_eo(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "errors_and_omissions"

    weak_contracts = _has(
        blob,
        "guarantee of results",
        "guaranteed outcome",
        "unlimited liability",
        "consequential damages",
        "hold harmless",
        "broad indemnity",
        "weak contract",
        "one-sided contract",
    )
    if weak_contracts:
        _add_flag(
            flags,
            "EO_WEAK_CONTRACTS",
            "Weak / aggressive contract terms",
            "Client contracts may expand professional liability beyond standard scope.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "scope creep", "scope expansion", "outside scope", "unapproved work", "change order"):
        _add_flag(
            flags,
            "EO_SCOPE_CREEP",
            "Scope creep",
            "Work performed outside original engagement scope.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    high_risk_industry = _has(
        blob,
        "cryptocurrency",
        "crypto",
        "fintech",
        "medical device",
        "healthcare it",
        "aerospace",
        "new industry",
        "emerging technology",
        "ai consulting",
        "blockchain",
    )
    if high_risk_industry:
        _add_flag(
            flags,
            "EO_HIGH_RISK_INDUSTRY",
            "High-risk / emerging industry",
            "Services target high-severity or rapidly evolving industry segment.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "subcontractor", "sub-contractor", "1099", "outsourced delivery", "third-party delivery"):
        _add_flag(
            flags,
            "EO_SUBCONTRACTOR",
            "Subcontractor reliance",
            "Material reliance on subcontractors for client deliverables.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    prior_claims = _has(
        blob,
        "prior claim",
        "e&o claim",
        "professional liability claim",
        "malpractice claim",
        "prior acts claim",
    )
    if prior_claims:
        _add_flag(
            flags,
            "EO_PRIOR_CLAIMS",
            "Prior E&O claims",
            "Prior professional liability claims disclosed.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    codes = _flag_codes(flags)
    trigger_flags = {"EO_WEAK_CONTRACTS", "EO_PRIOR_CLAIMS", "EO_HIGH_RISK_INDUSTRY"}
    if len(trigger_flags & codes) >= 2 or (weak_contracts and (high_risk_industry or prior_claims)):
        scenarios.append(
            ScenarioHit(
                code="EO_CONTRACT_INDUSTRY_CLAIMS_SCENARIO",
                name="Contract weakness + industry / claims",
                description=("Aggressive contract terms combined with high-risk industry exposure and/or prior claims — professional liability accumulation."),
                flag_codes=sorted(trigger_flags & codes),
                decision_hint=UWDecision.REFER,
                actions=[
                    UWAction(
                        UWActionType.REQUIRE_DOC,
                        "EO_CONTRACT_INDUSTRY_CLAIMS_SCENARIO",
                        detail="Require sample client contracts and claims-made warranty; standardize liability caps.",
                    ),
                    UWAction(
                        UWActionType.ADD_EXCLUSION,
                        "EO_CONTRACT_INDUSTRY_CLAIMS_SCENARIO",
                        detail="Exclude non-standard indemnity / consequential damages exposures pending contract review.",
                    ),
                    UWAction(
                        UWActionType.PRICE_UP,
                        "EO_CONTRACT_INDUSTRY_CLAIMS_SCENARIO",
                        premium_mod_pct=15.0,
                        detail="Contract / industry debit.",
                    ),
                    UWAction(
                        UWActionType.REFER,
                        "EO_CONTRACT_INDUSTRY_CLAIMS_SCENARIO",
                        detail="Refer to professional liability underwriter.",
                    ),
                ],
            )
        )

    return flags, scenarios


def _eval_key_person(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "key_person"

    age = _num(blob, "insured age", "key person age", "applicant age", "age")
    age_high = age is not None and age >= 60
    if age_high:
        _add_flag(
            flags,
            "KP_AGE_60",
            "Key person age ≥60",
            f"Insured age {age:.0f} — mortality and succession concern.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    medical_risk = _has(
        blob,
        "cancer",
        "heart attack",
        "stroke",
        "diabetes",
        "coronary",
        "hypertension",
        "medical history",
        "cardiac",
        "tobacco",
        "smoker",
    )
    if medical_risk:
        _add_flag(
            flags,
            "KP_MEDICAL_RISK",
            "Material medical history",
            "Disclosed medical conditions affect mortality assessment.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    rev_dep = _pct(blob, "revenue dependency", "revenue attributable", "dependency on key person")
    if rev_dep is None:
        m = re.search(r"(\d{1,3})\s*%\s*(?:of\s*)?(?:revenue|sales)\s*(?:depends|dependent|attributable)", blob)
        if m:
            rev_dep = float(m.group(1))
    high_dep = rev_dep is not None and rev_dep >= 40
    if high_dep:
        _add_flag(
            flags,
            "KP_REVENUE_DEPENDENCY",
            "Revenue dependency ≥40%",
            f"Key person drives {rev_dep:.0f}% of revenue.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    no_succession = _has(
        blob,
        "no succession",
        "without succession",
        "succession: none",
        "succession plan: no",
        "lacks succession",
        "missing succession",
    ) or (
        not _has(
            blob,
            "succession plan",
            "backup leadership",
            "key person replacement",
            "buy-sell",
            "continuity plan",
        )
    )
    if no_succession:
        _add_flag(
            flags,
            "KP_NO_SUCCESSION",
            "No succession plan",
            "No documented succession or continuity plan for the key person.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    codes = _flag_codes(flags)
    if no_succession and (age_high or medical_risk) and (high_dep or medical_risk):
        scenario_flags = sorted(c for c in codes if c in {"KP_AGE_60", "KP_MEDICAL_RISK", "KP_REVENUE_DEPENDENCY", "KP_NO_SUCCESSION"})
        scenarios.append(
            ScenarioHit(
                code="KP_SUCCESSION_MEDICAL_SCENARIO",
                name="Succession gap + medical / age stress",
                description=("No succession plan while key person is older or has medical history and business dependency is elevated."),
                flag_codes=scenario_flags,
                decision_hint=UWDecision.REFER,
                actions=[
                    UWAction(
                        UWActionType.REQUIRE_DOC,
                        "KP_SUCCESSION_MEDICAL_SCENARIO",
                        detail="Require succession plan and updated medical / financial justification.",
                    ),
                    UWAction(
                        UWActionType.ENHANCED_REVIEW,
                        "KP_SUCCESSION_MEDICAL_SCENARIO",
                        detail="Enhanced medical underwriting and business continuity review.",
                    ),
                    UWAction(
                        UWActionType.PRICE_UP,
                        "KP_SUCCESSION_MEDICAL_SCENARIO",
                        premium_mod_pct=20.0,
                        detail="Age / medical / dependency debit pending succession plan.",
                    ),
                    UWAction(
                        UWActionType.REFER,
                        "KP_SUCCESSION_MEDICAL_SCENARIO",
                        detail="Refer to life / key-person underwriter.",
                    ),
                ],
            )
        )

    return flags, scenarios


def _eval_aviation(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "aviation"

    hull = _num(blob, "hull value", "aircraft value", "insurable value", "insured value")
    if hull is not None and hull > 5_000_000:
        _add_flag(
            flags,
            "AV_HIGH_HULL",
            "High hull value",
            f"Hull valued at ${hull:,.0f} — concentration / reinsurance review.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(blob, "aging fleet", "old fleet", "high cycle", "airframe age", "vintage aircraft"):
        _add_flag(
            flags,
            "AV_AGING_FLEET",
            "Aging / high-cycle fleet",
            "Older airframes or high cycle counts — maintenance record review required.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "single engine", "single-engine", "piston engine", "experimental", "homebuilt"):
        _add_flag(
            flags,
            "AV_SINGLE_ENGINE",
            "Single-engine / experimental airframes",
            "Single-engine or experimental aircraft — elevated hull + liability frequency.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(blob, "no pilots", "pilot shortage", "fatigue", "undocumented crew") or _has(blob, "pilot", "crew") and _has(blob, "undocumented", "unlicensed", "expired medical"):
        _add_flag(
            flags,
            "AV_CREW_DOCS",
            "Crew qualification gap",
            "Pilot / crew qualification or medical currency not documented.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "territory", "war risk", "conflict zone", "hostile", "sanctioned airspace"):
        _add_flag(
            flags,
            "AV_TERRITORY_RISK",
            "Hostile / special territory exposure",
            "Operations into conflict or special-risk territories — war-risk and political risk review.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "no maintenance", "lack of maintenance", "deferred maintenance", "maintenance deferred", "airworthy"):
        _add_flag(
            flags,
            "AV_MAINTENANCE",
            "Maintenance / airworthiness concern",
            "Deferred maintenance or airworthiness questions — require maintenance log review.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    codes = _flag_codes(flags)
    if {"AV_AGING_FLEET", "AV_MAINTENANCE"} <= codes and "AV_TERRITORY_RISK" in codes:
        scenarios.append(
            ScenarioHit(
                code="AV_FLEET_TERRITORY_SCENARIO",
                name="Aged fleet into special territory",
                description=("Aging airframes with maintenance concerns operating into special-risk territory."),
                flag_codes=sorted(codes),
                decision_hint=UWDecision.REFER,
                actions=[
                    UWAction(UWActionType.REQUIRE_DOC, "AV_FLEET_TERRITORY_SCENARIO", detail="Require full maintenance log and crew currency documentation."),
                    UWAction(UWActionType.PRICE_UP, "AV_FLEET_TERRITORY_SCENARIO", premium_mod_pct=25.0, detail="Aviation exposure debit."),
                    UWAction(UWActionType.REFER, "AV_FLEET_TERRITORY_SCENARIO", detail="Refer to aviation underwriter / reinsurer."),
                ],
            )
        )

    return flags, scenarios


def _eval_cat_property(blob: str, *, peril: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = f"catastrophe_{peril}"

    in_zone = _has(blob, "flood zone", "sfha", "zone ae", "zone ve", "zone a ", "seismic zone", "quake zone", "fault line", "special flood")
    if in_zone:
        _add_flag(
            flags,
            f"CAT_{peril.upper()}_ZONE",
            f"{peril.title()} zone exposure",
            f"Subject located in a designated {peril} zone.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    has_mit = _has(blob, "elevation certificate", "raised foundation", "dry floodproof", "seismic retrofit", "base isolation", "shear wall")
    if in_zone and (not has_mit or _neg(blob, "elevation certificate", "raised foundation", "dry floodproof", "seismic retrofit", "base isolation", "shear wall")):
        _add_flag(
            flags,
            f"CAT_{peril.upper()}_NO_MITIGATION",
            f"No {peril} mitigation documented",
            f"{peril.title()} zone without elevation / retrofit documentation — likely deductible or attachment adjustment.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "prior loss", "prior flood", "prior earthquake", "past claims", "flood loss", "quake loss"):
        _add_flag(
            flags,
            f"CAT_{peril.upper()}_PRIOR_LOSS",
            f"Prior {peril} losses",
            "Claim history for the same peril — frequency accumulation.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    return flags, scenarios


def _eval_flood(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags, scenarios = _eval_cat_property(blob, peril="flood")
    return flags, scenarios


def _eval_earthquake(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags, scenarios = _eval_cat_property(blob, peril="earthquake")
    return flags, scenarios


def _eval_pollution(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "pollution_liability"

    if _has(blob, "no esa", "no phase i", "no phase ii", "missing assessment"):
        _add_flag(
            flags,
            "POL_NO_ESA",
            "No environmental site assessment",
            "Phase I / II ESA missing — site condition unknown.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "underground storage", "ust", "storage tank"):
        _add_flag(
            flags,
            "POL_UST",
            "Underground storage tanks",
            "UST exposure — leak detection and tank registration review.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "chemical", "hazardous", "solvent", "waste", "flammable storage", "chlorine", "asbestos"):
        _add_flag(
            flags,
            "POL_HAZMAT",
            "Hazardous material handling",
            "Chemical / hazardous materials on site — spill and cleanup exposure.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(blob, "remediation", "contaminated", "cleanup", "spill", "violation", "cease and desist"):
        _add_flag(
            flags,
            "POL_CONTAMINATION",
            "Prior contamination / violations",
            "Remediation or regulatory action history — claims exposure.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    return flags, scenarios


def _eval_kr(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "kidnap_ransom"

    if _has(blob, "high profile", "celebrity", "public figure", "prominent", "executive", "high net worth"):
        _add_flag(
            flags,
            "KR_HIGH_PROFILE",
            "High-profile insured",
            "Celebrity / executive / high-net-worth profile elevates kidnapping and extortion exposure.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(blob, "high risk country", "high risk jurisdiction", "elevated threat", "threat level", "conflict", "kidnap hotspot"):
        _add_flag(
            flags,
            "KR_GEO_RISK",
            "High-risk geography",
            "Operations in high-risk / elevated-threat jurisdictions.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    missing_crisis = _neg(blob, "crisis protocol", "crisis response plan", "response plan", "travel security")
    denied_crisis = _has(
        blob,
        "no crisis protocol",
        "no crisis response plan",
        "no response plan",
        "no travel security",
        "lack of training",
    )
    if missing_crisis or denied_crisis:
        _add_flag(
            flags,
            "KR_NO_CRISIS_PLAN",
            "No crisis / response plan",
            "Absence of crisis management and travel security procedures.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    return flags, scenarios


def _eval_political_risk(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "political_risk"

    if _has(blob, "expropriation", "nationalization", "confiscation", "creeping expropriation"):
        _add_flag(
            flags,
            "PR_EXPROPRIATION",
            "Expropriation exposure",
            "Host-country expropriation / nationalization risk disclosed.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "currency", "transfer risk", "inconvertibility", "remittance", "blocked funds"):
        _add_flag(
            flags,
            "PR_TRANSFER_RISK",
            "Currency transfer risk",
            "Currency inconvertibility / transfer restrictions exposure.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "political violence", "civil unrest", "insurrection", "war", "sanctions"):
        _add_flag(
            flags,
            "PR_VIOLENCE",
            "Political violence / sanctions",
            "Political violence or sanctions-related exposure in covered territories.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "single country", "single contract", "concentration"):
        _add_flag(
            flags,
            "PR_CONCENTRATION",
            "Country / contract concentration",
            "Concentrated exposure in one country or contract — portfolio spread concern.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    return flags, scenarios


def _eval_terrorism(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "terrorism"

    if _has(blob, "certified act", "certified event", "treasury certification", "tripwire"):
        _add_flag(
            flags,
            "TERR_CERTIFIED",
            "Certified-acts coverage structure",
            "Coverage triggers on certified acts — confirm TRIA-style certification terms.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(blob, "iconic", "landmark", "high profile", "government", "stadium", "crowd concentration", "mass gathering"):
        _add_flag(
            flags,
            "TERR_TARGET",
            "High-profile / high-crowd target",
            "Iconic or crowd-concentrating location elevates terrorist attack exposure.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "no counterterror", "no security plan", "no access control"):
        _add_flag(
            flags,
            "TERR_NO_SECURITY",
            "Security plan gap",
            "No counterterror / physical security plan documented.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    return flags, scenarios


def _eval_legal_expense(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "legal_expense"

    if _has(blob, "litigation", "lawsuit", "pending claim", "dispute", "claim pending"):
        _add_flag(
            flags,
            "LEG_PENDING_LITIGATION",
            "Pending litigation / dispute",
            "Active or anticipated litigation drives defence-cost exposure.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    if _has(blob, "employment", "discrimination", "wrongful termination", "harassment"):
        _add_flag(
            flags,
            "LEG_EMPLOYMENT",
            "Employment-related exposure",
            "Employment disputes — frequency-prone defence costs.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    if _has(blob, "no panel", "no counsel", "no legal team", "no firm"):
        _add_flag(
            flags,
            "LEG_NO_PANEL",
            "No panel counsel arrangements",
            "No established panel counsel — defence cost control unclear.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    return flags, scenarios


_EVALUATORS: dict[InsuranceLine, Callable[[str], tuple[list[ChecklistFlag], list[ScenarioHit]]]] = {
    InsuranceLine.COMMERCIAL_PROPERTY: _eval_property,
    InsuranceLine.BOP: _eval_property,
    InsuranceLine.DIRECTORS_AND_OFFICERS: _eval_do,
    InsuranceLine.WORKERS_COMP: _eval_wc,
    InsuranceLine.TRADE_CREDIT: _eval_trade_credit,
    InsuranceLine.ERRORS_AND_OMISSIONS: _eval_eo,
    InsuranceLine.KEY_PERSON: _eval_key_person,
    InsuranceLine.AVIATION: _eval_aviation,
    InsuranceLine.FLOOD: _eval_flood,
    InsuranceLine.EARTHQUAKE: _eval_earthquake,
    InsuranceLine.POLLUTION: _eval_pollution,
    InsuranceLine.KIDNAP_RANSOM: _eval_kr,
    InsuranceLine.POLITICAL_RISK: _eval_political_risk,
    InsuranceLine.TERRORISM: _eval_terrorism,
    InsuranceLine.LEGAL_EXPENSE: _eval_legal_expense,
}


# Business-interruption triggers — BI runs as an additive pass whenever the
# submission carries BI / extra-expense coverages.
_BI_TRIGGERS = (
    "business interruption",
    "extra expense",
    "extra_extra_expense",
    "contingent business interruption",
    "civil authority",
    "gross earnings",
    "gross profit",
    "business income",
    "b.i.",
)


def _eval_bi(blob: str) -> tuple[list[ChecklistFlag], list[ScenarioHit]]:
    """Business interruption / extra-expense worksheet review.

    BI protects the lost net income + continuing expenses during a covered
    shutdown — so an inadequate BI limit, missing 80% coinsurance, or reliance
    on a single supplier/location all undermine the protection.
    """
    flags: list[ChecklistFlag] = []
    scenarios: list[ScenarioHit] = []
    category = "business_interruption"

    bi_limit = _num(blob, "bi limit", "business interruption limit", "bi amount", "gross earnings limit", "gross profit limit")
    gross = _num(blob, "gross earnings", "gross profit", "annual gross earnings", "annual gross profit")
    if gross is not None and bi_limit is not None and bi_limit < gross * 0.80:
        _add_flag(
            flags,
            "BI_LIMIT_BELOW_80PCT",
            "BI limit below 80% of gross earnings",
            f"BI limit {bi_limit:,.0f} covers only {bi_limit / gross:.1%} of gross earnings {gross:,.0f} — under-reporting risk at loss time.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    coinsurance = _pct(blob, "bi coinsurance", "coinsurance")
    if coinsurance is not None and coinsurance < 80:
        _add_flag(
            flags,
            "BI_COINSURANCE_LOW",
            "BI coinsurance below 80%",
            f"BI coinsurance clause at {coinsurance:.0f}% — claims subject to the coinsurance penalty if under-reported.",
            severity=RiskSeverity.HIGH,
            category=category,
        )

    elimination = _num(blob, "elimination period", "waiting period", "bi elimination")
    if elimination is not None and elimination > 72:
        _add_flag(
            flags,
            "BI_ELIMINATION_LONG",
            "Long BI elimination period",
            f"Elimination period of {elimination:.0f} hours means coverage does not respond until that point — confirm the insured can absorb the gap.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )

    single_supplier = _has(blob, "single supplier", "sole supplier", "single source", "single location dependency")
    if single_supplier:
        _add_flag(
            flags,
            "BI_SINGLE_SUPPLIER",
            "Single supplier / location dependency",
            "Revenue depends on a single supplier or location — contingent BI exposure is concentrated.",
            severity=RiskSeverity.MODERATE,
            category=category,
        )
        scenarios.append(
            ScenarioHit(
                code="BI_SINGLE_SOURCE_SCENARIO",
                name="Single-source dependency",
                description="Concentration of supply or production in one node amplifies any interruption.",
                flag_codes=["BI_SINGLE_SUPPLIER"],
                actions=[
                    UWAction(
                        action_type=UWActionType.HIGHER_DEDUCTIBLE,
                        reason="Reduce BI loss potential via a longer elimination period",
                    )
                ],
                decision_hint=UWDecision.CONDITIONAL_ACCEPT,
            )
        )

    has_extra = _has(blob, "extra expense", "extra_extra_expense", "extra expense coverage")
    has_contingent = _has(blob, "contingent business interruption", "contingent bi")
    has_civil = _has(blob, "civil authority")
    if has_extra:
        _add_flag(
            flags,
            "BI_EXTRA_EXPENSE_PRESENT",
            "Extra expense coverage present",
            "Extra expense coverage found — verify the limit is sufficient to keep the operation running during restoration.",
            severity=RiskSeverity.LOW,
            category=category,
        )
    if has_contingent:
        _add_flag(
            flags,
            "BI_CONTINGENT_PRESENT",
            "Contingent BI coverage present",
            "Contingent business interruption found — confirm key suppliers / customers are scheduled.",
            severity=RiskSeverity.LOW,
            category=category,
        )
    if has_civil:
        _add_flag(
            flags,
            "BI_CIVIL_AUTHORITY_PRESENT",
            "Civil-authority coverage present",
            "Civil-authority ingress/egress coverage found — verify the time-and-distance limit.",
            severity=RiskSeverity.LOW,
            category=category,
        )

    return flags, scenarios


def evaluate_bi_checklist(bundle: SubmissionBundle) -> CommercialUWResult:
    """Run the business-interruption evaluator standalone and return a result."""
    blob = _blob(bundle).lower()
    flags, scenarios = _eval_bi(blob)
    actions: list[UWAction] = []
    for scenario in scenarios:
        actions.extend(scenario.actions)
    decision = _decision_from_flags_and_actions(flags, actions, scenarios)
    findings = _flags_to_findings(flags, InsuranceLine.COMMERCIAL_PROPERTY)
    story = _build_story(InsuranceLine.COMMERCIAL_PROPERTY, flags, scenarios, decision, actions, 0.0)
    return CommercialUWResult(
        line=InsuranceLine.COMMERCIAL_PROPERTY,
        decision=decision,
        flags=flags,
        scenarios=scenarios,
        actions=actions,
        findings=findings,
        premium_mod_pct=0.0,
        story=story,
    )


def _build_story(
    line: InsuranceLine,
    flags: list[ChecklistFlag],
    scenarios: list[ScenarioHit],
    decision: UWDecision,
    actions: list[UWAction],
    premium_mod_pct: float,
) -> str:
    parts: list[str] = [
        f"Commercial {line.value.replace('_', ' ')} checklist: {len(flags)} flag(s)",
    ]
    if flags:
        top = ", ".join(f.label for f in flags[:4])
        if len(flags) > 4:
            top += f", +{len(flags) - 4} more"
        parts.append(f"Key flags: {top}.")
    if scenarios:
        parts.append("Combined scenarios: " + "; ".join(f"{s.code} ({s.name})" for s in scenarios) + ".")
    action_bits = [a.action_type.value.replace("_", " ") for a in actions[:6]]
    if action_bits:
        parts.append("Recommended actions: " + ", ".join(action_bits) + ".")
    if premium_mod_pct:
        direction = "debit" if premium_mod_pct > 0 else "credit"
        parts.append(f"Net premium {direction} {abs(premium_mod_pct):.1f}%.")
    parts.append(f"Overall decision: {decision.value.replace('_', ' ')}.")
    return " ".join(parts)


def _decision_from_flags_and_actions(
    flags: list[ChecklistFlag],
    actions: list[UWAction],
    scenarios: list[ScenarioHit],
) -> UWDecision:
    decisions: list[UWDecision] = [UWDecision.ACCEPT]

    # Critical flags escalate to staff referral; only explicit DECLINE actions decline.
    if any(f.severity == RiskSeverity.CRITICAL for f in flags):
        decisions.append(UWDecision.REFER)

    for action in actions:
        if action.action_type == UWActionType.DECLINE:
            decisions.append(UWDecision.DECLINE)
        elif action.action_type == UWActionType.REFER:
            decisions.append(UWDecision.REFER)

    for scenario in scenarios:
        if scenario.decision_hint:
            decisions.append(scenario.decision_hint)

    conditional_types = {
        UWActionType.REQUIRE_DOC,
        UWActionType.REQUIRE_MITIGATION,
        UWActionType.HIGHER_DEDUCTIBLE,
        UWActionType.ADD_EXCLUSION,
        UWActionType.CAP_COVERAGE,
        UWActionType.ENHANCED_REVIEW,
    }
    if any(a.action_type in conditional_types for a in actions):
        decisions.append(UWDecision.CONDITIONAL_ACCEPT)

    if any(f.severity == RiskSeverity.HIGH for f in flags) and _worst(*decisions) == UWDecision.ACCEPT:
        decisions.append(UWDecision.CONDITIONAL_ACCEPT)

    return _worst(*decisions)


def _flags_to_findings(flags: list[ChecklistFlag], line: InsuranceLine) -> list[Finding]:
    findings: list[Finding] = []
    for flag in flags:
        findings.append(
            Finding(
                title=flag.label,
                description=flag.detail,
                severity=flag.severity,
                category=flag.category or line.value,
                evidence=[flag.code],
            )
        )
    return findings


def evaluate_commercial_checklist(bundle: SubmissionBundle, line: InsuranceLine) -> CommercialUWResult:
    """Run LOB checklist + scenario engine and return aggregated UW result."""
    blob = _blob(bundle).lower()
    evaluator = _EVALUATORS.get(line, _eval_property)
    flags, scenarios = evaluator(blob)

    # Additive BI pass: business-interruption coverages ride on property lines,
    # so evaluate them whenever the package carries BI / extra-expense terms.
    if any(t in blob for t in _BI_TRIGGERS):
        try:
            bi_flags, bi_scenarios = _eval_bi(blob)
            flags = list(flags) + bi_flags
            scenarios = list(scenarios) + bi_scenarios
        except Exception:
            pass

    actions: list[UWAction] = []
    for scenario in scenarios:
        actions.extend(scenario.actions)

    premium_mod_pct = sum(a.premium_mod_pct for a in actions)

    decision = _decision_from_flags_and_actions(flags, actions, scenarios)
    findings = _flags_to_findings(flags, line)

    for scenario in scenarios:
        findings.append(
            Finding(
                title=f"Scenario: {scenario.name}",
                description=scenario.description,
                severity=RiskSeverity.HIGH,
                category=line.value,
                evidence=[scenario.code, *scenario.flag_codes],
            )
        )

    story = _build_story(line, flags, scenarios, decision, actions, premium_mod_pct)

    return CommercialUWResult(
        line=line,
        decision=decision,
        flags=flags,
        scenarios=scenarios,
        actions=actions,
        findings=findings,
        premium_mod_pct=premium_mod_pct,
        story=story,
    )
