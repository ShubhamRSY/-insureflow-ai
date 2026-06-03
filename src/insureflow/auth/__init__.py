from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    UNDERWRITER = "underwriter"
    VIEWER = "viewer"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 1,
    Role.UNDERWRITER: 2,
    Role.ADMIN: 3,
}
