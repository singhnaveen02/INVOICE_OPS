from __future__ import annotations
import csv
import io
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models.vendor import Vendor
from ..models.purchase_order import PurchaseOrder
from ..schemas.vendor import VendorCreate, VendorUpdate, VendorResponse

router = APIRouter()


@router.get("/", response_model=List[VendorResponse])
def list_vendors(
    status: Optional[str] = Query(None, description="Filter by approval status"),
    search: Optional[str] = Query(None, description="Search by name, GSTIN, or tax_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Vendor)
    if status:
        query = query.filter(Vendor.approval_status == status.upper())
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Vendor.name.ilike(pattern),
                Vendor.gstin.ilike(pattern),
                Vendor.tax_id.ilike(pattern),
            )
        )
    return query.order_by(Vendor.name.asc()).offset(skip).limit(limit).all()


@router.post("/", response_model=VendorResponse, status_code=201)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    existing = db.query(Vendor).filter(Vendor.name.ilike(payload.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Vendor with name '{payload.name}' already exists")

    vendor = Vendor(
        id=str(uuid.uuid4()),
        name=payload.name,
        gstin=payload.gstin,
        tax_id=payload.tax_id,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        country=payload.country,
        approval_status=payload.approval_status.upper(),
        notes=payload.notes,
    )
    if vendor.approval_status == "APPROVED":
        vendor.approved_by = "admin"
        vendor.approved_at = datetime.utcnow()

    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(vendor_id: str, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.put("/{vendor_id}", response_model=VendorResponse)
def update_vendor(vendor_id: str, payload: VendorUpdate, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        if field_name == "approval_status" and value:
            val_upper = value.upper()
            setattr(vendor, field_name, val_upper)
            if val_upper == "APPROVED" and not vendor.approved_at:
                vendor.approved_at = datetime.utcnow()
                vendor.approved_by = payload.approved_by or "admin"
        else:
            setattr(vendor, field_name, value)

    vendor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(vendor)
    return vendor


@router.post("/import-csv")
async def import_vendors_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    text = content.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    updated = 0
    errors = []

    for row in reader:
        name = row.get("name", "").strip()
        if not name:
            continue
        try:
            status = row.get("approval_status", "PENDING").strip().upper()
            existing = db.query(Vendor).filter(Vendor.name.ilike(name)).first()
            if existing:
                existing.gstin = row.get("gstin") or existing.gstin
                existing.tax_id = row.get("tax_id") or existing.tax_id
                existing.email = row.get("email") or existing.email
                existing.phone = row.get("phone") or existing.phone
                existing.address = row.get("address") or existing.address
                existing.approval_status = status
                updated += 1
            else:
                vendor = Vendor(
                    id=row.get("id") or str(uuid.uuid4()),
                    name=name,
                    gstin=row.get("gstin") or None,
                    tax_id=row.get("tax_id") or None,
                    email=row.get("email") or None,
                    phone=row.get("phone") or None,
                    address=row.get("address") or None,
                    country=row.get("country", "US"),
                    approval_status=status,
                    notes=row.get("notes") or None,
                )
                if status == "APPROVED":
                    vendor.approved_by = "csv_import"
                    vendor.approved_at = datetime.utcnow()
                db.add(vendor)
                imported += 1
        except Exception as e:
            errors.append(f"Row {name}: {str(e)}")

    db.commit()
    return {
        "status": "success",
        "imported": imported,
        "updated": updated,
        "errors": errors,
    }
