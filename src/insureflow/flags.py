"""In-process runtime flags — not LaunchDarkly.

Bank/lab switches already live as env vars. This module is the catalog so ops
can see what is on without a third-party flag service.
"""

from __future__ import annotations

import os
from typing import Any


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def current_flags() -> dict[str, Any]:
    return {
        "BANK_MODE": _bool("BANK_MODE"),
        "SSO_ENABLED": _bool("SSO_ENABLED"),
        "SSO_REQUIRED": _bool("SSO_REQUIRED"),
        "OPERATING_MODE": (os.getenv("OPERATING_MODE") or "shadow").strip() or "shadow",
        "PILOT_SHADOW_MODE": _bool("PILOT_SHADOW_MODE"),
        "ALLOW_OPEN_REGISTRATION": _bool("ALLOW_OPEN_REGISTRATION"),
        "ALLOW_AUTH_RESET": _bool("ALLOW_AUTH_RESET"),
        "ALLOW_SIMULATED_BIND": _bool("ALLOW_SIMULATED_BIND"),
        "ALLOW_VISION_EGRESS": _bool("ALLOW_VISION_EGRESS"),
        "ALLOW_EMBEDDING_EGRESS": _bool("ALLOW_EMBEDDING_EGRESS"),
        "RETAIN_SOURCE_DOCS": _bool("RETAIN_SOURCE_DOCS"),
        "LANGSMITH_ALLOW_IN_BANK": _bool("LANGSMITH_ALLOW_IN_BANK"),
        "REQUIRE_LIVE_ORACLES": _bool("REQUIRE_LIVE_ORACLES"),
        "CLOUDWATCH_LOGS": _bool("CLOUDWATCH_LOGS"),
        "CLOUDWATCH_METRICS": _bool("CLOUDWATCH_METRICS"),
        "TRUSTED_PROXY": _bool("TRUSTED_PROXY"),
    }
