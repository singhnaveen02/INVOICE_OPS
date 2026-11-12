import os
import uuid
import pytest
from app.models.invoice import Invoice, ProcessingStage
from app.models.decision import Decision
from app.routers.invoices import run_processing_pipeline
from app.database import SessionLocal, Base, engine


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    # Clear any leftover invoices and duplicate fingerprints before e2e tests
    db = SessionLocal()
    from app.models.duplicate import DuplicateFingerprint
    from app.models.decision import Decision, ValidationResult, AuditLog
    from app.models.invoice import InvoiceLineItem, ProcessingStage
    from app.utils.seed import seed_database
    db.query(ValidationResult).delete()
    db.query(Decision).delete()
    db.query(ProcessingStage).delete()
    db.query(InvoiceLineItem).delete()
    db.query(AuditLog).delete()
    db.query(DuplicateFingerprint).delete()
    db.query(Invoice).delete()
    db.commit()

    # Ensure vendors and POs exist
    seed_database(db)
    db.close()
    yield


def test_pipeline_normal_invoice_approves():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_invoices", "normal_invoice.pdf")
    if not os.path.exists(sample_path):
        pytest.skip("normal_invoice.pdf not generated")

    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    db = SessionLocal()
    inv_id = str(uuid.uuid4())
    inv = Invoice(
        id=inv_id,
        filename="normal_invoice.pdf",
        original_filename="normal_invoice.pdf",
        file_path=sample_path,
        file_hash="hash_normal_test",
        status="PROCESSING",
    )
    db.add(inv)
    db.commit()
    db.close()

    # Execute pipeline
    run_processing_pipeline(inv_id, sample_path, file_bytes)

    # Check results in DB
    db = SessionLocal()
    processed_inv = db.query(Invoice).filter_by(id=inv_id).first()
    assert processed_inv is not None
    assert processed_inv.status in ["APPROVE", "APPROVED"]
    assert processed_inv.invoice_number == "INV-2024-001"
    assert processed_inv.grand_total == 1296.0

    stages = db.query(ProcessingStage).filter_by(invoice_id=inv_id).all()
    assert len(stages) >= 8

    decision = db.query(Decision).filter_by(invoice_id=inv_id).first()
    assert decision is not None
    assert decision.decision in ["APPROVE", "APPROVED"]
    db.close()


def test_pipeline_duplicate_invoice_rejects():
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_invoices", "duplicate_invoice.pdf")
    if not os.path.exists(sample_path):
        pytest.skip("duplicate_invoice.pdf not generated")

    with open(sample_path, "rb") as f:
        file_bytes = f.read()

    db = SessionLocal()
    inv_id = str(uuid.uuid4())
    inv = Invoice(
        id=inv_id,
        filename="duplicate_invoice.pdf",
        original_filename="duplicate_invoice.pdf",
        file_path=sample_path,
        file_hash="hash_duplicate_test",
        status="PROCESSING",
    )
    db.add(inv)
    db.commit()
    db.close()

    # Run pipeline
    run_processing_pipeline(inv_id, sample_path, file_bytes)

    # Verify rejection due to duplicate
    db = SessionLocal()
    processed_inv = db.query(Invoice).filter_by(id=inv_id).first()
    assert processed_inv is not None
    assert processed_inv.status == "REJECTED"
    assert processed_inv.is_duplicate is True
    db.close()


