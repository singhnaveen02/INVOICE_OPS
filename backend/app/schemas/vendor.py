from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VendorCreate(BaseModel):
    name: str
    gstin: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    country: str = "US"
    approval_status: str = "PENDING"
    notes: Optional[str] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None


class VendorResponse(BaseModel):
    id: str
    name: str
    gstin: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    country: str
    approval_status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VendorListResponse(BaseModel):
    items: list[VendorResponse]
    total: int
    page: int
    page_size: int
