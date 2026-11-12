from __future__ import annotations
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.invoice import Invoice
from ..models.vendor import Vendor
from ..models.purchase_order import PurchaseOrder
from ..models.decision import Decision, ValidationResult, AuditLog
from ..services.matching import MatchResult
from ..services.validation import ValidationEngine
from ..services.decision import DecisionEngine
from ..services.extraction import ExtractionResult, ExtractedLineItem
from ..schemas.invoice import InvoiceResponse
from ..schemas.decision import DecisionResponse

router = APIRouter()
validator = ValidationEngine()
decision_engine = DecisionEngine()


class ReviewRevalidatePayload(BaseModel):
    field_corrections: Optional[Dict[str, Any]] = None
    new_vendor_id: Optional[str] = None
    new_po_id: Optional[str] = None
    reviewer_name: Optional[str] = "AP Reviewer"


class ReviewSubmissionPayload(BaseModel):
    decision: str  # "APPROVE" | "APPROVED" | "REJECT" | "REJECTED"
    reviewer_name: str
    reviewer_notes: Optional[str] = None
    override_reason: Optional[str] = None
    field_corrections: Optional[Dict[str, Any]] = None
    new_vendor_id: Optional[str] = None
    new_po_id: Optional[str] = None
    rerun_validation: bool = False


def _apply_invoice_edits(invoice: Invoice, field_corrections: Optional[Dict[str, Any]], new_vendor_id: Optional[str], new_po_id: Optional[str], db: Session):
    if field_corrections:
        for k, v in field_corrections.items():
            if hasattr(invoice, k):
                if v is None or v == "":
                    if k in ["grand_total", "subtotal", "tax_amount", "discount_amount", "shipping_amount"]:
                        setattr(invoice, k, None)
                    elif k == "invoice_number":
                        setattr(invoice, k, None)
                    continue
                if k in ["grand_total", "subtotal", "tax_amount", "discount_amount", "shipping_amount"]:
                    setattr(invoice, k, float(v))
                elif k in ["invoice_date", "due_date"] and isinstance(v, str):
                    try:
                        setattr(invoice, k, datetime.strptime(v.strip()[:10], "%Y-%m-%d").date())
                    except ValueError:
                        pass
                else:
                    setattr(invoice, k, v)

    if new_vendor_id is not None:
        if new_vendor_id == "":
            invoice.vendor_id = None
        else:
            v = db.query(Vendor).filter(Vendor.id == new_vendor_id).first()
            if v:
                invoice.vendor_id = v.id
    if new_po_id is not None:
        if new_po_id == "":
            invoice.po_id = None
        else:
            p = db.query(PurchaseOrder).filter(PurchaseOrder.id == new_po_id).first()
            if p:
                invoice.po_id = p.id


def _execute_revalidation(invoice: Invoice, db: Session):
    vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first() if invoice.vendor_id else None
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == invoice.po_id).first() if invoice.po_id else None

    line_items = [
        ExtractedLineItem(
            line_number=li.line_number,
            description=li.description,
            sku=li.sku,
            quantity=li.quantity,
            unit_price=li.unit_price,
            tax_rate=li.tax_rate,
            tax_amount=li.tax_amount,
            total_price=li.total_price,
            confidence=li.confidence or 1.0,
        )
        for li in (invoice.line_items or [])
    ]

    extraction = ExtractionResult(
        vendor_name=vendor.name if vendor else invoice.vendor_name_extracted,
        vendor_gstin=vendor.gstin if vendor else invoice.gstin_extracted,
        vendor_tax_id=vendor.tax_id if vendor else invoice.tax_id_extracted,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        due_date=invoice.due_date.isoformat() if invoice.due_date else None,
        po_number=po.po_number if po else invoice.po_number_extracted,
        payment_terms=invoice.payment_terms,
        currency=invoice.currency or "USD",
        subtotal=invoice.subtotal,
        tax_amount=invoice.tax_amount,
        discount_amount=invoice.discount_amount,
        shipping_amount=invoice.shipping_amount,
        grand_total=invoice.grand_total,
        line_items=line_items,
        extraction_method=invoice.extraction_method or "PDF",
        overall_confidence=max(invoice.extraction_confidence or 0.0, 0.85 if (invoice.invoice_number and invoice.grand_total and vendor) else 0.0),
    )

    match_result = MatchResult(
        matched_vendor=vendor,
        matched_po=po,
        vendor_confidence=1.0 if vendor else 0.0,
        po_confidence=1.0 if po else 0.0,
        match_method="manual_review",
        is_ambiguous=False if (vendor and po) else True,
    )

    val_results = validator.validate(
        extraction=extraction,
        match_result=match_result,
        db=db,
        is_duplicate=bool(invoice.is_duplicate),
        duplicate_of_id=invoice.duplicate_of_id,
    )
    decision_data = decision_engine.decide(val_results, extraction.overall_confidence)
    return val_results, decision_data


