from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    LICENSED_UW = "licensed_uw"
    UNDERWRITER = "underwriter"
    VIEWER = "viewer"
    CUO = "cuo"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 1,
    Role.UNDERWRITER: 2,
    Role.LICENSED_UW: 3,
    Role.ADMIN: 4,
    Role.CUO: 5,
}
