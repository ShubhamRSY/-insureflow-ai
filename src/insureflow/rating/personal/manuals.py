"""Load personal-lines rate manuals and medical guides from data/personal_lines."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


def _default_root() -> Path:
    env = (os.getenv("PERSONAL_LINES_MANUALS_PATH") or "").strip()
    if env:
        return Path(env)
    # Packaged filings ship with the module (data/ may be gitignored in deploy images).
    packaged = Path(__file__).resolve().parent / "filings"
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[4] / "data" / "personal_lines"


def load_manual(name: str) -> dict[str, Any]:
    return _load_manual_cached(name)


@lru_cache(maxsize=8)
def _load_manual_cached(name: str) -> dict[str, Any]:
    path = _default_root() / name
    if not path.exists():
        raise FileNotFoundError(f"Personal lines manual not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def clear_manual_cache() -> None:
    _load_manual_cached.cache_clear()


def homeowners_manual() -> dict[str, Any]:
    return load_manual("homeowners_rate_manual.json")


def auto_manual() -> dict[str, Any]:
    return load_manual("auto_rate_manual.json")


def life_manual() -> dict[str, Any]:
    return load_manual("life_rate_manual.json")


def life_medical_guide() -> dict[str, Any]:
    return load_manual("life_medical_guide.json")


def _band_factor(bands: list[dict[str, Any]], value: float, max_key: str, factor_key: str = "factor") -> float:
    for band in bands:
        mx = band.get(max_key)
        if mx is None or value <= float(mx):
            return float(band[factor_key])
    return float(bands[-1][factor_key]) if bands else 1.0


def nearest_key(table: dict[str, Any], age: int) -> str:
    keys = sorted(int(k) for k in table.keys())
    if not keys:
        return "40"
    best = min(keys, key=lambda k: abs(k - age))
    return str(best)