@router.get("/queue", response_model=List[InvoiceResponse])
def get_review_queue(db: Session = Depends(get_db)):
    """Return all invoices in REVIEW status requiring human intervention."""
    return (
        db.query(Invoice)
        .filter(Invoice.status == "REVIEW")
        .order_by(Invoice.created_at.desc())
        .all()
    )


@router.get("/{invoice_id}")
def get_review_detail(invoice_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return comprehensive invoice details for human review."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    decision = db.query(Decision).filter(Decision.invoice_id == invoice_id).first()
    val_results = []
    if decision:
        val_results = (
            db.query(ValidationResult)
            .filter(ValidationResult.decision_id == decision.id)
            .all()
        )

    matched_vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first() if invoice.vendor_id else None
    matched_po = db.query(PurchaseOrder).filter(PurchaseOrder.id == invoice.po_id).first() if invoice.po_id else None

    # Available vendors & POs for re-assignment
    all_vendors = db.query(Vendor).filter(Vendor.approval_status == "APPROVED").all()
    all_pos = db.query(PurchaseOrder).filter(PurchaseOrder.status.in_(["OPEN", "PARTIAL"])).all()

    return {
        "invoice": {
            "id": invoice.id,
            "filename": invoice.filename,
            "original_filename": invoice.original_filename,
            "file_hash": invoice.file_hash,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "vendor_id": invoice.vendor_id,
            "po_id": invoice.po_id,
            "vendor_name_extracted": invoice.vendor_name_extracted,
            "gstin_extracted": invoice.gstin_extracted,
            "tax_id_extracted": invoice.tax_id_extracted,
            "po_number_extracted": invoice.po_number_extracted,
            "currency": invoice.currency,
            "subtotal": invoice.subtotal,
            "tax_amount": invoice.tax_amount,
            "discount_amount": invoice.discount_amount,
            "shipping_amount": invoice.shipping_amount,
            "grand_total": invoice.grand_total,
            "extraction_confidence": invoice.extraction_confidence,
            "extraction_method": invoice.extraction_method,
            "status": invoice.status,
            "payment_terms": invoice.payment_terms,
            "notes": invoice.notes,
            "is_duplicate": invoice.is_duplicate,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        },
        "decision": {
            "id": decision.id if decision else None,
            "decision": decision.decision if decision else None,
            "confidence_score": decision.confidence_score if decision else None,
            "primary_reason": decision.primary_reason if decision else None,
            "explanation": decision.explanation if decision else [],
            "discrepancies": decision.discrepancies if decision else [],
            "validation_summary": decision.validation_summary if decision else {},
            "validation_results": [
                {
                    "rule_name": vr.rule_name,
                    "passed": vr.passed,
                    "severity": vr.severity,
                    "message": vr.message,
                    "details": vr.details,
                }
                for vr in val_results
            ],
        },
        "vendor": {
            "id": matched_vendor.id,
            "name": matched_vendor.name,
            "approval_status": matched_vendor.approval_status,
            "tax_id": matched_vendor.tax_id,
            "gstin": matched_vendor.gstin,
        } if matched_vendor else None,
        "purchase_order": {
            "id": matched_po.id,
            "po_number": matched_po.po_number,
            "status": matched_po.status,
            "total_amount": matched_po.total_amount,
            "utilized_amount": matched_po.utilized_amount,
            "remaining_amount": matched_po.remaining_amount,
            "currency": matched_po.currency,
        } if matched_po else None,
        "available_vendors": [
            {"id": v.id, "name": v.name, "approval_status": v.approval_status}
            for v in all_vendors
        ],
        "available_pos": [
            {
                "id": p.id,
                "po_number": p.po_number,
                "vendor_id": p.vendor_id,
                "total_amount": p.total_amount,
                "remaining_amount": p.remaining_amount,
                "currency": p.currency,
            }
            for p in all_pos
        ],
    }


@router.post("/{invoice_id}/revalidate")
def revalidate_invoice(
    invoice_id: str,
    payload: ReviewRevalidatePayload,
    db: Session = Depends(get_db),
):
    """
    Applies proposed field corrections and vendor/PO match updates,
    re-runs all 11 validation rules, persists updated ValidationResult records,
    logs the modification in AuditLog, and returns updated validation & decision summary.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    before_state = {
        "vendor_id": invoice.vendor_id,
        "po_id": invoice.po_id,
        "invoice_number": invoice.invoice_number,
        "subtotal": invoice.subtotal,
        "tax_amount": invoice.tax_amount,
        "grand_total": invoice.grand_total,
    }

    _apply_invoice_edits(invoice, payload.field_corrections, payload.new_vendor_id, payload.new_po_id, db)
    val_results, decision_data = _execute_revalidation(invoice, db)

    decision = db.query(Decision).filter(Decision.invoice_id == invoice.id).first()
    if not decision:
        decision = Decision(
            id=str(uuid.uuid4()),
            invoice_id=invoice.id,
            decision=decision_data["decision"],
            confidence_score=decision_data["confidence_score"],
            primary_reason=decision_data["primary_reason"],
            explanation=decision_data["explanation"],
            discrepancies=decision_data["discrepancies"],
            validation_summary={r.rule_name: r.passed for r in val_results},
            decided_by="Re-validation Engine",
        )
        db.add(decision)
        db.flush()
    else:
        decision.confidence_score = decision_data["confidence_score"]
        decision.primary_reason = decision_data["primary_reason"]
        decision.explanation = decision_data["explanation"]
        decision.discrepancies = decision_data["discrepancies"]
        decision.validation_summary = {r.rule_name: r.passed for r in val_results}
        db.query(ValidationResult).filter(ValidationResult.decision_id == decision.id).delete()

    for r in val_results:
        db.add(
            ValidationResult(
                id=str(uuid.uuid4()),
                decision_id=decision.id,
                rule_name=r.rule_name,
                passed=r.passed,
                severity=r.severity,
                message=r.message,
                details=r.details,
            )
        )

    after_state = {
        "vendor_id": invoice.vendor_id,
        "po_id": invoice.po_id,
        "invoice_number": invoice.invoice_number,
        "subtotal": invoice.subtotal,
        "tax_amount": invoice.tax_amount,
        "grand_total": invoice.grand_total,
        "recommended_decision": decision_data["decision"],
    }
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            invoice_id=invoice.id,
            action="REVIEW_REVALIDATED",
            actor=payload.reviewer_name or "AP Reviewer",
            timestamp=datetime.utcnow(),
            before_state=before_state,
            after_state=after_state,
            notes="Reviewer edited fields/matches and re-ran validation rules",
        )
    )
    db.commit()

    return {
        "recommended_decision": decision_data["decision"],
        "confidence_score": decision_data["confidence_score"],
        "primary_reason": decision_data["primary_reason"],
        "explanation": decision_data["explanation"],
        "discrepancies": decision_data["discrepancies"],
        "validation_results": [
            {
                "rule_name": r.rule_name,
                "passed": r.passed,
                "severity": r.severity,
                "message": r.message,
                "details": r.details,
            }
            for r in val_results
        ],
    }


@router.post("/{invoice_id}/submit")
def submit_review_decision(
    invoice_id: str,
    payload: ReviewSubmissionPayload,
    db: Session = Depends(get_db),
):
    """
    Submits human reviewer decision:
    - Allows field corrections & vendor/PO changes
    - Optionally re-runs all validation rules
    - Re-evaluates hard policy rules: MANUAL APPROVAL NEVER BYPASSES HARD POLICY VIOLATIONS
    - Records audit log
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    _raw = payload.decision.upper()
    _map = {"APPROVE": "APPROVED", "APPROVED": "APPROVED", "REJECT": "REJECTED", "REJECTED": "REJECTED"}
    if _raw not in _map:
        raise HTTPException(status_code=400, detail="Decision must be APPROVE or REJECT")
    decision_choice = _map[_raw]

    if not payload.reviewer_name.strip():
        raise HTTPException(status_code=400, detail="Reviewer name is required")

    before_state = {
        "status": invoice.status,
        "vendor_id": invoice.vendor_id,
        "po_id": invoice.po_id,
        "invoice_number": invoice.invoice_number,
        "grand_total": invoice.grand_total,
    }

    # 1. Apply field corrections & Vendor / PO matches if provided
    _apply_invoice_edits(invoice, payload.field_corrections, payload.new_vendor_id, payload.new_po_id, db)

    # 2. Check for hard policy violations:
    # Rule check: Even with manual override, duplicate / rejected vendor / closed PO / PO budget overrun CANNOT be approved!
    current_vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first() if invoice.vendor_id else None
    current_po = db.query(PurchaseOrder).filter(PurchaseOrder.id == invoice.po_id).first() if invoice.po_id else None

    if decision_choice == "APPROVED":
        if invoice.is_duplicate:
            raise HTTPException(
                status_code=400,
                detail="Manual approval blocked: Confirmed duplicate invoice cannot be approved.",
            )
        if current_vendor and current_vendor.approval_status in ["REJECTED", "SUSPENDED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Manual approval blocked: Vendor '{current_vendor.name}' has status '{current_vendor.approval_status}'.",
            )
        if current_po and current_po.status in ["CLOSED", "CANCELLED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Manual approval blocked: PO '{current_po.po_number}' is {current_po.status}.",
            )
        if current_po and invoice.grand_total and (current_po.utilized_amount + invoice.grand_total > current_po.total_amount):
            remaining = current_po.total_amount - current_po.utilized_amount
            raise HTTPException(
                status_code=400,
                detail=f"Manual approval blocked: Invoice total ${invoice.grand_total:.2f} exceeds remaining PO budget ${remaining:.2f}.",
            )

    # 3. Re-run validation rules if requested
    val_results = None
    decision_data = None
    if payload.rerun_validation:
        val_results, decision_data = _execute_revalidation(invoice, db)

    # 4. If approving with a PO, update cumulative PO utilization
    if decision_choice == "APPROVED" and current_po and invoice.grand_total:
        current_po.utilized_amount += invoice.grand_total
        current_po.remaining_amount = current_po.total_amount - current_po.utilized_amount
        if current_po.remaining_amount <= 0:
            current_po.status = "CLOSED"
        else:
            current_po.status = "PARTIAL"

    # 5. Update invoice status
    invoice.status = decision_choice
    invoice.processed_at = datetime.utcnow()

    # 6. Update or create Decision record
    decision = db.query(Decision).filter(Decision.invoice_id == invoice.id).first()
    if not decision:
        decision = Decision(
            id=str(uuid.uuid4()),
            invoice_id=invoice.id,
            decision=decision_choice,
            confidence_score=1.0,
            primary_reason=payload.reviewer_notes or f"Manual review decision by {payload.reviewer_name}",
            explanation=decision_data["explanation"] if decision_data else [
                f"Manual decision by {payload.reviewer_name}: {payload.override_reason or 'No override reason provided'}"
            ],
            discrepancies=decision_data["discrepancies"] if decision_data else [],
            validation_summary={r.rule_name: r.passed for r in val_results} if val_results else {"manual_override": True},
            decided_by=payload.reviewer_name,
            is_manual_override=True,
            override_reason=payload.override_reason,
            reviewer_notes=payload.reviewer_notes,
            reviewer_name=payload.reviewer_name,
            reviewed_at=datetime.utcnow(),
        )
        db.add(decision)
        db.flush()
    else:
        decision.decision = decision_choice
        decision.is_manual_override = True
        decision.override_reason = payload.override_reason
        decision.reviewer_notes = payload.reviewer_notes
        decision.reviewer_name = payload.reviewer_name
        decision.reviewed_at = datetime.utcnow()
        decision.primary_reason = f"Manual decision by {payload.reviewer_name}: {payload.override_reason or decision_choice}"
        if decision_data and val_results is not None:
            decision.explanation = decision_data["explanation"]
            decision.discrepancies = decision_data["discrepancies"]
            decision.validation_summary = {r.rule_name: r.passed for r in val_results}
            db.query(ValidationResult).filter(ValidationResult.decision_id == decision.id).delete()

    if val_results is not None:
        for r in val_results:
            db.add(
                ValidationResult(
                    id=str(uuid.uuid4()),
                    decision_id=decision.id,
                    rule_name=r.rule_name,
                    passed=r.passed,
                    severity=r.severity,
                    message=r.message,
                    details=r.details,
                )
            )

    # 7. Record AuditLog
    after_state = {
        "status": invoice.status,
        "vendor_id": invoice.vendor_id,
        "po_id": invoice.po_id,
        "invoice_number": invoice.invoice_number,
        "grand_total": invoice.grand_total,
        "decision": decision_choice,
        "reviewer": payload.reviewer_name,
    }

    audit = AuditLog(
        id=str(uuid.uuid4()),
        invoice_id=invoice.id,
        action=f"REVIEW_{decision_choice}",
        actor=payload.reviewer_name,
        timestamp=datetime.utcnow(),
        before_state=before_state,
        after_state=after_state,
        notes=payload.reviewer_notes,
    )
    db.add(audit)

    db.commit()
    db.refresh(invoice)

    return {
        "status": "success",
        "invoice_id": invoice.id,
        "decision": decision_choice,
        "reviewer": payload.reviewer_name,
    }
