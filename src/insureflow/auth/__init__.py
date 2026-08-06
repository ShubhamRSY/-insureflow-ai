from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    LICENSED_UW = "licensed_uw"
    STAFF_UW = "staff_uw"  # Home-office staff underwriter (policy, guides, audits)
    UNDERWRITER = "underwriter"  # Line underwriter (branch / regional process)
    VIEWER = "viewer"
    CUO = "cuo"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 1,
    Role.UNDERWRITER: 2,  # Line UW
    Role.STAFF_UW: 2,  # Staff UW — same hierarchy band; desk differs
    Role.LICENSED_UW: 3,
    Role.ADMIN: 4,
    Role.CUO: 5,
}
