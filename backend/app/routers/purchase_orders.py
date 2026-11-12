from __future__ import annotations
import csv
import io
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..models.purchase_order import PurchaseOrder, POLineItem
from ..models.vendor import Vendor
from ..schemas.purchase_order import POCreate, POUpdate, POResponse, POLineItemResponse

router = APIRouter()


@router.get("/", response_model=List[POResponse])
def list_pos(
    status: Optional[str] = Query(None, description="Filter by PO status"),
    vendor_id: Optional[str] = Query(None, description="Filter by vendor ID"),
    search: Optional[str] = Query(None, description="Search by PO number or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseOrder)
    if status:
        query = query.filter(PurchaseOrder.status == status.upper())
    if vendor_id:
        query = query.filter(PurchaseOrder.vendor_id == vendor_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                PurchaseOrder.po_number.ilike(pattern),
                PurchaseOrder.description.ilike(pattern),
            )
        )
    return query.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=POResponse, status_code=201)
def create_po(payload: POCreate, db: Session = Depends(get_db)):
    existing = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == payload.po_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"PO with number '{payload.po_number}' already exists")

    vendor = db.query(Vendor).filter(Vendor.id == payload.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=400, detail="Associated vendor not found")

    po = PurchaseOrder(
        id=str(uuid.uuid4()),
        po_number=payload.po_number,
        vendor_id=payload.vendor_id,
        status=payload.status.upper(),
        currency=payload.currency.upper(),
        total_amount=payload.total_amount,
        utilized_amount=payload.utilized_amount,
        remaining_amount=payload.total_amount - payload.utilized_amount,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        payment_terms=payload.payment_terms,
        description=payload.description,
    )
    db.add(po)
    db.flush()

    for item in payload.line_items:
        line_item = POLineItem(
            id=str(uuid.uuid4()),
            po_id=po.id,
            line_number=item.line_number,
            description=item.description,
            sku=item.sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            unit_of_measure=item.unit_of_measure,
        )
        db.add(line_item)

    db.commit()
    db.refresh(po)
    return po


@router.get("/{po_id}", response_model=POResponse)
def get_po(po_id: str, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.put("/{po_id}", response_model=POResponse)
def update_po(po_id: str, payload: POUpdate, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        if field_name == "status" and value:
            setattr(po, field_name, value.upper())
        else:
            setattr(po, field_name, value)

    if po.utilized_amount is not None:
        po.remaining_amount = po.total_amount - po.utilized_amount

    po.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(po)
    return po


@router.post("/import-csv")
async def import_pos_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    text = content.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    updated = 0
    errors = []

    for row in reader:
        po_number = row.get("po_number", "").strip()
        if not po_number:
            continue
        try:
            vendor_id = row.get("vendor_id", "").strip()
            if not vendor_id:
                vendor_name = row.get("vendor_name", "").strip()
                v = db.query(Vendor).filter(Vendor.name.ilike(vendor_name)).first() if vendor_name else None
                vendor_id = v.id if v else None

            if not vendor_id:
                first_v = db.query(Vendor).first()
                vendor_id = first_v.id if first_v else None

            total = float(row.get("total_amount", 0.0))
            utilized = float(row.get("utilized_amount", 0.0))
            status = row.get("status", "OPEN").strip().upper()

            existing = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).first()
            if existing:
                existing.total_amount = total
                existing.utilized_amount = utilized
                existing.remaining_amount = total - utilized
                existing.status = status
                updated += 1
            else:
                po = PurchaseOrder(
                    id=row.get("id") or str(uuid.uuid4()),
                    po_number=po_number,
                    vendor_id=vendor_id,
                    status=status,
                    currency=row.get("currency", "USD").upper(),
                    total_amount=total,
                    utilized_amount=utilized,
                    remaining_amount=total - utilized,
                    issue_date=datetime.strptime(row.get("issue_date", "2024-01-01")[:10], "%Y-%m-%d").date() if row.get("issue_date") else date.today(),
                    expiry_date=datetime.strptime(row.get("expiry_date", "2024-12-31")[:10], "%Y-%m-%d").date() if row.get("expiry_date") else None,
                    payment_terms=row.get("payment_terms", "Net 30"),
                    description=row.get("description", ""),
                )
                db.add(po)
                imported += 1
        except Exception as e:
            errors.append(f"Row {po_number}: {str(e)}")

    db.commit()
    return {"status": "success", "imported": imported, "updated": updated, "errors": errors}
