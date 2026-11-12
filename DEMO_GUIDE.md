# InvoiceOps — Live Demonstration & Interview Guide

This guide walks through testing and demonstrating **InvoiceOps** end-to-end, highlighting the four mandatory edge cases and showing the enterprise AP workflow.

---

## 1. Quick Startup

### Option A: Windows One-Command
Double-click `start.bat` or run:
```powershell
.\start.bat
```

### Option B: Manual Terminal Execution
**Terminal 1 (Backend):**
```powershell
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm run dev
```

Open your browser to: **`http://localhost:5173`**

---

## 2. Walkthrough: The 4 Core Edge Cases

Sample PDFs are generated and ready in `sample_invoices/`:

### Scenario 1: Clean Invoice Matching -> Automated APPROVE
1. Go to **Upload & Process** tab (`http://localhost:5173/upload`).
2. Upload `sample_invoices/normal_invoice.pdf`.
3. Click **Start Automated Processing**.
4. **Expected Outcome:**
   - Watch the 10 processing stages execute live.
   - Decision: **`APPROVE`**
   - Matched Vendor: **Acme Corporation** (Approved)
   - Matched PO: **PO-2024-001**
   - All 11 validation rules pass.
   - Cumulative PO utilization updates in real-time.

---

### Scenario 2: Split Invoices (Cumulative Billing Tracking)
*Tests multi-invoice partial billing against a single PO budget.*
1. In `sample_invoices/`, notice:
   - PO-2024-003 has a total approved budget of **$12,000.00**.
   - `split_invoice_1.pdf` is for **$5,000.00**.
   - `split_invoice_2.pdf` is for **$4,800.00**.
2. Upload `split_invoice_1.pdf` -> Decision: **`APPROVE`**.
   - Go to **Purchase Orders** (`/purchase-orders`).
   - Notice PO-2024-003 status changed to **PARTIAL**, utilized amount is **$5,000.00**, remaining balance is **$7,000.00**.
3. Upload `split_invoice_2.pdf` -> Decision: **`APPROVE`**.
   - Notice PO-2024-003 utilized amount is now **$9,800.00** of **$12,000.00** (81.7% utilized).
   - If an invoice exceeds the remaining budget, Rule 10 triggers a **CRITICAL** policy rejection.

---

### Scenario 3: Duplicate Submission Detection -> Hard REJECT
1. Upload `sample_invoices/duplicate_invoice.pdf`.
   - *Note: This PDF has different metadata and filename, but identical invoice number (INV-2024-001) and vendor content.*
2. Click **Start Automated Processing**.
3. **Expected Outcome:**
   - Decision: **`REJECT`**
   - Primary Reason: **Duplicate invoice submission rejected**
   - Rule 3 (`duplicate_detection`): Fails with `CRITICAL` severity.
   - Persisted duplicate fingerprint links back to the original invoice record.

---

### Scenario 4: Missing Critical Fields & Ambiguous Matching -> Human REVIEW
1. Upload `sample_invoices/missing_fields_invoice.pdf`.
2. Click **Start Automated Processing**.
3. **Expected Outcome:**
   - Decision: **`REVIEW`**
   - Reason: Missing mandatory fields (`invoice_number`, `po_number`) and low extraction confidence.
   - Rule 2 (`mandatory_fields`): Fails with `ERROR`.
   - The invoice automatically appears in the **Review Queue** (`/review`).

4. **Demonstrating the Human Review Workflow:**
   - Go to **Review Queue** (`/review`).
   - Click **Review & Resolve** on the invoice.
   - Inspect the original PDF side-by-side with the extraction errors.
   - Re-assign the vendor to **Acme Corporation** from the dropdown.
   - Re-assign the PO to **PO-2024-001**.
   - Correct the invoice number to `INV-CORRECTED-001`.
   - Select **APPROVE FOR PAYMENT**.
   - Input your reviewer name (`Jane Doe`) and justification rationale.
   - Click **Commit Review Decision**.
   - The invoice status transitions from `REVIEW` to `APPROVE`, and a tamper-evident entry is written to the **Audit Trail**.

---

## 3. Running Automated Tests

Run the complete 34-test automated suite:
```powershell
cd backend
venv\Scripts\activate
pytest tests/ -v
```

All 34 tests will execute, validating:
- Regular expressions & OCR heuristics
- Multi-stage PO & fuzzy vendor matching
- Cryptographic & normalized duplicate detection
- Financial reconciliation & line item consistency
- 11 business rules & deterministic decision matrix
- Database persistence & cumulative split billing
