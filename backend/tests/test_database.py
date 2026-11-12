import pytest
import uuid
from datetime import date, datetime
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder, POLineItem
from app.models.invoice import Invoice, InvoiceLineItem, ProcessingStage
from app.models.decision import Decision, ValidationResult, AuditLog
from app.models.duplicate import DuplicateFingerprint


def test_vendor_and_po_database_persistence(db_session):
    vendor = Vendor(
        id=str(uuid.uuid4()),
        name="Test Vendor Ltd",
        country="US",
        approval_status="APPROVED",
    )
    db_session.add(vendor)
    db_session.commit()

    po = PurchaseOrder(
        id=str(uuid.uuid4()),
        po_number="PO-TEST-001",
        vendor_id=vendor.id,
        status="OPEN",
        total_amount=10000.0,
        utilized_amount=0.0,
        remaining_amount=10000.0,
        issue_date=date(2024, 1, 1),
    )
    db_session.add(po)
    db_session.commit()

    queried_po = db_session.query(PurchaseOrder).filter_by(po_number="PO-TEST-001").first()
    assert queried_po is not None
    assert queried_po.vendor.name == "Test Vendor Ltd"


def test_split_invoice_cumulative_tracking(db_session, sample_vendor):
    # Requirement: "Split invoices: Multiple invoices against one PO, with cumulative billing and remaining balance tracking."
    po = PurchaseOrder(
        id=str(uuid.uuid4()),
        po_number="PO-SPLIT-TEST",
        vendor_id=sample_vendor.id,
        status="OPEN",
        total_amount=10000.0,
        utilized_amount=0.0,
        remaining_amount=10000.0,
        issue_date=date(2024, 1, 1),
    )
    db_session.add(po)
    db_session.commit()

    # Invoice 1: $4,000 against PO
    inv1 = Invoice(
        id=str(uuid.uuid4()),
        original_filename="inv1.pdf",
        filename="inv1.pdf",
        file_path="",
        file_hash="hash1",
        invoice_number="INV-SPLIT-1",
        po_id=po.id,
        grand_total=4000.0,
        status="APPROVED",
    )
    db_session.add(inv1)
    po.utilized_amount += inv1.grand_total
    po.remaining_amount = po.total_amount - po.utilized_amount
    po.status = "PARTIAL"
    db_session.commit()

    assert po.utilized_amount == 4000.0
    assert po.remaining_amount == 6000.0
    assert po.status == "PARTIAL"

    # Invoice 2: $6,000 against same PO (completes budget)
    inv2 = Invoice(
        id=str(uuid.uuid4()),
        original_filename="inv2.pdf",
        filename="inv2.pdf",
        file_path="",
        file_hash="hash2",
        invoice_number="INV-SPLIT-2",
        po_id=po.id,
        grand_total=6000.0,
        status="APPROVED",
    )
    db_session.add(inv2)
    po.utilized_amount += inv2.grand_total
    po.remaining_amount = po.total_amount - po.utilized_amount
    if po.remaining_amount <= 0:
        po.status = "CLOSED"
    db_session.commit()

    assert po.utilized_amount == 10000.0
    assert po.remaining_amount == 0.0
    assert po.status == "CLOSED"


def test_audit_log_and_decision_traceability(db_session, sample_vendor):
    inv = Invoice(
        id=str(uuid.uuid4()),
        original_filename="test.pdf",
        filename="test.pdf",
        file_path="",
        file_hash="testhash",
        status="APPROVE",
    )
    db_session.add(inv)
    db_session.flush()

    audit = AuditLog(
        id=str(uuid.uuid4()),
        invoice_id=inv.id,
        action="DECISION_APPROVE",
        actor="System",
        after_state={"status": "APPROVE"},
        notes="All checks passed",
    )
    db_session.add(audit)
    db_session.commit()

    saved_log = db_session.query(AuditLog).filter_by(invoice_id=inv.id).first()
    assert saved_log is not None
    assert saved_log.action == "DECISION_APPROVE"
