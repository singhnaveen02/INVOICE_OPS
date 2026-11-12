from __future__ import annotations
import csv
import io
import os
import time
import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    BackgroundTasks,
    Response,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from ..database import get_db, SessionLocal
from ..config import settings
from ..models.invoice import Invoice, InvoiceLineItem, ProcessingStage
from ..models.vendor import Vendor
from ..models.purchase_order import PurchaseOrder
from ..models.decision import Decision, ValidationResult, AuditLog
from ..models.duplicate import DuplicateFingerprint
from ..schemas.invoice import (
    InvoiceResponse,
    InvoiceListResponse,
    ManualInvoiceCreate,
    InvoiceLineItemResponse,
)
from ..schemas.decision import DecisionResponse, ValidationResultResponse
from ..services.extraction import InvoiceExtractor
from ..services.matching import POMatchingEngine
from ..services.validation import ValidationEngine
from ..services.decision import DecisionEngine
from ..services.duplicate import DuplicateDetector
from ..utils.file_utils import validate_and_save_file

router = APIRouter()

extractor = InvoiceExtractor()
matcher = POMatchingEngine()
validator = ValidationEngine()
decision_engine = DecisionEngine()
dup_detector = DuplicateDetector()


def run_processing_pipeline(invoice_id: str, file_path: str, file_bytes: bytes):
    """
    Executes the full 10-stage processing pipeline on the invoice.
    Updates ProcessingStage records synchronously in DB as each stage executes.
    """
    db: Session = SessionLocal()
    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return

        def start_stage(stage_name: str, started_at: datetime) -> ProcessingStage:
            stage = ProcessingStage(
                id=str(uuid.uuid4()),
                invoice_id=invoice.id,
                stage_name=stage_name,
                status="RUNNING",
                started_at=started_at,
            )
            db.add(stage)
            db.commit()
            return stage

        def finish_stage(
            stage: ProcessingStage,
            status: str,
            started_at: datetime,
            completed_at: datetime,
            findings: Optional[dict] = None,
            error: Optional[str] = None,
        ):
            stage.status = status
            stage.completed_at = completed_at
            stage.duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            stage.findings = findings
            stage.error_message = error
            db.commit()
            return stage

        # Stage 1: Document Received
        t0 = datetime.utcnow()
        s1 = start_stage("document_received", t0)
        finish_stage(
            s1,
            "COMPLETED",
            t0,
            datetime.utcnow(),
            {"file_name": invoice.original_filename, "file_size_bytes": len(file_bytes)},
        )

        # Stage 2: PDF Parsing / OCR
        t1 = datetime.utcnow()
        s2 = start_stage("pdf_parsing", t1)
        try:
            extraction = extractor.extract(file_path, file_bytes)
            finish_stage(
                s2,
                "COMPLETED",
                t1,
                datetime.utcnow(),
                {
                    "method": extraction.extraction_method,
                    "raw_text_length": len(extraction.raw_text or ""),
                },
            )
        except Exception as e:
            finish_stage(s2, "FAILED", t1, datetime.utcnow(), error=str(e))
            invoice.status = "REJECTED"
            db.commit()
            return

        # Stage 3: Field Extraction
        t2 = datetime.utcnow()
        s3 = start_stage("field_extraction", t2)
        invoice.invoice_number = extraction.invoice_number
        invoice.vendor_name_extracted = extraction.vendor_name
        invoice.gstin_extracted = extraction.vendor_gstin
        invoice.tax_id_extracted = extraction.vendor_tax_id
        invoice.po_number_extracted = extraction.po_number
        invoice.currency = extraction.currency or "USD"
        invoice.subtotal = extraction.subtotal
        invoice.tax_amount = extraction.tax_amount
        invoice.discount_amount = extraction.discount_amount
        invoice.shipping_amount = extraction.shipping_amount
        invoice.grand_total = extraction.grand_total
        invoice.extraction_confidence = extraction.overall_confidence
        invoice.extraction_method = extraction.extraction_method
        invoice.payment_terms = extraction.payment_terms

        # Parse invoice date
        if extraction.invoice_date:
            for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y"]:
                try:
                    invoice.invoice_date = datetime.strptime(extraction.invoice_date.strip(), fmt).date()
                    break
                except Exception:
                    pass

        # Parse line items
        for item in extraction.line_items:
            li = InvoiceLineItem(
                id=str(uuid.uuid4()),
                invoice_id=invoice.id,
                line_number=item.line_number,
                description=item.description,
                sku=item.sku,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
                tax_amount=item.tax_amount,
                total_price=item.total_price,
                confidence=item.confidence,
            )
            db.add(li)
        db.commit()

        finish_stage(
            s3,
            "COMPLETED",
            t2,
            datetime.utcnow(),
            {
                "invoice_number": invoice.invoice_number,
                "grand_total": invoice.grand_total,
                "confidence": invoice.extraction_confidence,
                "line_items_count": len(extraction.line_items),
            },
        )

        # Stage 4: Vendor Identification
        t3 = datetime.utcnow()
        s4 = start_stage("vendor_identification", t3)
        match_result = matcher.match(db, extraction)
        if match_result.matched_vendor:
            invoice.vendor_id = match_result.matched_vendor.id

        finish_stage(
            s4,
            "COMPLETED",
            t3,
            datetime.utcnow(),
            {
                "vendor_matched": match_result.matched_vendor.name if match_result.matched_vendor else None,
                "confidence": match_result.vendor_confidence,
                "approval_status": match_result.matched_vendor.approval_status if match_result.matched_vendor else None,
            },
        )

        # Stage 5: PO Matching
        t4 = datetime.utcnow()
        s5 = start_stage("po_matching", t4)
        if match_result.matched_po:
            invoice.po_id = match_result.matched_po.id

        finish_stage(
            s5,
            "COMPLETED",
            t4,
            datetime.utcnow(),
            {
                "po_matched": match_result.matched_po.po_number if match_result.matched_po else None,
                "confidence": match_result.po_confidence,
                "match_method": match_result.match_method,
                "is_ambiguous": match_result.is_ambiguous,
            },
        )

        # Stage 6: Duplicate Detection
        t5 = datetime.utcnow()
        s6 = start_stage("duplicate_detection", t5)
        fingerprints = dup_detector.compute_fingerprints(
            file_bytes=file_bytes,
            vendor_name=extraction.vendor_name,
            invoice_number=extraction.invoice_number,
            grand_total=extraction.grand_total,
        )
        is_dup, dup_of_id, dup_reason = dup_detector.check_duplicate(
            db, fingerprints, exclude_invoice_id=invoice.id
        )
        if is_dup:
            invoice.is_duplicate = True
            invoice.duplicate_of_id = dup_of_id

        # Save fingerprint
        dup_detector.save_fingerprint(db, invoice.id, fingerprints)

        finish_stage(
            s6,
            "COMPLETED",
            t5,
            datetime.utcnow(),
            {"is_duplicate": is_dup, "duplicate_of": dup_of_id, "reason": dup_reason},
        )

        # Stage 7: Financial Reconciliation
        t6 = datetime.utcnow()
        s7 = start_stage("financial_reconciliation", t6)
        reconciliation_passed = True
        recon_findings = {}
        if invoice.grand_total is not None and invoice.subtotal is not None:
            calc_total = (invoice.subtotal or 0.0) + (invoice.tax_amount or 0.0) - (invoice.discount_amount or 0.0) + (invoice.shipping_amount or 0.0)
            diff = abs(calc_total - invoice.grand_total)
            reconciliation_passed = diff < 1.0
            recon_findings = {"calculated": calc_total, "stated": invoice.grand_total, "diff": round(diff, 2)}

        finish_stage(
            s7,
            "COMPLETED" if reconciliation_passed else "WARNING",
            t6,
            datetime.utcnow(),
            recon_findings,
        )

        # Stage 8: Business Validation
        t7 = datetime.utcnow()
        s8 = start_stage("business_validation", t7)
        validation_results = validator.validate(
            extraction=extraction,
            match_result=match_result,
            db=db,
            is_duplicate=is_dup,
            duplicate_of_id=dup_of_id,
        )
        passed_rules = sum(1 for r in validation_results if r.passed)
        finish_stage(
            s8,
            "COMPLETED",
            t7,
            datetime.utcnow(),
            {
                "passed_rules": passed_rules,
                "total_rules": len(validation_results),
            },
        )

        # Stage 9: Decision Generation
        t8 = datetime.utcnow()
        s9 = start_stage("decision_generation", t8)
        decision_data = decision_engine.decide(validation_results, invoice.extraction_confidence)
        decision_record = Decision(
            id=str(uuid.uuid4()),
            invoice_id=invoice.id,
            decision=decision_data["decision"],
            confidence_score=decision_data["confidence_score"],
            primary_reason=decision_data["primary_reason"],
            explanation=decision_data["explanation"],
            discrepancies=decision_data["discrepancies"],
            validation_summary={r.rule_name: r.passed for r in validation_results},
            decided_at=datetime.utcnow(),
            decided_by="System (Rule Engine)",
        )
        db.add(decision_record)
        db.flush()

        # Save individual ValidationResult records
        for r in validation_results:
            vr = ValidationResult(
                id=str(uuid.uuid4()),
                decision_id=decision_record.id,
                rule_name=r.rule_name,
                passed=r.passed,
                severity=r.severity,
                message=r.message,
                details=r.details,
            )
            db.add(vr)

        finish_stage(
            s9,
            "COMPLETED",
            t8,
            datetime.utcnow(),
            {
                "decision": decision_data["decision"],
                "confidence": decision_data["confidence_score"],
                "primary_reason": decision_data["primary_reason"],
            },
        )

        # Stage 10: Database Persistence
        t9 = datetime.utcnow()
        s10 = start_stage("database_persistence", t9)
        invoice.status = decision_data["decision"]
        invoice.processed_at = datetime.utcnow()

        # If approved with PO, update PO utilization
        if invoice.status == "APPROVED" and match_result.matched_po and invoice.grand_total:
            po = match_result.matched_po
            po.utilized_amount += invoice.grand_total
            po.remaining_amount = po.total_amount - po.utilized_amount
            if po.remaining_amount <= 0:
                po.status = "CLOSED"
            else:
                po.status = "PARTIAL"

        # Record AuditLog
        audit = AuditLog(
            id=str(uuid.uuid4()),
            invoice_id=invoice.id,
            action=f"PROCESSED_{invoice.status}",
            actor="InvoiceOps Pipeline",
            timestamp=datetime.utcnow(),
            after_state={"status": invoice.status, "decision": decision_data["decision"]},
            notes=f"Automated pipeline completed. Decision: {invoice.status}",
        )
        db.add(audit)
        db.commit()

        finish_stage(
            s10,
            "COMPLETED",
            t9,
            datetime.utcnow(),
            {"invoice_id": invoice.id, "final_status": invoice.status},
        )

    except Exception as e:
        db.rollback()
        try:
            inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if inv:
                inv.status = "REVIEW"
                inv.notes = f"Processing error: {str(e)}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/upload")
