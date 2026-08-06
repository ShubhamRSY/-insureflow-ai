"""Line vs staff underwriter desks — classical insurer role model.

Insurers distinguish:
- Line underwriters: implement the underwriting process in branch/regional offices
- Staff underwriters: set and govern underwriting policy from the home office

Activities can overlap (e.g. staff UW on large/unusual accounts). This module
defines desks, capabilities, and how JWT roles map onto them.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from insureflow.auth import Role


class UnderwriterDesk(str, Enum):
    """Which underwriting desk a person sits on."""

    LINE = "line"
    STAFF = "staff"
    BOTH = "both"


# Capability catalog mirrors textbook line / staff activity lists.
LINE_CAPABILITIES: list[dict[str, str]] = [
    {
        "id": "uw_process",
        "title": "Implement the underwriting process",
        "description": "Intake → risk analysis → decision → quote → bind → issuance.",
    },
    {
        "id": "coverage_assist",
        "title": "Determine appropriate coverage",
        "description": "Match forms and endorsements to exposures; broaden or narrow coverage.",
    },
    {
        "id": "producer_service",
        "title": "Service producers",
        "description": "Quotations, proposals, endorsements, certificates, renewals, and info requests.",
    },
    {
        "id": "policyholder_service",
        "title": "Service policyholders",
        "description": "Cancellations, endorsements, certificates, and routine policy service.",
    },
]

STAFF_CAPABILITIES: list[dict[str, str]] = [
    {
        "id": "market_research",
        "title": "Research the market",
        "description": "Target markets, state expansion, product mix, and premium volume goals.",
    },
    {
        "id": "coverage_development",
        "title": "Research and develop coverages",
        "description": "Modify forms/endorsements for market or regulatory change.",
    },
    {
        "id": "experience_evaluation",
        "title": "Evaluate underwriting experience",
        "description": "Loss and premium trends by line, class, size, and territory.",
    },
    {
        "id": "rating_plans",
        "title": "Review and revise rating plans",
        "description": "Update rates and plans using ISO/AAIS/NCCI loss costs plus expense/profit loads.",
    },
    {
        "id": "uw_policy",
        "title": "Formulate underwriting policy",
        "description": "Set selection standards and communicate via guides and bulletins.",
    },
    {
        "id": "uw_guides",
        "title": "Develop underwriting guides",
        "description": "Author and version the underwriting guide used by line underwriters.",
    },
    {
        "id": "uw_audits",
        "title": "Conduct underwriting audits",
        "description": "File reviews and statistical monitoring for guideline compliance.",
    },
    {
        "id": "education",
        "title": "Assist with education and training",
        "description": "Identify line UW training needs and deliver technical courses.",
    },
]


def desk_for_role(role: Role | str | None) -> UnderwriterDesk:
    """Map JWT RBAC role onto an underwriting desk."""
    if role is None:
        return UnderwriterDesk.LINE
    value = role.value if isinstance(role, Role) else str(role)
    if value in (Role.STAFF_UW.value, Role.CUO.value, Role.ADMIN.value):
        return UnderwriterDesk.BOTH if value == Role.ADMIN.value else UnderwriterDesk.STAFF
    if value in (Role.UNDERWRITER.value, Role.LICENSED_UW.value):
        return UnderwriterDesk.LINE
    return UnderwriterDesk.LINE


def role_supports_staff_desk(role: Role | str | None) -> bool:
    if role is None:
        return False
    value = role.value if isinstance(role, Role) else str(role)
    return value in {
        Role.STAFF_UW.value,
        Role.ADMIN.value,
        Role.CUO.value,
        Role.LICENSED_UW.value,  # overlap: large/unusual accounts
    }


def capabilities_overview() -> dict[str, Any]:
    return {
        "desks": {
            UnderwriterDesk.LINE.value: {
                "label": "Line Underwriter",
                "location": "Branch or regional office",
                "primary": "Implement the steps in the underwriting process",
                "capabilities": LINE_CAPABILITIES,
            },
            UnderwriterDesk.STAFF.value: {
                "label": "Staff Underwriter",
                "location": "Home office",
                "primary": "Make and implement underwriting policy",
                "capabilities": STAFF_CAPABILITIES,
            },
            UnderwriterDesk.BOTH.value: {
                "label": "Line + Staff",
                "location": "Hybrid",
                "primary": "Operational UW plus policy, guides, and audits",
                "capabilities": LINE_CAPABILITIES + STAFF_CAPABILITIES,
            },
        },
        "overlap_note": (
            "Line and staff activities sometimes overlap. Staff underwriters may "
            "participate in individual decisions for large or unusual accounts when "
            "fit with overall underwriting goals must be judged at home office."
        ),
        "role_mapping": {
            Role.UNDERWRITER.value: UnderwriterDesk.LINE.value,
            Role.LICENSED_UW.value: UnderwriterDesk.LINE.value,
            Role.STAFF_UW.value: UnderwriterDesk.STAFF.value,
            Role.ADMIN.value: UnderwriterDesk.BOTH.value,
            Role.CUO.value: UnderwriterDesk.STAFF.value,
            Role.VIEWER.value: UnderwriterDesk.LINE.value,
        },
    }
