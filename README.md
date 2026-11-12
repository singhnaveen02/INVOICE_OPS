# InvoiceOps — AI-Powered Accounts Payable Automation

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.3-646cff.svg)](https://vitejs.dev)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38bdf8.svg)](https://tailwindcss.com)
[![Tests Passing](https://img.shields.io/badge/Tests-34%20Passed-emerald.svg)](backend/tests)

**InvoiceOps** is a production-grade, enterprise Accounts Payable (AP) automation platform. It ingests vendor invoice PDFs (machine-readable and scanned), performs structured OCR and layout parsing, matches documents against approved Purchase Orders using multi-stage exact and fuzzy heuristics, audits 11 business and financial validation rules, and generates explainable **APPROVE**, **REVIEW**, or **REJECT** decisions backed by audit trails.

---

## Key Features

1. **Document Processing Pipeline**
   - High-throughput PyMuPDF and pdfplumber extraction.
   - OpenCV image preprocessing and Tesseract OCR fallback for scanned receipts.
   - Optional Amazon Bedrock Claude integration for complex unstructured layouts, with deterministic local fallback.
   - Line items table parsing, tax breakdown, and GSTIN/Tax ID verification.

2. **Intelligent 3-Stage PO Matching**
   - **Stage 1 (Exact):** Exact PO number, vendor tax ID, and currency lookup.
   - **Stage 2 (Fuzzy):** RapidFuzz token set ratio matching with corporate entity normalization.
   - **Stage 3 (Heuristic):** Ambiguity resolution using vendor identity, amounts, and line item similarity. *Never matches POs based on similar amounts alone.*

3. **11-Rule Business Validation Engine**
   - **Rule 1:** Vendor Approval Status (`APPROVED`, `PENDING`, `REJECTED`, `SUSPENDED`).
   - **Rule 2:** Mandatory Invoice Fields (`invoice_number`, `invoice_date`, `grand_total`, etc.).
   - **Rule 3:** Duplicate Submission Detection (SHA-256 byte hash & normalized vendor+number fingerprint).
   - **Rule 4:** Vendor & PO Cross-Validation.
   - **Rule 5:** Purchase Order Status (`OPEN`, `PARTIAL`, `CLOSED`, `CANCELLED`).
   - **Rule 6:** Invoice vs. PO Amount Tolerance checks.
   - **Rule 7:** Line Item Quantity and Unit Price Discrepancy checks.
   - **Rule 8:** Tax & Subtotal Mathematical Reconciliation ($1 rounding tolerance).
   - **Rule 9:** Multi-Currency Compatibility verification.
   - **Rule 10:** Cumulative PO Utilization (prevents billing beyond PO limits).
   - **Rule 11:** Invoice and PO Date Consistency.

4. **Deterministic Decision Engine**
   - **`APPROVE`:** All mandatory checks pass with high confidence.
   - **`REVIEW`:** Missing fields, low extraction confidence, or ambiguous matches.
   - **`REJECT`:** Hard policy violations (rejected vendor, closed PO, or confirmed duplicate).

5. **Human Review Workflow**
   - Interactive side-by-side PDF preview and extracted fields.
   - Ability to correct values, re-assign vendors/POs, and re-run validation rules.
   - Mandatory reviewer name and justification rationale.
   - Hard policy violations cannot be bypassed.

6. **Enterprise SaaS Dashboard**
   - Financial exposure metrics, total value, and duplicate detection counters.
   - 30-day invoice volume trends line chart and decision distribution pie chart.
   - Purchase order budget utilization bars and live audit trail.

---

## Architecture

```
                       ┌───────────────────────────────┐
                       │       Vendor PDF Invoices     │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │ 10-Stage Processing Pipeline   │
                       ├───────────────────────────────┤
                       │ 1. Document Received          │
                       │ 2. PDF Parsing / OCR          │
                       │ 3. Field & Line Item Extract  │
                       │ 4. Vendor Identification      │
                       │ 5. Multi-Stage PO Matching    │
                       │ 6. Duplicate Fingerprinting   │
                       │ 7. Financial Reconciliation   │
                       │ 8. 11-Rule Business Validation│
                       │ 9. Decision Engine            │
                       │ 10. Database Persistence      │
                       └───────────────┬───────────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                ▼                      ▼                      ▼
        ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
        │    APPROVE    │      │    REVIEW     │      │    REJECT     │
        │ Clean Match   │      │ Human Queue   │      │ Hard Policy   │
        └───────────────┘      └───────────────┘      └───────────────┘
```

---

## Quick Start

### Windows One-Command
Double-click `start.bat` or run:
```powershell
.\start.bat
```

### Manual Setup

#### 1. Backend (FastAPI + SQLite)
```powershell
cd backend
python -m venv venv
venv\Scripts\activate       # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend (React + Vite + Tailwind CSS)
```powershell
cd frontend
npm install
npm run dev
```

Visit **`http://localhost:5173`** to access the application.  
API documentation is available at **`http://localhost:8000/docs`**.

---

## Automated Test Suite

Run the full automated test suite (34 tests):
```powershell
cd backend
venv\Scripts\activate
pytest tests/ -v
```

Test coverage includes:
- Machine and OCR text parsing
- Multi-stage PO and fuzzy vendor matching
- Cryptographic duplicate fingerprinting
- Financial reconciliation & line items math
- All 11 validation rules
- Split invoice tracking and budget limits
- Full end-to-end pipeline execution

---

## Sample Data & Edge Cases

The project includes ready-to-test sample invoices generated in `sample_invoices/`:
- `normal_invoice.pdf`: Clean matching invoice -> Automated `APPROVE`.
- `split_invoice_1.pdf` & `split_invoice_2.pdf`: Multi-invoice billing against single PO budget.
- `duplicate_invoice.pdf`: Identical invoice number with changed filename -> Hard `REJECT`.
- `missing_fields_invoice.pdf`: Missing PO and invoice number -> Routes to `REVIEW`.
- `tech_invoice.pdf`: Approved tech equipment invoice against PO-2024-002.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for step-by-step interview demonstration instructions.
