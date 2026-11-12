import pytest
from app.services.duplicate import DuplicateDetector
from app.models.invoice import Invoice
from app.models.duplicate import DuplicateFingerprint
import uuid


@pytest.fixture
def detector():
    return DuplicateDetector()


def test_content_hash_identical_bytes(db_session, detector):
    pdf_bytes = b"%PDF-1.4 sample invoice content 12345"
    fp1 = detector.compute_fingerprints(pdf_bytes, "Acme Corp", "INV-100", 500.0)

    # Save to DB
    inv_id = str(uuid.uuid4())
    detector.save_fingerprint(db_session, inv_id, fp1)

    # Check identical bytes
    is_dup, dup_of, reason = detector.check_duplicate(db_session, fp1)
    assert is_dup is True
    assert dup_of == inv_id
    assert "Exact PDF content match" in reason


def test_normalized_vendor_invoice_key_duplicate(db_session, detector):
    # Same vendor and invoice number, but different file bytes (e.g. re-exported PDF)
    bytes1 = b"%PDF-1.4 version 1"
    bytes2 = b"%PDF-1.4 version 2 with different timestamp"

    fp1 = detector.compute_fingerprints(bytes1, "Acme Corporation", "INV-2024-001", 1200.0)
    inv_id1 = str(uuid.uuid4())
    detector.save_fingerprint(db_session, inv_id1, fp1)

    fp2 = detector.compute_fingerprints(bytes2, "acme corporation ", "inv-2024-001", 1200.0)
    is_dup, dup_of, reason = detector.check_duplicate(db_session, fp2)
    assert is_dup is True
    assert dup_of == inv_id1
    assert "Same vendor + invoice number" in reason


def test_different_invoice_same_vendor_not_duplicate(db_session, detector):
    bytes1 = b"%PDF-1.4 invoice 1"
    bytes2 = b"%PDF-1.4 invoice 2"

    fp1 = detector.compute_fingerprints(bytes1, "Acme Corp", "INV-001", 100.0)
    inv_id1 = str(uuid.uuid4())
    detector.save_fingerprint(db_session, inv_id1, fp1)

    fp2 = detector.compute_fingerprints(bytes2, "Acme Corp", "INV-002", 100.0)
    is_dup, dup_of, reason = detector.check_duplicate(db_session, fp2)
    assert is_dup is False
    assert dup_of is None
