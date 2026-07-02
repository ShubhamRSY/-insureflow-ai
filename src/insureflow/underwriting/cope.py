"""COPE Risk Analysis — Construction, Occupancy, Protection, Exposure.

This is the standard property underwriting framework used across the
P&C insurance industry. Every property submission is scored on four
pillars, each contributing to the overall risk grade and the schedule
rating debit/credit modifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from insureflow.models.submissions import SubmissionBundle


class ConstructionClass(str, Enum):
    FRAME = "frame"  # Wood frame — highest fire risk
    JOISTED_MASONRY = "joisted_masonry"  # Masonry walls, wood roof
    MASONRY_NON_COMBUSTIBLE = "masonry_non_combustible"  # Masonry walls, steel roof
    MODIFIED_FIRE_RESISTIVE = "modified_fire_resistive"  # Masonry with fire protection
    FIRE_RESISTIVE = "fire_resistive"  # Reinforced concrete/steel with fireproofing


class OccupancyClass(str, Enum):
    MERCANTILE = "mercantile"  # Retail stores, restaurants
    OFFICE = "office"  # Professional offices
    MANUFACTURING = "manufacturing"  # Factories, assembly plants
    WAREHOUSE = "warehouse"  # Storage, distribution
    LODGING = "lodging"  # Hotels, motels
    INSTITUTIONAL = "institutional"  # Schools, churches, hospitals
    HABITATIONAL = "habitational"  # Apartment buildings
    SERVICE = "service"  # Repair shops, cleaners, auto
    SPECIAL = "special"  # Theaters, bowling alleys


class ProtectionClass(int, Enum):
    """ISO Protection Class 1 (best) through 10 (worst)."""

    PC_1 = 1
    PC_2 = 2
    PC_3 = 3
    PC_4 = 4
    PC_5 = 5
    PC_6 = 6
    PC_7 = 7
    PC_8 = 8
    PC_9 = 9
    PC_10 = 10


class ExposureType(str, Enum):
    COASTAL_WIND = "coastal_wind"
    INLAND_WIND = "inland_wind"
    EARTHQUAKE = "earthquake"
    WILDFIRE = "wildfire"
    FLOOD = "flood"
    HAIL = "hail"
    TERRORISM = "terrorism"
    SINKHOLE = "sinkhole"
    MINE_SUBSIDENCE = "mine_subsidence"
    NONE = "none"


class RiskGrade(str, Enum):
    PREFERRED = "preferred"  # Best risks, lowest rate
    STANDARD = "standard"  # Acceptable risks, standard rate
    NON_STANDARD = "non_standard"  # Higher risk, surcharged rate
    DECLINED = "declined"  # Cannot write


@dataclass
class COPEScore:
    construction_score: float = 0.0  # 0.0 (best) to 1.0 (worst)
    occupancy_score: float = 0.0
    protection_score: float = 0.0
    exposure_score: float = 0.0
    total_score: float = 0.0
    risk_grade: RiskGrade = RiskGrade.STANDARD
    schedule_mod_pct: float = 0.0  # Debit (+) or credit (-) from schedule rating

    construction_mod_pct: float = 0.0
    occupancy_mod_pct: float = 0.0
    protection_mod_pct: float = 0.0
    exposure_mod_pct: float = 0.0


CONSTRUCTION_MODIFIERS: dict[ConstructionClass, float] = {
    ConstructionClass.FRAME: 25.0,
    ConstructionClass.JOISTED_MASONRY: 15.0,
    ConstructionClass.MASONRY_NON_COMBUSTIBLE: 0.0,
    ConstructionClass.MODIFIED_FIRE_RESISTIVE: -10.0,
    ConstructionClass.FIRE_RESISTIVE: -15.0,
}

OCCUPANCY_MODIFIERS: dict[OccupancyClass, float] = {
    OccupancyClass.MERCANTILE: 0.0,
    OccupancyClass.OFFICE: -5.0,
    OccupancyClass.MANUFACTURING: 15.0,
    OccupancyClass.WAREHOUSE: 5.0,
    OccupancyClass.LODGING: 10.0,
    OccupancyClass.INSTITUTIONAL: -5.0,
    OccupancyClass.HABITATIONAL: 5.0,
    OccupancyClass.SERVICE: 10.0,
    OccupancyClass.SPECIAL: 20.0,
}

PROTECTION_MODIFIERS: dict[int, float] = {
    1: -15.0,
    2: -10.0,
    3: -5.0,
    4: 0.0,
    5: 5.0,
    6: 10.0,
    7: 15.0,
    8: 20.0,
    9: 25.0,
    10: 35.0,
}

EXPOSURE_MODIFIERS: dict[ExposureType, float] = {
    ExposureType.NONE: 0.0,
    ExposureType.INLAND_WIND: 5.0,
    ExposureType.HAIL: 5.0,
    ExposureType.COASTAL_WIND: 25.0,
    ExposureType.WILDFIRE: 15.0,
    ExposureType.FLOOD: 10.0,
    ExposureType.EARTHQUAKE: 20.0,
    ExposureType.TERRORISM: 10.0,
    ExposureType.SINKHOLE: 15.0,
    ExposureType.MINE_SUBSIDENCE: 15.0,
}

# Construction class mapping from common description strings
CONSTRUCTION_MAP: dict[str, ConstructionClass] = {
    "frame": ConstructionClass.FRAME,
    "wood": ConstructionClass.FRAME,
    "wood frame": ConstructionClass.FRAME,
    "joisted masonry": ConstructionClass.JOISTED_MASONRY,
    "masonry": ConstructionClass.MASONRY_NON_COMBUSTIBLE,
    "masonry non-combustible": ConstructionClass.MASONRY_NON_COMBUSTIBLE,
    "masonry non combustible": ConstructionClass.MASONRY_NON_COMBUSTIBLE,
    "modified fire resistive": ConstructionClass.MODIFIED_FIRE_RESISTIVE,
    "fire resistive": ConstructionClass.FIRE_RESISTIVE,
    "reinforced concrete": ConstructionClass.FIRE_RESISTIVE,
    "steel": ConstructionClass.FIRE_RESISTIVE,
    "concrete": ConstructionClass.FIRE_RESISTIVE,
}

OCCUPANCY_MAP: dict[str, OccupancyClass] = {
    "retail": OccupancyClass.MERCANTILE,
    "restaurant": OccupancyClass.MERCANTILE,
    "store": OccupancyClass.MERCANTILE,
    "mercantile": OccupancyClass.MERCANTILE,
    "office": OccupancyClass.OFFICE,
    "professional": OccupancyClass.OFFICE,
    "manufacturing": OccupancyClass.MANUFACTURING,
    "factory": OccupancyClass.MANUFACTURING,
    "plant": OccupancyClass.MANUFACTURING,
    "warehouse": OccupancyClass.WAREHOUSE,
    "storage": OccupancyClass.WAREHOUSE,
    "distribution": OccupancyClass.WAREHOUSE,
    "hotel": OccupancyClass.LODGING,
    "motel": OccupancyClass.LODGING,
    "lodging": OccupancyClass.LODGING,
    "apartment": OccupancyClass.HABITATIONAL,
    "habitational": OccupancyClass.HABITATIONAL,
    "church": OccupancyClass.INSTITUTIONAL,
    "school": OccupancyClass.INSTITUTIONAL,
    "hospital": OccupancyClass.INSTITUTIONAL,
    "institutional": OccupancyClass.INSTITUTIONAL,
    "service": OccupancyClass.SERVICE,
    "repair": OccupancyClass.SERVICE,
    "auto": OccupancyClass.SERVICE,
    "theater": OccupancyClass.SPECIAL,
    "special": OccupancyClass.SPECIAL,
    "bowling": OccupancyClass.SPECIAL,
}


@dataclass
class COPEAnalysisResult:
    construction_class: Optional[ConstructionClass] = None
    construction_raw: str = ""
    occupancy_class: Optional[OccupancyClass] = None
    occupancy_raw: str = ""
    protection_class: Optional[int] = None
    exposure_types: list[ExposureType] = field(default_factory=list)

    score: COPEScore = field(default_factory=COPEScore)

    # Detailed findings
    construction_detail: str = ""
    occupancy_detail: str = ""
    protection_detail: str = ""
    exposure_detail: str = ""

    year_built: Optional[int] = None
    square_footage: Optional[float] = None
    number_of_stories: Optional[int] = None
    sprinklered: Optional[bool] = None


def _classify_construction(construction_str: str) -> Optional[ConstructionClass]:
    if not construction_str:
        return None
    key = construction_str.strip().lower()
    for k, v in CONSTRUCTION_MAP.items():
        if k in key or key in k:
            return v
    return None


def _classify_occupancy(occupancy_str: str) -> Optional[OccupancyClass]:
    if not occupancy_str:
        return None
    key = occupancy_str.strip().lower()
    for k, v in OCCUPANCY_MAP.items():
        if k in key or key in k:
            return v
    return None


def _exposure_for_state(state: str) -> list[ExposureType]:
    exposures: list[ExposureType] = []
    coastal_state = {"FL", "TX", "LA", "SC", "NC", "GA", "AL", "MS", "HI"}
    if state.upper() in coastal_state:
        exposures.append(ExposureType.COASTAL_WIND)
    elif state.upper() in {"OK", "KS", "NE", "SD", "ND", "CO", "WY"}:
        exposures.append(ExposureType.INLAND_WIND)
        exposures.append(ExposureType.HAIL)
    elif state.upper() in {"CA", "OR", "WA", "NV", "AZ", "UT", "CO", "ID", "MT", "WY", "NM"}:
        exposures.append(ExposureType.WILDFIRE)
    else:
        exposures.append(ExposureType.NONE)

    if state.upper() in {"CA", "AK", "OR", "WA", "NV", "UT", "ID", "MT", "HI"}:
        exposures.append(ExposureType.EARTHQUAKE)

    if state.upper() in {"FL", "LA", "TX", "MS", "AL", "GA", "NC", "SC", "NJ", "NY"}:
        exposures.append(ExposureType.FLOOD)

    return exposures


def analyze_cope(
    construction_type: str = "",
    occupancy_type: str = "",
    protection_class: Optional[int] = None,
    state: str = "",
    year_built: Optional[int] = None,
    sprinklered: Optional[bool] = None,
    number_of_stories: Optional[int] = None,
    building_value: Optional[float] = None,
) -> COPEAnalysisResult:
    """Run full COPE analysis and return structured result with schedule rating modifiers."""

    result = COPEAnalysisResult(
        construction_raw=construction_type,
        occupancy_raw=occupancy_type,
        year_built=year_built,
        sprinklered=sprinklered,
        number_of_stories=number_of_stories,
    )

    # C — Construction
    c_class = _classify_construction(construction_type)
    result.construction_class = c_class
    c_mod = CONSTRUCTION_MODIFIERS.get(c_class, 0.0) if c_class else 0.0
    c_score = 0.0
    if c_class in (ConstructionClass.FRAME, ConstructionClass.JOISTED_MASONRY):
        c_score = 0.8
        result.construction_detail = f"Frame construction is highest fire risk; applies +{c_mod:.0f}% schedule debit"
    elif c_class in (ConstructionClass.MASONRY_NON_COMBUSTIBLE,):
        c_score = 0.4
        result.construction_detail = "Masonry non-combustible construction provides moderate fire protection"
    elif c_class in (ConstructionClass.MODIFIED_FIRE_RESISTIVE,):
        c_score = 0.2
        result.construction_detail = f"Modified fire-resistive construction; applies {c_mod:.0f}% schedule credit"
    elif c_class == ConstructionClass.FIRE_RESISTIVE:
        c_score = 0.1
        result.construction_detail = f"Fire-resistive construction is best; applies {c_mod:.0f}% schedule credit"
    else:
        result.construction_detail = f"Construction type '{construction_type}' unclassified — no adjustment"

    # O — Occupancy
    o_class = _classify_occupancy(occupancy_type)
    result.occupancy_class = o_class
    o_mod = OCCUPANCY_MODIFIERS.get(o_class, 0.0) if o_class else 0.0
    o_score = 0.0
    if o_class in (OccupancyClass.SPECIAL, OccupancyClass.MANUFACTURING):
        o_score = 0.7
        result.occupancy_detail = f"{occupancy_type} occupancy has elevated risk; applies +{o_mod:.0f}% debit"
    elif o_class in (
        OccupancyClass.LODGING,
        OccupancyClass.SERVICE,
        OccupancyClass.HABITATIONAL,
        OccupancyClass.WAREHOUSE,
    ):
        o_score = 0.5
        result.occupancy_detail = f"{occupancy_type} has moderate risk; applies +{o_mod:.0f}% debit"
    elif o_class in (OccupancyClass.MERCANTILE,):
        o_score = 0.3
        result.occupancy_detail = "Standard mercantile occupancy; no adjustment"
    elif o_class in (OccupancyClass.OFFICE, OccupancyClass.INSTITUTIONAL):
        o_score = 0.2
        result.occupancy_detail = f"Low-risk occupancy; applies {o_mod:.0f}% schedule credit"
    else:
        result.occupancy_detail = f"Occupancy '{occupancy_type}' unclassified — no adjustment"

    # Additional occupancy factors
    if sprinklered:
        o_mod -= 5.0
        o_score = max(0.0, o_score - 0.1)
        result.occupancy_detail += " Sprinklered — 5% credit applied."

    if year_built and year_built < 1970:
        o_mod += 10.0
        o_score = min(1.0, o_score + 0.15)
        result.occupancy_detail += f" Building age ({year_built}) over 55 years — +10% age surcharge."
    if number_of_stories and number_of_stories > 5:
        o_mod += 5.0
        o_score = min(1.0, o_score + 0.1)
        result.occupancy_detail += f" Multi-story ({number_of_stories}) — +5% height surcharge."

    # P — Protection
    result.protection_class = protection_class
    p_mod = PROTECTION_MODIFIERS.get(protection_class, 0.0) if protection_class else 0.0
    p_score = 0.0
    if protection_class:
        if protection_class <= 3:
            p_score = 0.1
            result.protection_detail = f"ISO Class {protection_class} — excellent fire protection"
        elif protection_class <= 5:
            p_score = 0.3
            result.protection_detail = f"ISO Class {protection_class} — adequate fire protection"
        elif protection_class <= 7:
            p_score = 0.5
            result.protection_detail = f"ISO Class {protection_class} — below-average fire protection"
        else:
            p_score = 0.8
            result.protection_detail = f"ISO Class {protection_class} — poor fire protection"
    else:
        result.protection_detail = "No ISO protection class available — defaulting to moderate risk"

    # E — Exposure
    exposures = _exposure_for_state(state)
    result.exposure_types = exposures
    e_mod = sum(EXPOSURE_MODIFIERS.get(ex, 0.0) for ex in exposures)
    e_mod = min(e_mod, 45.0)  # Cap at 45%
    exposures[0] if exposures else ExposureType.NONE
    e_score = 0.0
    if ExposureType.COASTAL_WIND in exposures:
        e_score = 0.9
        result.exposure_detail = "Coastal wind zone — high CAT exposure"
    elif ExposureType.WILDFIRE in exposures:
        e_score = 0.6
        result.exposure_detail = "Wildfire zone — elevated CAT exposure"
    elif ExposureType.EARTHQUAKE in exposures:
        e_score = 0.5
        result.exposure_detail = "Earthquake zone — moderate CAT exposure"
    elif ExposureType.NONE in exposures and len(exposures) == 1:
        e_score = 0.1
        result.exposure_detail = "No significant CAT exposure identified"
    else:
        e_score = 0.3
        result.exposure_detail = f"Moderate exposures: {', '.join(e.value for e in exposures)}"

    # Total score (weighted: C=25%, O=25%, P=25%, E=25%)
    total_score = c_score * 0.25 + o_score * 0.25 + p_score * 0.25 + e_score * 0.25

    # Risk grade
    if total_score <= 0.25:
        grade = RiskGrade.PREFERRED
    elif total_score <= 0.50:
        grade = RiskGrade.STANDARD
    elif total_score <= 0.75:
        grade = RiskGrade.NON_STANDARD
    else:
        grade = RiskGrade.DECLINED

    # Total schedule mod (minimum -25%, maximum +50%)
    schedule_mod = c_mod + o_mod + p_mod + e_mod
    schedule_mod = max(-25.0, min(50.0, schedule_mod))

    result.score = COPEScore(
        construction_score=c_score,
        occupancy_score=o_score,
        protection_score=p_score,
        exposure_score=e_score,
        total_score=round(total_score, 3),
        risk_grade=grade,
        schedule_mod_pct=round(schedule_mod, 1),
        construction_mod_pct=c_mod,
        occupancy_mod_pct=o_mod,
        protection_mod_pct=p_mod,
        exposure_mod_pct=e_mod,
    )

    return result


class COPERatingEngine:
    """Applies COPE analysis to produce schedule rating modifiers for the rating engine."""

    def analyze(self, bundle: SubmissionBundle) -> COPEAnalysisResult:
        constr = ""
        occup = ""
        prot_class = None
        state = ""
        year_built = None
        sprinklered = None
        stories = None
        bldg_value = None

        if bundle.structured:
            if bundle.structured.risk_profile:
                constr = bundle.structured.risk_profile.construction_type or ""
                occup = bundle.structured.risk_profile.occupancy_type or ""
                sprinklered = bundle.structured.risk_profile.sprinklered
                stories = bundle.structured.risk_profile.number_of_stories
            if bundle.structured.locations:
                loc = bundle.structured.locations[0]
                state = loc.state or ""
                prot_class = loc.protection_class
                bldg_value = loc.building_value
                year_built = loc.year_built

        # Also try extracted fields from unstructured
        if not constr or not occup:
            for doc in bundle.unstructured:
                for fields in doc.extracted_fields.get("construction_type", []):
                    constr = constr or fields.value
                for fields in doc.extracted_fields.get("occupancy_type", []):
                    occup = occup or fields.value
                for fields in doc.extracted_fields.get("state", []):
                    state = state or fields.value

        return analyze_cope(
            construction_type=constr,
            occupancy_type=occup,
            protection_class=prot_class,
            state=state,
            year_built=year_built,
            sprinklered=sprinklered,
            number_of_stories=stories,
            building_value=bldg_value,
        )
