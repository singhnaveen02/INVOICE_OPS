"""
Generates realistic sample PDF invoices for InvoiceOps demonstration and testing.
Scenarios covered:
1. normal_invoice.pdf - Clean match with Acme Corporation (PO-2024-001) -> APPROVE
2. split_invoice_1.pdf - 1st partial invoice against Global Logistics (PO-2024-003) -> APPROVE
3. split_invoice_2.pdf - 2nd partial invoice against same PO-2024-003 -> APPROVE (tracks cumulative)
4. duplicate_invoice.pdf - Identical invoice number & amounts to #1 -> REJECT (Duplicate)
5. missing_fields_invoice.pdf - Missing invoice number, PO, and uncertain vendor -> REVIEW
6. tech_invoice.pdf - TechSupplies Ltd against PO-2024-002 -> APPROVE
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

SAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_invoice_pdf(filename: str, data: dict):
    filepath = os.path.join(SAMPLE_DIR, filename)
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=inch / 2,
        leftMargin=inch / 2,
        topMargin=inch / 2,
        bottomMargin=inch / 2,
    )

    styles = getSampleStyleSheet()
    story = []

    # Vendor Header
    header_style = ParagraphStyle(
        "header",
        fontSize=20,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    story.append(Paragraph(data.get("company", "VENDOR NAME"), header_style))
    if data.get("company_address"):
        story.append(Paragraph(data["company_address"], styles["Normal"]))
    if data.get("gstin"):
        story.append(Paragraph(f"<b>GSTIN:</b> {data['gstin']}", styles["Normal"]))
    elif data.get("tax_id"):
        story.append(Paragraph(f"<b>Tax ID:</b> {data['tax_id']}", styles["Normal"]))
    story.append(Spacer(1, 16))

    # Invoice Title Bar
    title_style = ParagraphStyle(
        "title",
        fontSize=16,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1d4ed8"),
    )
    story.append(Paragraph("TAX INVOICE", title_style))
    story.append(Spacer(1, 8))

    # Details Grid
    details = [
        ["Invoice Number:", data.get("invoice_number", "N/A"), "Invoice Date:", data.get("invoice_date", "N/A")],
        ["Purchase Order:", data.get("po_number", "N/A"), "Due Date:", data.get("due_date", "N/A")],
        ["Payment Terms:", data.get("payment_terms", "Net 30"), "Currency:", data.get("currency", "USD")],
    ]
    details_table = Table(details, colWidths=[1.5 * inch, 2.5 * inch, 1.5 * inch, 2.0 * inch])
    details_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
        ])
    )
    story.append(details_table)
    story.append(Spacer(1, 16))

    # Bill To
    story.append(Paragraph("<b>Billed To:</b>", styles["Normal"]))
    story.append(Paragraph("MidSize Corp Inc.<br/>Accounts Payable Department<br/>100 Enterprise Way, Suite 400<br/>San Francisco, CA 94105", styles["Normal"]))
    story.append(Spacer(1, 14))

    # Line Items Table
    items_data = [["#", "Description", "SKU", "Qty", "Unit Price", "Total"]]
    for i, item in enumerate(data.get("line_items", []), 1):
        items_data.append([
            str(i),
            item.get("description", ""),
            item.get("sku", "-"),
            str(item.get("quantity", 1)),
            f"${item.get('unit_price', 0):.2f}",
            f"${item.get('total', 0):.2f}",
        ])

    items_table = Table(
        items_data,
        colWidths=[0.4 * inch, 3.2 * inch, 1.2 * inch, 0.6 * inch, 1.0 * inch, 1.1 * inch],
    )
    items_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ])
    )
    story.append(items_table)
    story.append(Spacer(1, 14))

    # Totals Summary
    totals = []
    if data.get("subtotal") is not None:
        totals.append(["Subtotal:", f"${data['subtotal']:.2f}"])
    if data.get("tax_amount") is not None:
        totals.append([f"Tax ({data.get('tax_rate', 8)}%):", f"${data['tax_amount']:.2f}"])
    if data.get("shipping_amount"):
        totals.append(["Shipping:", f"${data['shipping_amount']:.2f}"])
    if data.get("discount_amount"):
        totals.append(["Discount:", f"-${data['discount_amount']:.2f}"])
    totals.append(["GRAND TOTAL:", f"${data['grand_total']:.2f}"])

    totals_table = Table(totals, colWidths=[5.4 * inch, 2.1 * inch])
    totals_table.setStyle(
        TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 12),
            ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.HexColor("#1d4ed8")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(totals_table)

    if data.get("notes"):
        story.append(Spacer(1, 14))
        story.append(Paragraph(f"<b>Notes / Terms:</b> {data['notes']}", styles["Normal"]))

    doc.build(story)
    print(f"Generated: {filepath}")
    return filepath


def generate_all_samples():
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    samples = [
        # 1. Normal Clean Invoice -> Should APPROVE
        {
            "filename": "normal_invoice.pdf",
            "data": {
                "company": "Acme Corporation",
                "company_address": "1 Acme Plaza, Phoenix, AZ 85001",
                "gstin": "22AAAAA0000A1Z5",
                "tax_id": "EIN-12-3456789",
                "invoice_number": "INV-2024-001",
                "invoice_date": "11/01/2024",
                "due_date": "12/01/2024",
                "po_number": "PO-2024-001",
                "payment_terms": "Net 30",
                "currency": "USD",
                "line_items": [
                    {"description": "Ergonomic Office Chair Model X200", "sku": "CHAIR-X200", "quantity": 5, "unit_price": 150.00, "total": 750.00},
                    {"description": "LED Desk Lamp Pro", "sku": "LAMP-PRO", "quantity": 10, "unit_price": 45.00, "total": 450.00},
                ],
                "subtotal": 1200.00,
                "tax_amount": 96.00,
                "tax_rate": 8,
                "grand_total": 1296.00,
                "notes": "Thank you for your business. Payment due within 30 days.",
            },
        },
        # 2. Split Invoice Part 1 -> Should APPROVE (PO-2024-003 has $12,000 budget)
        {
            "filename": "split_invoice_1.pdf",
            "data": {
                "company": "Global Logistics Inc",
                "company_address": "88 Harbor Boulevard, Miami, FL 33101",
                "tax_id": "EIN-34-5678901",
                "invoice_number": "INV-2024-003A",
                "invoice_date": "11/01/2024",
                "due_date": "12/31/2024",
                "po_number": "PO-2024-003",
                "payment_terms": "Net 60",
                "currency": "USD",
                "line_items": [
                    {"description": "International Freight Logistics - Part 1", "sku": "FREIGHT-01", "quantity": 1, "unit_price": 5000.00, "total": 5000.00},
                ],
                "subtotal": 5000.00,
                "tax_amount": 0.00,
                "grand_total": 5000.00,
                "notes": "Partial invoice 1 of 2 against PO-2024-003.",
            },
        },
        # 3. Split Invoice Part 2 -> Should APPROVE (Cumulative = 5000 + 4800 = 9800 <= 12000)
        {
            "filename": "split_invoice_2.pdf",
            "data": {
                "company": "Global Logistics Inc",
                "company_address": "88 Harbor Boulevard, Miami, FL 33101",
                "tax_id": "EIN-34-5678901",
                "invoice_number": "INV-2024-003B",
                "invoice_date": "11/15/2024",
                "due_date": "01/15/2025",
                "po_number": "PO-2024-003",
                "payment_terms": "Net 60",
                "currency": "USD",
                "line_items": [
                    {"description": "Customs Clearing & Delivery - Part 2", "sku": "CUSTOMS-02", "quantity": 1, "unit_price": 4800.00, "total": 4800.00},
                ],
                "subtotal": 4800.00,
                "tax_amount": 0.00,
                "grand_total": 4800.00,
                "notes": "Partial invoice 2 of 2 against PO-2024-003. Cumulative total $9,800.",
            },
        },
        # 4. Duplicate Invoice -> Should REJECT (Same invoice # and vendor as #1)
        {
            "filename": "duplicate_invoice.pdf",
            "data": {
                "company": "Acme Corporation",
                "company_address": "1 Acme Plaza, Phoenix, AZ 85001",
                "gstin": "22AAAAA0000A1Z5",
                "tax_id": "EIN-12-3456789",
                "invoice_number": "INV-2024-001",  # Duplicate number!
                "invoice_date": "11/01/2024",
                "due_date": "12/01/2024",
                "po_number": "PO-2024-001",
                "payment_terms": "Net 30",
                "currency": "USD",
                "line_items": [
                    {"description": "Ergonomic Office Chair Model X200", "sku": "CHAIR-X200", "quantity": 5, "unit_price": 150.00, "total": 750.00},
                    {"description": "LED Desk Lamp Pro", "sku": "LAMP-PRO", "quantity": 10, "unit_price": 45.00, "total": 450.00},
                ],
                "subtotal": 1200.00,
                "tax_amount": 96.00,
                "tax_rate": 8,
                "grand_total": 1296.00,
                "notes": "Re-submitted copy for testing duplicate detection engine.",
            },
        },
        # 5. Missing Fields Invoice -> Should trigger REVIEW
        {
            "filename": "missing_fields_invoice.pdf",
            "data": {
                "company": "ACME",  # Sparse/unclear name
                "company_address": "",
                "tax_id": "",
                "invoice_number": "",  # Missing invoice number!
                "invoice_date": "11/10/2024",
                "due_date": "",
                "po_number": "",  # Missing PO number!
                "payment_terms": "",
                "currency": "USD",
                "line_items": [
                    {"description": "General consulting and misc services", "sku": "", "quantity": 1, "unit_price": 750.00, "total": 750.00},
                ],
                "subtotal": 750.00,
                "grand_total": 750.00,
                "notes": "Invoice generated with missing metadata fields.",
            },
        },
        # 6. Tech Supplies Invoice -> Clean match with PO-2024-002
        {
            "filename": "tech_invoice.pdf",
            "data": {
                "company": "TechSupplies Ltd",
                "company_address": "42 Silicon Road, London, EC1A 1BB, UK",
                "tax_id": "EIN-98-7654321",
                "invoice_number": "INV-2024-002",
                "invoice_date": "11/05/2024",
                "due_date": "12/05/2024",
                "po_number": "PO-2024-002",
                "payment_terms": "Net 30",
                "currency": "USD",
                "line_items": [
                    {"description": "Server RAM 32GB DDR5 ECC", "sku": "RAM-32GB", "quantity": 10, "unit_price": 180.00, "total": 1800.00},
                    {"description": "NVMe SSD 1TB Enterprise", "sku": "SSD-1TB-ENT", "quantity": 5, "unit_price": 320.00, "total": 1600.00},
                    {"description": "Network Switch 24-Port Managed", "sku": "SWITCH-24P", "quantity": 2, "unit_price": 450.00, "total": 900.00},
                ],
                "subtotal": 4300.00,
                "tax_amount": 344.00,
                "tax_rate": 8,
                "grand_total": 4644.00,
                "notes": "Includes 1-year enterprise hardware warranty.",
            },
        },
    ]

    for s in samples:
        create_invoice_pdf(s["filename"], s["data"])
    print(f"\nAll {len(samples)} sample PDFs successfully generated in {SAMPLE_DIR}")


if __name__ == "__main__":
    generate_all_samples()
