"""Load ISO/Verisk-style rate curves from file or HTTP for pricing calibration.

When no real rate curves are configured (RATE_CURVES_URL or RATE_CURVES_PATH),
the module marks rates as synthetic and provides provenance metadata so the
rating engine can track whether a quote used real filed rates or built-in
representative values.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] | None = None


def default_curve_path() -> Path:
    return Path(os.getenv("RATE_CURVES_PATH") or Path.cwd() / "data" / "rate_curves.json")


def load_rate_curves(*, force: bool = False) -> dict[str, Any]:
    """Return calibrated loss costs / LCMs / territory relativities when present.

    Returns a dict with:
        - "source": where the curves came from
        - "synthetic": True if no real curves are configured
        - "loss_costs", "lcm", "territory_relativities": the rate data (if real)
    """
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE

    payload: dict[str, Any] = {"source": "builtin", "synthetic": True}
    url = (os.getenv("RATE_CURVES_URL") or "").strip()
    path = default_curve_path()

    if url:
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
                payload = json.loads(resp.read().decode("utf-8"))
                payload.setdefault("source", url)
                payload["synthetic"] = False
        except Exception as exc:  # noqa: BLE001
            logger.warning("RATE_CURVES_URL fetch failed (%s) — trying file", exc)

    if payload.get("synthetic", True) and path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload.setdefault("source", str(path))
            payload["synthetic"] = False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load rate curves from %s: %s", path, exc)

    _CACHE = payload
    return payload


def is_rate_curves_synthetic() -> bool:
    """True when no real rate curves are configured — rates are built-in representative values."""
    curves = load_rate_curves()
    return bool(curves.get("synthetic", True))


def rate_curves_provenance() -> dict[str, Any]:
    """Return provenance metadata for the current rate curves configuration."""
    curves = load_rate_curves()
    return {
        "source": curves.get("source", "builtin"),
        "synthetic": bool(curves.get("synthetic", True)),
        "has_loss_costs": bool(curves.get("loss_costs")),
        "has_lcm": bool(curves.get("lcm")),
        "has_territory": bool(curves.get("territory_relativities")),
    }


def calibrated_loss_costs(builtin: dict[Any, float]) -> dict[Any, float]:
    curves = load_rate_curves()
    raw = curves.get("loss_costs") or {}
    if not raw:
        return builtin
    out = dict(builtin)
    for key, value in raw.items():
        for enum_key in list(out.keys()):
            if getattr(enum_key, "value", str(enum_key)) == key or str(enum_key) == key:
                out[enum_key] = float(value)
    return out


def calibrated_lcm(builtin: dict[Any, float]) -> dict[Any, float]:
    curves = load_rate_curves()
    raw = curves.get("lcm") or {}
    if not raw:
        return builtin
    out = dict(builtin)
    for key, value in raw.items():
        for enum_key in list(out.keys()):
            if getattr(enum_key, "value", str(enum_key)) == key or str(enum_key) == key:
                out[enum_key] = float(value)
    return out


def calibrated_territory(builtin: dict[str, dict[Any, float]]) -> dict[str, dict[Any, float]]:
    curves = load_rate_curves()
    raw = curves.get("territory_relativities") or {}
    if not raw:
        return builtin
    out: dict[str, dict[Any, float]] = {k: dict(v) for k, v in builtin.items()}
    for state, by_line in raw.items():
        bucket = out.setdefault(state, {})
        for line_key, value in (by_line or {}).items():
            matched = False
            for enum_key in list(bucket.keys()) or list(next(iter(builtin.values()), {}).keys()):
                if getattr(enum_key, "value", str(enum_key)) == line_key:
                    bucket[enum_key] = float(value)
                    matched = True
                    break
            if not matched:
                # Keep string key for later resolution
                bucket[line_key] = float(value)
    return out
