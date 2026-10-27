from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=120)
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    headquarters: Optional[str] = None
    organization_type: Optional[str] = None
    about: Optional[str] = None
    specialties: Optional[List[str] | str] = None
    is_verified: bool = False


class CompanyCreate(CompanyBase):
    owner_id: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    headquarters: Optional[str] = None
    organization_type: Optional[str] = None
    about: Optional[str] = None
    specialties: Optional[List[str] | str] = None
    is_verified: Optional[bool] = None


class Company(CompanyBase):
    id: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
