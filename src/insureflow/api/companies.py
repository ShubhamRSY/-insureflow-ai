from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from insureflow.auth.dependencies import get_current_user_optional
from insureflow.auth.models import TokenData
from insureflow.models.company import CompanyCreate, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])

# In-memory store for MVP (can be swapped to DB later)
_COMPANIES: Dict[str, Dict[str, Any]] = {}


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
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
def create_company(payload: CompanyCreate, current: TokenData | None = Depends(get_current_user_optional)) -> Dict[str, Any]:
    slug = payload.slug or _slugify(payload.name)
    if slug in _COMPANIES:
        raise HTTPException(status_code=409, detail="Company with this slug already exists")

    now = datetime.now(timezone.utc)
    company_id = str(uuid.uuid4())
    specialties = payload.specialties
    if isinstance(specialties, str):
        specialties = [s.strip() for s in specialties.split(',') if s.strip()]

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
        "owner_id": payload.owner_id or (current.username if current else None),
        "is_verified": payload.is_verified,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _COMPANIES[slug] = company
    return company


@router.put("/{slug}")
def update_company(slug: str, payload: CompanyUpdate, current: TokenData | None = Depends(get_current_user_optional)) -> Dict[str, Any]:
    company = _COMPANIES.get(slug)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Basic ownership check if owner exists
    if company.get("owner_id") and current and company.get("owner_id") != current.username:
        raise HTTPException(status_code=403, detail="Not authorized to edit this company")

    update_data = payload.model_dump(exclude_unset=True)
    if "specialties" in update_data and isinstance(update_data["specialties"], str):
        update_data["specialties"] = [s.strip() for s in update_data["specialties"].split(',') if s.strip()]

    company.update(update_data)
    company["updated_at"] = datetime.now(timezone.utc).isoformat()
    _COMPANIES[slug] = company
    return company


@router.delete("/{slug}")
def delete_company(slug: str, current: TokenData | None = Depends(get_current_user_optional)) -> Dict[str, str]:
    company = _COMPANIES.get(slug)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.get("owner_id") and current and company.get("owner_id") != current.username:
        role = getattr(current, "role", None)
        role_val = getattr(role, "value", role) if role else None
        if role_val != "admin":
            raise HTTPException(status_code=403, detail="Not authorized to delete this company")

    del _COMPANIES[slug]
    return {"message": "Company deleted"}
