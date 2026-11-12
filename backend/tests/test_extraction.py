import os
import pytest
from app.services.extraction import InvoiceExtractor, ExtractionResult


@pytest.fixture
def extractor():
    return InvoiceExtractor()


def test_regex_pattern_invoice_number(extractor):
    text = "TAX INVOICE\nInvoice Number: INV-998877\nDate: 10/12/2024"
    result = ExtractionResult()
    extractor._parse_fields(text, result)
    assert result.invoice_number == "INV-998877"
    assert result.field_confidence.get("invoice_number", 0) > 0.8


def test_regex_pattern_po_number(extractor):
    text = "Purchase Order #: PO-2024-8899\nPayment Terms: Net 30"
    result = ExtractionResult()
    extractor._parse_fields(text, result)
    assert result.po_number == "PO-2024-8899"


def test_regex_pattern_gstin(extractor):
    text = "Vendor GSTIN: 22AAAAA0000A1Z5\nRegistered in Maharashtra"
    result = ExtractionResult()
    extractor._parse_fields(text, result)
    assert result.vendor_gstin == "22AAAAA0000A1Z5"


def test_regex_pattern_currency(extractor):
    text = "Currency: EUR\nTotal: 1,500.00"
    result = ExtractionResult()
    extractor._parse_fields(text, result)
    assert result.currency == "EUR"


def test_financial_amounts_extraction(extractor):
    text = """
    Subtotal: $2,500.00
    Tax: $200.00
    Discount: $50.00
    Shipping: $25.00
    Grand Total: $2,675.00
    """
    result = ExtractionResult()
    extractor._parse_fields(text, result)
    assert result.subtotal == 2500.0
    assert result.tax_amount == 200.0
    assert result.discount_amount == 50.0
    assert result.shipping_amount == 25.0
    assert result.grand_total == 2675.0


def test_real_sample_pdf_extraction(extractor):
    pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_invoices", "normal_invoice.pdf")
    if os.path.exists(pdf_path):
        result = extractor.extract(pdf_path)
        assert result.invoice_number == "INV-2024-001"
        assert result.po_number == "PO-2024-001"
        assert result.grand_total == 1296.0
        assert result.overall_confidence > 0.5


def test_confidence_scoring(extractor):
    res_high = ExtractionResult(
        invoice_number="INV-100",
        grand_total=100.0,
        vendor_name="Acme",
        invoice_date="11/01/2024",
        subtotal=90.0,
        po_number="PO-1",
        field_confidence={"invoice_number": 0.9, "grand_total": 0.9, "vendor_name": 0.9},
    )
    score_high = extractor._calculate_confidence(res_high)
    assert score_high > 0.6

    res_empty = ExtractionResult()
    score_empty = extractor._calculate_confidence(res_empty)
    assert score_empty == 0.0
