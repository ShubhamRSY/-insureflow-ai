"""Case assignment systems — Chapter 4.

Chapter 4 describes the common systems by which applications are assigned to
underwriters: by face amount (larger amounts to senior underwriters), by type
of application (new vs. renewal), by geographic origin (territory desks), and
by alphabetical distribution of the insured's name. This module implements all
four as structured, deterministic rules plus a fair-distribution fallback so
the automation can assign a case consistently with how a manual desk operates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AssignmentMethod(str, Enum):
    FACE_AMOUNT = "face_amount"
    APPLICATION_TYPE = "application_type"
    GEOGRAPHIC = "geographic"
    LAST_NAME = "last_name"
    ROTATION = "rotation"  # fair-distribution fallback


class CaseType(str, Enum):
    NEW = "new"
    RENEWAL = "renewal"
    ENDORSEMENT = "endorsement"
    FLAT_CANCEL = "flat_cancel"


@dataclass
class CaseAssignment:
    """The result of assigning a case to an underwriter desk."""

    case_id: str
    assigned_desk: str = ""
    method: AssignmentMethod = AssignmentMethod.FACE_AMOUNT
    reason: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


# Face-amount thresholds (premium proxy when face amount unavailable).
_FACE_AMOUNT_BANDS: list[tuple[float, str]] = [
    (250_000, "junior_desk"),
    (1_000_000, "standard_desk"),
    (10_000_000, "senior_desk"),
    (float("inf"), "executive_desk"),
]

# Geographic territory → desk mapping.
_TERRITORY_DESKS: dict[str, str] = {
    "TX": "southwest_desk",
    "OK": "southwest_desk",
    "AR": "southwest_desk",
    "LA": "gulf_desk",
    "MS": "gulf_desk",
    "AL": "gulf_desk",
    "FL": "gulf_desk",
    "GA": "southeast_desk",
    "NC": "southeast_desk",
    "SC": "southeast_desk",
    "CA": "west_desk",
    "WA": "west_desk",
    "OR": "west_desk",
    "NY": "northeast_desk",
    "NJ": "northeast_desk",
    "CT": "northeast_desk",
    "MA": "northeast_desk",
}

# Alphabetical buckets → desk, classic last-name distribution.
_LAST_NAME_BANDS: list[tuple[str, str, str]] = [
    ("a", "f", "desk_af"),
    ("g", "m", "desk_gm"),
    ("n", "r", "desk_nr"),
    ("s", "z", "desk_sz"),
]

# Application-type → desk.
_CASE_TYPE_DESKS: dict[CaseType, str] = {
    CaseType.NEW: "new_business_desk",
    CaseType.RENEWAL: "renewal_desk",
    CaseType.ENDORSEMENT: "endorsement_desk",
    CaseType.FLAT_CANCEL: "endorsement_desk",
}

# Fair-distribution desks for rotation fallback.
_ROTATION_DESKS = [
    "desk_af",
    "desk_gm",
    "desk_nr",
    "desk_sz",
]


def _face_amount_band(face_amount: float) -> str:
    for threshold, desk in _FACE_AMOUNT_BANDS:
        if face_amount <= threshold:
            return desk
    return "executive_desk"


def _last_name_band(name: str) -> str:
    if not name:
        return "desk_af"
    first = name.strip().lower()[0]
    for lo, hi, desk in _LAST_NAME_BANDS:
        if lo <= first <= hi:
            return desk
    return "desk_af"


def assign_by_face_amount(face_amount: float) -> CaseAssignment:
    desk = _face_amount_band(face_amount)
    return CaseAssignment(
        case_id="",
        assigned_desk=desk,
        method=AssignmentMethod.FACE_AMOUNT,
        reason=f"Face amount ${face_amount:,.0f} assigned to {desk}",
        attributes={"face_amount": face_amount},
    )


def assign_by_application_type(case_type: CaseType) -> CaseAssignment:
    desk = _CASE_TYPE_DESKS[case_type]
    return CaseAssignment(
        case_id="",
        assigned_desk=desk,
        method=AssignmentMethod.APPLICATION_TYPE,
        reason=f"{case_type.value} case assigned to {desk}",
        attributes={"case_type": case_type.value},
    )


def assign_by_geography(state: str, territory: str = "") -> CaseAssignment:
    desk = _TERRITORY_DESKS.get(state.upper(), _TERRITORY_DESKS.get(territory.upper(), "general_desk"))
    return CaseAssignment(
        case_id="",
        assigned_desk=desk,
        method=AssignmentMethod.GEOGRAPHIC,
        reason=f"Risk in {state or territory or 'unknown territory'} assigned to {desk}",
        attributes={"state": state, "territory": territory},
    )


def assign_by_last_name(insured_name: str) -> CaseAssignment:
    desk = _last_name_band(insured_name)
    return CaseAssignment(
        case_id="",
        assigned_desk=desk,
        method=AssignmentMethod.LAST_NAME,
        reason=f"Insured name '{insured_name}' assigned to {desk}",
        attributes={"insured_name": insured_name},
    )


def assign_by_rotation(rotation_index: int) -> CaseAssignment:
    desk = _ROTATION_DESKS[rotation_index % len(_ROTATION_DESKS)]
    return CaseAssignment(
        case_id="",
        assigned_desk=desk,
        method=AssignmentMethod.ROTATION,
        reason=f"Rotation index {rotation_index} assigned to {desk}",
        attributes={"rotation_index": rotation_index},
    )


class CaseAssignmentEngine:
    """Assigns a case using the configured Chapter 4 systems.

    The engine runs the systems in priority order and returns the first one
    that yields a specific desk. ``method`` selects which single system to use;
    when ``None`` it falls through face amount → application type → geography →
    last name → rotation, mirroring how a manual desk prioritizes.
    """

    def __init__(
        self,
        *,
        method: Optional[AssignmentMethod] = None,
        priority: Optional[list[AssignmentMethod]] = None,
    ) -> None:
        self.method = method
        self.priority = priority or [
            AssignmentMethod.FACE_AMOUNT,
            AssignmentMethod.APPLICATION_TYPE,
            AssignmentMethod.GEOGRAPHIC,
            AssignmentMethod.LAST_NAME,
            AssignmentMethod.ROTATION,
        ]

    def assign(
        self,
        *,
        case_id: str = "",
        face_amount: float = 0.0,
        case_type: CaseType = CaseType.NEW,
        state: str = "",
        territory: str = "",
        insured_name: str = "",
        rotation_index: int = 0,
    ) -> CaseAssignment:
        methods = [self.method] if self.method else self.priority
        for m in methods:
            if m == AssignmentMethod.FACE_AMOUNT:
                result = assign_by_face_amount(face_amount)
            elif m == AssignmentMethod.APPLICATION_TYPE:
                result = assign_by_application_type(case_type)
            elif m == AssignmentMethod.GEOGRAPHIC:
                result = assign_by_geography(state, territory)
            elif m == AssignmentMethod.LAST_NAME:
                result = assign_by_last_name(insured_name)
            else:
                result = assign_by_rotation(rotation_index)
            result.case_id = case_id
            if result.assigned_desk:
                return result

        result = assign_by_rotation(rotation_index)
        result.case_id = case_id
        return result
