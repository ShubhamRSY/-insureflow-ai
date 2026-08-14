"""Appointed insurance-company panel — pick which writing company a file is for.

The desk chooses a company from the org's panel (or adds one). Rytera does not
invent a live market appointment. Rating still uses the loaded carrier book;
this choice is recorded on the job so UW, audit, and bind know whose paper it is.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_PANEL = _REPO_ROOT / "data" / "insurance" / "company_panel.json"
_ORG_PANELS = _REPO_ROOT / "data" / "insurance" / "panels"


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return slug[:64] or "company"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def default_panel() -> dict[str, Any]:
    data = _load_json(_DEFAULT_PANEL)
    companies = data.get("companies") or []
    return {
        "panel_id": data.get("panel_id") or "rytera_default_panel",
        "description": data.get("description") or "",
        "companies": [c for c in companies if isinstance(c, dict) and c.get("id") and c.get("name")],
    }


def org_overlay(org_id: str) -> list[dict[str, Any]]:
    safe = _slug(org_id or "default")
    data = _load_json(_ORG_PANELS / f"{safe}.json")
    companies = data.get("companies") or []
    return [c for c in companies if isinstance(c, dict) and c.get("id") and c.get("name")]


def list_companies(org_id: str = "default") -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for company in default_panel()["companies"] + org_overlay(org_id):
        cid = str(company.get("id") or "")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(
            {
                "id": cid,
                "name": str(company.get("name") or cid),
                "kind": str(company.get("kind") or "panel"),
                "naic": str(company.get("naic") or ""),
                "notes": str(company.get("notes") or ""),
            }
        )
    return out


def resolve_company(
    *,
    company_id: str = "",
    company_name: str = "",
    org_id: str = "default",
) -> dict[str, Any]:
    cid = (company_id or "").strip()
    name = (company_name or "").strip()
    if cid:
        for company in list_companies(org_id):
            if company["id"] == cid:
                if name:
                    company = {**company, "name": name}
                return company
        return {
            "id": cid,
            "name": name or cid.replace("-", " ").title(),
            "kind": "custom",
            "naic": "",
            "notes": "",
        }
    if name:
        return {
            "id": _slug(name),
            "name": name,
            "kind": "custom",
            "naic": "",
            "notes": "",
        }
    return {"id": "", "name": "", "kind": "", "naic": "", "notes": ""}


def add_company(
    org_id: str,
    *,
    name: str,
    naic: str = "",
    notes: str = "",
) -> dict[str, Any]:
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Company name is required")
    company = {
        "id": _slug(clean_name),
        "name": clean_name,
        "kind": "panel",
        "naic": (naic or "").strip(),
        "notes": (notes or "").strip(),
    }
    _ORG_PANELS.mkdir(parents=True, exist_ok=True)
    path = _ORG_PANELS / f"{_slug(org_id or 'default')}.json"
    data = _load_json(path)
    companies = [c for c in (data.get("companies") or []) if isinstance(c, dict)]
    companies = [c for c in companies if str(c.get("id") or "") != company["id"]]
    companies.append(company)
    path.write_text(json.dumps({"companies": companies}, indent=2) + "\n", encoding="utf-8")
    return company
