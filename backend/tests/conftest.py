import pytest
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app import models  # noqa: F401 - registers models
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder, POLineItem
from app.services.extraction import ExtractionResult, ExtractedLineItem
import uuid
from datetime import date, datetime


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite database session for isolated testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def sample_vendor(db_session):
    vendor = Vendor(
        id=str(uuid.uuid4()),
        name="Acme Corporation",
        gstin="22AAAAA0000A1Z5",
        tax_id="EIN-12-3456789",
        email="billing@acmecorp.com",
        phone="+1-800-555-0101",
        address="1 Acme Plaza, Phoenix, AZ",
        country="US",
        approval_status="APPROVED",
        approved_by="admin@invoiceops.com",
        approved_at=datetime.utcnow(),
    )
    db_session.add(vendor)
    db_session.commit()
    db_session.refresh(vendor)
    return vendor


@pytest.fixture
def sample_po(db_session, sample_vendor):
    po = PurchaseOrder(
        id=str(uuid.uuid4()),
        po_number="PO-2024-001",
        vendor_id=sample_vendor.id,
        status="OPEN",
        currency="USD",
        total_amount=5000.00,
        utilized_amount=0.0,
        remaining_amount=5000.00,
        issue_date=date(2024, 1, 1),
        expiry_date=date(2024, 12, 31),
        payment_terms="Net 30",
        description="Office equipment and supplies annual contract",
    )
    db_session.add(po)
    db_session.flush()

    line1 = POLineItem(
        id=str(uuid.uuid4()),
        po_id=po.id,
        line_number=1,
        description="Office Chairs",
        sku="CHAIR-01",
        quantity=10.0,
        unit_price=250.0,
        total_price=2500.0,
        unit_of_measure="EA",
    )
    line2 = POLineItem(
        id=str(uuid.uuid4()),
        po_id=po.id,
        line_number=2,
        description="Standing Desks",
        sku="DESK-01",
        quantity=5.0,
        unit_price=500.0,
        total_price=2500.0,
        unit_of_measure="EA",
    )
    db_session.add(line1)
    db_session.add(line2)
    db_session.commit()
    db_session.refresh(po)
    return po


@pytest.fixture
def clean_extraction():
    return ExtractionResult(
        vendor_name="Acme Corporation",
        vendor_gstin="22AAAAA0000A1Z5",
        vendor_tax_id="EIN-12-3456789",
        invoice_number="INV-2024-100",
        invoice_date="11/01/2024",
        due_date="12/01/2024",
        po_number="PO-2024-001",
        payment_terms="Net 30",
        currency="USD",
        subtotal=1200.00,
        tax_amount=96.00,
        discount_amount=0.0,
        shipping_amount=0.0,
        grand_total=1296.00,
        extraction_method="PDF",
        overall_confidence=0.92,
        field_confidence={
            "invoice_number": 0.95,
            "vendor_name": 0.90,
            "grand_total": 0.95,
            "po_number": 0.90,
        },
        line_items=[
            ExtractedLineItem(
                line_number=1,
                description="Office Chairs",
                sku="CHAIR-01",
                quantity=4.0,
                unit_price=250.0,
                total_price=1000.0,
                confidence=0.9,
            ),
            ExtractedLineItem(
                line_number=2,
                description="Desk Accessories",
                sku="ACC-01",
                quantity=2.0,
                unit_price=100.0,
                total_price=200.0,
                confidence=0.85,
            ),
        ],
    )