async def upload_invoices(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    live: bool = Query(False, description="Run pipeline asynchronously and stream stages via SSE"),
    db: Session = Depends(get_db),
):
    """
    Accepts single or multiple PDF uploads.
    Validates file, creates initial record, and executes the 10-stage processing pipeline.
    When live=true, queues the pipeline in the background so the UI can stream SSE events.
    """
    created_invoices = []
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        file_info = await validate_and_save_file(file, upload_dir)

        invoice_id = str(uuid.uuid4())
        invoice = Invoice(
            id=invoice_id,
            filename=file_info["filename"],
            original_filename=file_info["original_filename"],
            file_path=file_info["file_path"],
            file_hash=file_info["file_hash"],
            status="PROCESSING",
            extraction_method="PDF",
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        if live:
            background_tasks.add_task(
                run_processing_pipeline,
                invoice_id=invoice.id,
                file_path=file_info["file_path"],
                file_bytes=file_info["file_bytes"],
            )
        else:
            run_processing_pipeline(
                invoice_id=invoice.id,
                file_path=file_info["file_path"],
                file_bytes=file_info["file_bytes"],
            )

        db.refresh(invoice)
        created_invoices.append({
            "id": invoice.id,
            "filename": invoice.filename,
            "original_filename": invoice.original_filename,
            "status": invoice.status,
            "invoice_number": invoice.invoice_number,
            "grand_total": invoice.grand_total,
            "confidence": invoice.extraction_confidence,
        })

    return {"uploaded": len(created_invoices), "invoices": created_invoices}


@router.post("/manual", response_model=InvoiceResponse, status_code=201)
def create_manual_invoice(payload: ManualInvoiceCreate, db: Session = Depends(get_db)):
    """Creates a manual invoice entry and runs validation against matched PO."""
    invoice_id = str(uuid.uuid4())
    dummy_hash = f"manual_{uuid.uuid4().hex}"

    invoice = Invoice(
        id=invoice_id,
        filename=f"manual_{payload.invoice_number or invoice_id}.pdf",
        original_filename=payload.original_filename or f"Manual Entry {payload.invoice_number}",
        file_path="",
        file_hash=dummy_hash,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        vendor_id=payload.vendor_id,
        po_id=payload.po_id,
        currency=payload.currency,
        subtotal=payload.subtotal,
        tax_amount=payload.tax_amount,
        discount_amount=payload.discount_amount,
        shipping_amount=payload.shipping_amount,
        grand_total=payload.grand_total,
        payment_terms=payload.payment_terms,
        extraction_confidence=1.0,
        extraction_method="MANUAL",
        status="PENDING",
        notes=payload.notes,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # Run matching and validation
    vendor = db.query(Vendor).filter(Vendor.id == payload.vendor_id).first() if payload.vendor_id else None
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == payload.po_id).first() if payload.po_id else None

    from ..services.matching import MatchResult
    match_result = MatchResult(
        matched_vendor=vendor,
        matched_po=po,
        vendor_confidence=1.0 if vendor else 0.0,
        po_confidence=1.0 if po else 0.0,
        match_method="manual",
    )

    from ..services.extraction import ExtractionResult
    ext = ExtractionResult(
        vendor_name=vendor.name if vendor else None,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date.isoformat() if payload.invoice_date else None,
        po_number=po.po_number if po else None,
        currency=payload.currency,
        subtotal=payload.subtotal,
        tax_amount=payload.tax_amount,
        grand_total=payload.grand_total,
        overall_confidence=1.0,
        extraction_method="MANUAL",
    )

    val_results = validator.validate(ext, match_result, db, is_duplicate=False)
    decision_data = decision_engine.decide(val_results, 1.0)

    decision_record = Decision(
        id=str(uuid.uuid4()),
        invoice_id=invoice.id,
        decision=decision_data["decision"],
        confidence_score=decision_data["confidence_score"],
        primary_reason=decision_data["primary_reason"],
        explanation=decision_data["explanation"],
        discrepancies=decision_data["discrepancies"],
        validation_summary={r.rule_name: r.passed for r in val_results},
        decided_by="Manual Entry Form",
    )
    db.add(decision_record)

    invoice.status = decision_data["decision"]
    invoice.processed_at = datetime.utcnow()

    # If approved with PO, update utilization
    if invoice.status == "APPROVED" and po and invoice.grand_total:
        po.utilized_amount += invoice.grand_total
        po.remaining_amount = po.total_amount - po.utilized_amount
        if po.remaining_amount <= 0:
            po.status = "CLOSED"
        else:
            po.status = "PARTIAL"

    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/", response_model=InvoiceListResponse)
def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status (APPROVED/REVIEW/REJECTED/PENDING/PROCESSING)"),
    vendor_id: Optional[str] = Query(None),
    po_number: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Invoice)
    if status:
        # Normalize: APPROVE -> APPROVED, REJECT -> REJECTED
        _s = status.upper()
        _norm = {"APPROVE": "APPROVED", "REJECT": "REJECTED"}.get(_s, _s)
        query = query.filter(Invoice.status == _norm)
    if vendor_id:
        query = query.filter(Invoice.vendor_id == vendor_id)
    if po_number:
        from sqlalchemy import select
        po_subq = select(PurchaseOrder.id).where(PurchaseOrder.po_number.ilike(f"%{po_number}%"))
        query = query.filter(
            or_(
                Invoice.po_number_extracted.ilike(f"%{po_number}%"),
                Invoice.po_id.in_(po_subq),
            )
        )
    if date_from:
        query = query.filter(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.filter(Invoice.invoice_date <= date_to)
    if min_amount is not None:
        query = query.filter(Invoice.grand_total >= min_amount)
    if max_amount is not None:
        query = query.filter(Invoice.grand_total <= max_amount)
    if search:
        pat = f"%{search}%"
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(pat),
                Invoice.original_filename.ilike(pat),
                Invoice.vendor_name_extracted.ilike(pat),
                Invoice.po_number_extracted.ilike(pat),
            )
        )

    total = query.count()
    items = (
        query.order_by(desc(Invoice.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return InvoiceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
def export_invoices_csv(
    status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Exports filtered invoices as a CSV file."""
    query = db.query(Invoice)
    if status:
        query = query.filter(Invoice.status == status.upper())
    if vendor_id:
        query = query.filter(Invoice.vendor_id == vendor_id)

    invoices = query.order_by(desc(Invoice.created_at)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Invoice ID",
        "Invoice Number",
        "Vendor",
        "PO Number",
        "Invoice Date",
        "Due Date",
        "Currency",
        "Subtotal",
        "Tax Amount",
        "Grand Total",
        "Status",
        "Extraction Method",
        "Confidence",
        "Is Duplicate",
        "Created At",
    ])

    for inv in invoices:
        v_name = inv.vendor.name if inv.vendor else (inv.vendor_name_extracted or "")
        po_num = inv.po.po_number if inv.po else (inv.po_number_extracted or "")
        writer.writerow([
            inv.id,
            inv.invoice_number or "",
            v_name,
            po_num,
            inv.invoice_date.isoformat() if inv.invoice_date else "",
            inv.due_date.isoformat() if inv.due_date else "",
            inv.currency,
            inv.subtotal or 0.0,
            inv.tax_amount or 0.0,
            inv.grand_total or 0.0,
            inv.status,
            inv.extraction_method,
            f"{inv.extraction_confidence:.2f}",
            "Yes" if inv.is_duplicate else "No",
            inv.created_at.isoformat() if inv.created_at else "",
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices_export.csv"},
    )


@router.get("/{invoice_id}")
def get_invoice_detail(invoice_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    decision = db.query(Decision).filter(Decision.invoice_id == invoice.id).first()
    validation_results = []
    if decision:
        validation_results = (
            db.query(ValidationResult)
            .filter(ValidationResult.decision_id == decision.id)
            .all()
        )

    stages = (
        db.query(ProcessingStage)
        .filter(ProcessingStage.invoice_id == invoice.id)
        .order_by(ProcessingStage.started_at.asc())
        .all()
    )

    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.invoice_id == invoice.id)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    return {
        "invoice": {
            "id": invoice.id,
            "filename": invoice.filename,
            "original_filename": invoice.original_filename,
            "file_path": invoice.file_path,
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
            "payment_terms": invoice.payment_terms,
            "extraction_confidence": invoice.extraction_confidence,
            "extraction_method": invoice.extraction_method,
            "status": invoice.status,
            "notes": invoice.notes,
            "is_duplicate": invoice.is_duplicate,
            "duplicate_of_id": invoice.duplicate_of_id,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
            "processed_at": invoice.processed_at.isoformat() if invoice.processed_at else None,
        },
        "line_items": [
            {
                "id": li.id,
                "line_number": li.line_number,
                "description": li.description,
                "sku": li.sku,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "tax_rate": li.tax_rate,
                "tax_amount": li.tax_amount,
                "total_price": li.total_price,
                "confidence": li.confidence,
            }
            for li in invoice.line_items
        ],
        "vendor": {
            "id": invoice.vendor.id,
            "name": invoice.vendor.name,
            "approval_status": invoice.vendor.approval_status,
            "tax_id": invoice.vendor.tax_id,
            "gstin": invoice.vendor.gstin,
        } if invoice.vendor else None,
        "purchase_order": {
            "id": invoice.po.id,
            "po_number": invoice.po.po_number,
            "status": invoice.po.status,
            "total_amount": invoice.po.total_amount,
            "utilized_amount": invoice.po.utilized_amount,
            "remaining_amount": invoice.po.remaining_amount,
            "currency": invoice.po.currency,
        } if invoice.po else None,
        "decision": {
            "id": decision.id,
            "decision": decision.decision,
            "confidence_score": decision.confidence_score,
            "primary_reason": decision.primary_reason,
            "explanation": decision.explanation or [],
            "discrepancies": decision.discrepancies or [],
            "validation_summary": decision.validation_summary or {},
            "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
            "decided_by": decision.decided_by,
            "is_manual_override": decision.is_manual_override,
            "override_reason": decision.override_reason,
            "reviewer_notes": decision.reviewer_notes,
            "reviewer_name": decision.reviewer_name,
        } if decision else None,
        "validation_results": [
            {
                "id": vr.id,
                "rule_name": vr.rule_name,
                "passed": vr.passed,
                "severity": vr.severity,
                "message": vr.message,
                "details": vr.details,
            }
            for vr in validation_results
        ],
        "stages": [
            {
                "id": s.id,
                "stage_name": s.stage_name,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "duration_ms": s.duration_ms,
                "findings": s.findings,
                "error_message": s.error_message,
            }
            for s in stages
        ],
        "audit_logs": [
            {
                "id": al.id,
                "action": al.action,
                "actor": al.actor,
                "timestamp": al.timestamp.isoformat() if al.timestamp else None,
                "before_state": al.before_state,
                "after_state": al.after_state,
                "notes": al.notes,
            }
            for al in audit_logs
        ],
    }


@router.get("/{invoice_id}/pdf")
def get_invoice_pdf(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice or not invoice.file_path or not os.path.exists(invoice.file_path):
        raise HTTPException(status_code=404, detail="PDF file not found for this invoice")
    return FileResponse(
        invoice.file_path,
        media_type="application/pdf",
        filename=invoice.original_filename,
    )


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Clean up physical file if it exists
    if invoice.file_path and os.path.exists(invoice.file_path):
        try:
            os.remove(invoice.file_path)
        except Exception:
            pass

    db.delete(invoice)
    db.commit()
    return {"status": "success", "message": f"Invoice {invoice_id} deleted"}
