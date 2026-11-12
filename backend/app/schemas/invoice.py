from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class LineItemExtracted(BaseModel):
    line_number: int
    description: Optional[str] = None
    sku: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total_price: Optional[float] = None
    confidence: float = 1.0


class ExtractionResult(BaseModel):
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    shipping_amount: Optional[float] = None
    grand_total: Optional[float] = None
    line_items: List[LineItemExtracted] = []
    extraction_method: str = "PDF"
    overall_confidence: float = 0.0
    field_confidence: dict = {}


class InvoiceLineItemResponse(BaseModel):
    id: str
    invoice_id: str
    line_number: int
    description: Optional[str] = None
    sku: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total_price: Optional[float] = None
    confidence: float

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_path: str
    file_hash: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    vendor_id: Optional[str] = None
    po_id: Optional[str] = None
    vendor_name_extracted: Optional[str] = None
    gstin_extracted: Optional[str] = None
    tax_id_extracted: Optional[str] = None
    po_number_extracted: Optional[str] = None
    currency: str
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    shipping_amount: Optional[float] = None
    grand_total: Optional[float] = None
    payment_terms: Optional[str] = None
    extraction_confidence: float
    extraction_method: str
    status: str
    notes: Optional[str] = None
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    line_items: List[InvoiceLineItemResponse] = []

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int


class ManualInvoiceCreate(BaseModel):
    original_filename: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    vendor_id: Optional[str] = None
    po_id: Optional[str] = None
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    shipping_amount: Optional[float] = None
    grand_total: Optional[float] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
