from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from insureflow.auth import Role
from insureflow.auth.dependencies import get_current_user
from insureflow.auth.models import TokenData
from insureflow.models.company import CompanyCreate, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])

# In-memory store for MVP (can be swapped to DB later)
_COMPANIES: Dict[str, Dict[str, Any]] = {}


def _is_admin(current: TokenData) -> bool:
    return current.role == Role.ADMIN


def _require_owner_or_admin(company: Dict[str, Any], current: TokenData, action: str) -> None:
    """Fails closed: only the recorded owner or an admin may change a company. No owner means admin only."""
    owner = company.get("owner_id")
    if _is_admin(current) or (owner and current.username and owner == current.username):
        return
    raise HTTPException(status_code=403, detail=f"Not authorized to {action} this company")


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or f"company-{uuid.uuid4().hex[:8]}"


@router.get("/{slug}")
def get_company(slug: str) -> Dict[str, Any]:
    company = _COMPANIES.get(slug)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("")
def list_companies(limit: int = 50) -> List[Dict[str, Any]]:
    companies = list(_COMPANIES.values())
    return companies[:limit]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, current: TokenData = Depends(get_current_user)) -> Dict[str, Any]:
    if not current.username:
        raise HTTPException(status_code=401, detail="Sign in to create a company page")
    if payload.is_verified and not _is_admin(current):
        raise HTTPException(status_code=403, detail="Only an admin can mark a company verified")
    slug = payload.slug or _slugify(payload.name)
    if slug in _COMPANIES:
        raise HTTPException(status_code=409, detail="Company with this slug already exists")

    now = datetime.now(timezone.utc)
    company_id = str(uuid.uuid4())
    specialties = payload.specialties
    if isinstance(specialties, str):
        specialties = [s.strip() for s in specialties.split(",") if s.strip()]

    company = {
        "id": company_id,
        "slug": slug,
        "name": payload.name,
        "logo_url": payload.logo_url,
        "cover_url": payload.cover_url,
        "website": payload.website,
        "industry": payload.industry,
        "company_size": payload.company_size,
        "headquarters": payload.headquarters,
        "organization_type": payload.organization_type,
        "about": payload.about,
        "specialties": specialties or [],
        "owner_id": current.username,  # always the signed-in user, never taken from the request
        "is_verified": payload.is_verified,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _COMPANIES[slug] = company
    return company


@router.put("/{slug}")
def update_company(slug: str, payload: CompanyUpdate, current: TokenData = Depends(get_current_user)) -> Dict[str, Any]:
    company = _COMPANIES.get(slug)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    _require_owner_or_admin(company, current, "edit")
    update_data = payload.model_dump(exclude_unset=True)
    if "is_verified" in update_data and not _is_admin(current):
        raise HTTPException(status_code=403, detail="Only an admin can change verification")
    if "specialties" in update_data and isinstance(update_data["specialties"], str):
        update_data["specialties"] = [s.strip() for s in update_data["specialties"].split(",") if s.strip()]

    company.update(update_data)
    company["updated_at"] = datetime.now(timezone.utc).isoformat()
    _COMPANIES[slug] = company
    return company


@router.delete("/{slug}")
def delete_company(slug: str, current: TokenData = Depends(get_current_user)) -> Dict[str, str]:
    company = _COMPANIES.get(slug)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    _require_owner_or_admin(company, current, "delete")
    del _COMPANIES[slug]
    return {"message": "Company deleted"}
