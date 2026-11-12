import pytest
from app.services.matching import POMatchingEngine
from app.services.extraction import ExtractionResult
from app.models.vendor import Vendor
from app.models.purchase_order import PurchaseOrder


@pytest.fixture
def matcher():
    return POMatchingEngine()


def test_stage1_exact_po_match(db_session, matcher, sample_vendor, sample_po):
    extraction = ExtractionResult(
        po_number="PO-2024-001",
        grand_total=1296.0,
    )
    result = matcher.match(db_session, extraction)
    assert result.matched_po is not None
    assert result.matched_po.id == sample_po.id
    assert result.po_confidence == 1.0
    assert result.match_method == "exact_po"
    assert result.matched_vendor is not None
    assert result.matched_vendor.id == sample_vendor.id


def test_stage2_fuzzy_vendor_matching(db_session, matcher, sample_vendor):
    # Test slightly misspelled or variations
    extraction = ExtractionResult(
        vendor_name="Acme Corp.",  # Fuzzy match for Acme Corporation
        po_number=None,
    )
    result = matcher.match(db_session, extraction)
    assert result.matched_vendor is not None
    assert result.matched_vendor.id == sample_vendor.id
    assert result.vendor_confidence >= 0.8


def test_stage2_vendor_gstin_exact_match(db_session, matcher, sample_vendor):
    extraction = ExtractionResult(
        vendor_name="Unknown Name LLC",
        vendor_gstin="22AAAAA0000A1Z5",  # exact match
    )
    result = matcher.match(db_session, extraction)
    assert result.matched_vendor is not None
    assert result.matched_vendor.id == sample_vendor.id
    assert result.vendor_confidence == 1.0


def test_never_match_po_on_similar_amount_only(db_session, matcher, sample_po):
    # Requirement: "Never match a PO based only on similar amounts."
    extraction = ExtractionResult(
        vendor_name="Completely Random Vendor",
        po_number=None,
        grand_total=5000.0,  # Exact amount of sample_po, but no vendor or PO relation
    )
    result = matcher.match(db_session, extraction)
    assert result.matched_po is None
    assert result.is_ambiguous is True or result.po_confidence == 0.0


def test_unmatched_returns_empty_and_ambiguous(db_session, matcher):
    extraction = ExtractionResult(
        vendor_name="NonExistent Vendor XYZ",
        po_number="PO-9999-NONEXISTENT",
    )
    result = matcher.match(db_session, extraction)
    assert result.matched_vendor is None
    assert result.matched_po is None
    assert result.is_ambiguous is True
