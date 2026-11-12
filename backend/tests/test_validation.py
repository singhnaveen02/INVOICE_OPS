import pytest
from app.services.validation import ValidationEngine
from app.services.matching import MatchResult
from app.services.extraction import ExtractionResult
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder
import uuid
from datetime import date


@pytest.fixture
def validator():
    return ValidationEngine()


def test_rule1_vendor_approval_approved(db_session, validator, sample_vendor, clean_extraction):
    mr = MatchResult(matched_vendor=sample_vendor)
    results = validator.validate(clean_extraction, mr, db_session)
    r1 = next(r for r in results if r.rule_name == "vendor_approval")
    assert r1.passed is True
    assert r1.severity == "INFO"


def test_rule1_vendor_approval_rejected(db_session, validator, clean_extraction):
    bad_vendor = Vendor(
        id=str(uuid.uuid4()),
        name="Banned Vendor Inc",
        approval_status="REJECTED",
    )
    db_session.add(bad_vendor)
    db_session.commit()

    mr = MatchResult(matched_vendor=bad_vendor)
    results = validator.validate(clean_extraction, mr, db_session)
    r1 = next(r for r in results if r.rule_name == "vendor_approval")
    assert r1.passed is False
    assert r1.severity == "CRITICAL"


def test_rule2_mandatory_fields_missing(db_session, validator, sample_vendor):
    ext = ExtractionResult(
        vendor_name=None,
        invoice_number=None,
        grand_total=None,
    )
    mr = MatchResult(matched_vendor=sample_vendor)
    results = validator.validate(ext, mr, db_session)
    r2 = next(r for r in results if r.rule_name == "mandatory_fields")
    assert r2.passed is False
    assert "invoice_number" in r2.details.get("missing_fields", [])


def test_rule3_duplicate_detection(db_session, validator, clean_extraction, sample_vendor):
    mr = MatchResult(matched_vendor=sample_vendor)
    # With is_duplicate=True
    results = validator.validate(clean_extraction, mr, db_session, is_duplicate=True, duplicate_of_id="inv-orig")
    r3 = next(r for r in results if r.rule_name == "duplicate_detection")
    assert r3.passed is False
    assert r3.severity == "CRITICAL"


def test_rule5_po_status_closed_rejects(db_session, validator, clean_extraction, sample_vendor):
    closed_po = PurchaseOrder(
        id=str(uuid.uuid4()),
        po_number="PO-CLOSED",
        vendor_id=sample_vendor.id,
        status="CLOSED",
        currency="USD",
        total_amount=1000.0,
        utilized_amount=1000.0,
        issue_date=date(2024, 1, 1),
    )
    db_session.add(closed_po)
    db_session.commit()

    mr = MatchResult(matched_vendor=sample_vendor, matched_po=closed_po)
    results = validator.validate(clean_extraction, mr, db_session)
    r5 = next(r for r in results if r.rule_name == "po_status")
    assert r5.passed is False
    assert r5.severity == "CRITICAL"


def test_rule8_tax_reconciliation_math(db_session, validator, sample_vendor, sample_po):
    # Subtotal 1000 + Tax 100 = 1100. Stated grand total: 1100 -> Pass
    clean = ExtractionResult(
        subtotal=1000.0,
        tax_amount=100.0,
        discount_amount=0.0,
        shipping_amount=0.0,
        grand_total=1100.0,
        invoice_number="INV-1",
        vendor_name="Acme",
        invoice_date="11/01/2024",
    )
    mr = MatchResult(matched_vendor=sample_vendor, matched_po=sample_po)
    results = validator.validate(clean, mr, db_session)
    r8 = next(r for r in results if r.rule_name == "tax_reconciliation")
    assert r8.passed is True

    # Bad math: Subtotal 1000 + Tax 100 = 1100, but stated grand total is 1500!
    bad_math = ExtractionResult(
        subtotal=1000.0,
        tax_amount=100.0,
        grand_total=1500.0,
        invoice_number="INV-2",
        vendor_name="Acme",
        invoice_date="11/01/2024",
    )
    results_bad = validator.validate(bad_math, mr, db_session)
    r8_bad = next(r for r in results_bad if r.rule_name == "tax_reconciliation")
    assert r8_bad.passed is False
    assert r8_bad.severity == "ERROR"


def test_rule9_currency_mismatch(db_session, validator, sample_vendor, sample_po):
    # PO is USD, invoice claims EUR
    mismatch = ExtractionResult(
        currency="EUR",
        subtotal=100.0,
        grand_total=100.0,
        invoice_number="INV-EUR",
        vendor_name="Acme",
        invoice_date="11/01/2024",
    )
    mr = MatchResult(matched_vendor=sample_vendor, matched_po=sample_po)
    results = validator.validate(mismatch, mr, db_session)
    r9 = next(r for r in results if r.rule_name == "currency_check")
    assert r9.passed is False
    assert r9.severity == "ERROR"


def test_rule10_cumulative_po_utilization_budget_exceeded(db_session, validator, sample_vendor, sample_po):
    # sample_po total is 5000. Invoice wants 6000 -> Exceeds budget -> CRITICAL
    over_budget = ExtractionResult(
        subtotal=6000.0,
        grand_total=6000.0,
        invoice_number="INV-OVER",
        vendor_name="Acme",
        invoice_date="11/01/2024",
    )
    mr = MatchResult(matched_vendor=sample_vendor, matched_po=sample_po)
    results = validator.validate(over_budget, mr, db_session)
    r10 = next(r for r in results if r.rule_name == "po_utilization")
    assert r10.passed is False
    assert r10.severity == "CRITICAL"
