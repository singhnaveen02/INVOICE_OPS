from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class POLineItemCreate(BaseModel):
    line_number: int
    description: str
    sku: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float
    unit_of_measure: str = "EA"


class POLineItemResponse(BaseModel):
    id: str
    po_id: str
    line_number: int
    description: str
    sku: Optional[str] = None
    quantity: float
    unit_price: float
    total_price: float
    unit_of_measure: str

    class Config:
        from_attributes = True


class POCreate(BaseModel):
    po_number: str
    vendor_id: str
    status: str = "OPEN"
    currency: str = "USD"
    total_amount: float
    utilized_amount: float = 0.0
    issue_date: date
    expiry_date: Optional[date] = None
    payment_terms: Optional[str] = None
    description: Optional[str] = None
    line_items: List[POLineItemCreate] = []


class POUpdate(BaseModel):
    status: Optional[str] = None
    utilized_amount: Optional[float] = None
    remaining_amount: Optional[float] = None
    expiry_date: Optional[date] = None
    payment_terms: Optional[str] = None
    description: Optional[str] = None


class POResponse(BaseModel):
    id: str
    po_number: str
    vendor_id: str
    status: str
    currency: str
    total_amount: float
    utilized_amount: float
    remaining_amount: float
    issue_date: date
    expiry_date: Optional[date] = None
    payment_terms: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    line_items: List[POLineItemResponse] = []

    class Config:
        from_attributes = True