def test_api_all_four_edge_cases_and_human_review():
    """
    Tests all 4 mandatory edge cases + router handlers end-to-end against SQLite:
    1. Split invoices against one PO with cumulative billing tracking.
    2. Duplicate invoice rejection + hard policy block on manual approval.
    3. Missing fields routed to REVIEW + field correction + revalidation + approval.
    4. Unapproved/rejected vendor hard policy block on manual approval + dashboard metrics.
    """
    from fastapi import HTTPException
    from app.models.purchase_order import PurchaseOrder
    from app.models.vendor import Vendor
    from app.routers.dashboard import (
        get_dashboard_stats,
        get_invoice_trends,
        get_status_distribution,
        get_po_utilization,
        get_recent_activity,
    )
    from app.routers.invoices import list_invoices, export_invoices_csv, get_invoice_detail
    from app.routers.review import (
        get_review_queue,
        get_review_detail,
        revalidate_invoice,
        submit_review_decision,
        ReviewRevalidatePayload,
        ReviewSubmissionPayload,
    )

    samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sample_invoices")

    def run_pdf_file(fname: str) -> str:
        path = os.path.join(samples_dir, fname)
        with open(path, "rb") as f:
            file_bytes = f.read()
        db = SessionLocal()
        inv_id = str(uuid.uuid4())
        inv = Invoice(
            id=inv_id,
            filename=fname,
            original_filename=fname,
            file_path=path,
            file_hash=f"test_hash_{inv_id}",
            status="PROCESSING",
        )
        db.add(inv)
        db.commit()
        db.close()
        run_processing_pipeline(inv_id, path, file_bytes)
        return inv_id

    # 1. Split invoices against PO-2024-003 (Budget $10,000)
    db = SessionLocal()
    po3 = db.query(PurchaseOrder).filter_by(po_number="PO-2024-003").first()
    assert po3 is not None
    po3.utilized_amount = 0.0
    po3.remaining_amount = po3.total_amount
    po3.status = "OPEN"
    db.commit()
    db.close()

    inv1_id = run_pdf_file("split_invoice_1.pdf")
    inv2_id = run_pdf_file("split_invoice_2.pdf")

    db = SessionLocal()
    inv1 = db.query(Invoice).filter_by(id=inv1_id).first()
    inv2 = db.query(Invoice).filter_by(id=inv2_id).first()
    assert inv1.status == "APPROVED"
    assert inv2.status == "APPROVED"
    po3_after = db.query(PurchaseOrder).filter_by(po_number="PO-2024-003").first()
    assert po3_after.utilized_amount == pytest.approx(9800.0, abs=1.0)
    assert po3_after.remaining_amount == pytest.approx(po3_after.total_amount - 9800.0, abs=1.0)
    assert po3_after.status == "PARTIAL"

    # 2. Missing fields invoice -> REVIEW -> Revalidate -> Approve
    missing_id = run_pdf_file("missing_fields_invoice.pdf")
    missing_inv = db.query(Invoice).filter_by(id=missing_id).first()
    assert missing_inv.status == "REVIEW"

    queue = get_review_queue(db=db)
    assert any(item.id == missing_id for item in queue)

    review_detail = get_review_detail(missing_id, db=db)
    assert review_detail["invoice"]["id"] == missing_id

    acme = db.query(Vendor).filter(Vendor.name.ilike("%Acme%")).first()
    open_po = db.query(PurchaseOrder).filter(
        PurchaseOrder.vendor_id == acme.id, PurchaseOrder.status == "OPEN"
    ).first()

    reval = revalidate_invoice(
        missing_id,
        ReviewRevalidatePayload(
            reviewer_name="Test AP Specialist",
            field_corrections={
                "invoice_number": "INV-FIXED-999",
                "invoice_date": "2024-06-15",
                "subtotal": 200.0,
                "tax_amount": 16.0,
                "grand_total": 216.0,
            },
            new_vendor_id=acme.id,
            new_po_id=open_po.id if open_po else "",
        ),
        db=db,
    )
    assert "validation_results" in reval
    assert len(reval["validation_results"]) == 11

    sub = submit_review_decision(
        missing_id,
        ReviewSubmissionPayload(
            decision="APPROVE",
            reviewer_name="Test AP Specialist",
            override_reason="Corrected missing fields from vendor PDF",
            rerun_validation=True,
        ),
        db=db,
    )
    assert sub["decision"] == "APPROVED"

    # 3. Duplicate invoice manual approval must be blocked (hard policy rule)
    dup_inv = db.query(Invoice).filter_by(is_duplicate=True).first()
    assert dup_inv is not None
    with pytest.raises(HTTPException) as exc_info:
        submit_review_decision(
            dup_inv.id,
            ReviewSubmissionPayload(
                decision="APPROVE",
                reviewer_name="Test AP Specialist",
                override_reason="Attempt override",
            ),
            db=db,
        )
    assert exc_info.value.status_code == 400
    assert "duplicate" in exc_info.value.detail.lower()

    # 4. Rejected vendor manual approval must also be blocked (hard policy rule)
    rejected_vendor = Vendor(
        id=str(uuid.uuid4()),
        name="Blocked Test Vendor LLC",
        approval_status="REJECTED",
    )
    db.add(rejected_vendor)
    db.flush()
    inv_bad_vendor = Invoice(
        id=str(uuid.uuid4()),
        filename="bad_vendor.pdf",
        original_filename="bad_vendor.pdf",
        file_path="",
        file_hash=f"bad_v_{uuid.uuid4().hex}",
        vendor_id=rejected_vendor.id,
        invoice_number="INV-BAD-V-1",
        grand_total=100.0,
        status="REVIEW",
    )
    db.add(inv_bad_vendor)
    db.commit()
    with pytest.raises(HTTPException) as exc_v:
        submit_review_decision(
            inv_bad_vendor.id,
            ReviewSubmissionPayload(
                decision="APPROVE",
                reviewer_name="Test AP Specialist",
                override_reason="Attempt vendor override",
            ),
            db=db,
        )
    assert exc_v.value.status_code == 400
    assert "REJECTED" in exc_v.value.detail

    # 5. Dashboard, listing, detail & export verification against live DB records
    stats = get_dashboard_stats(db=db)
    assert stats["total_invoices"] >= 5
    assert stats["approved_invoices"] >= 3
    assert stats["rejected_invoices"] >= 1
    assert len(get_invoice_trends(db=db)) == 30
    assert len(get_status_distribution(db=db)) >= 1
    assert len(get_po_utilization(db=db)) >= 1
    assert len(get_recent_activity(db=db)) >= 1
    listed = list_invoices(
        status="APPROVED",
        vendor_id=None,
        po_number=None,
        date_from=None,
        date_to=None,
        min_amount=None,
        max_amount=None,
        search=None,
        page=1,
        page_size=20,
        db=db,
    )
    assert listed.total >= 3
    detail = get_invoice_detail(inv1_id, db=db)
    assert len(detail["stages"]) == 10
    assert len(detail["validation_results"]) == 11
    csv_resp = export_invoices_csv(db=db)
    assert csv_resp.status_code == 200
    db.close()
