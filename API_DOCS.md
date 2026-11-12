# InvoiceOps — API Documentation

Base URL: `http://localhost:8000`  
Interactive OpenAPI / Swagger UI: `http://localhost:8000/docs`

---

## 1. System Health

### `GET /health`
Returns system status and database health.
```json
{
  "status": "healthy",
  "service": "InvoiceOps API",
  "version": "1.0.0",
  "database": "connected"
}
```

---

## 2. Invoices

### `POST /invoices/upload`
Uploads one or more invoice PDFs and executes the 10-stage processing pipeline.
- **Content-Type:** `multipart/form-data`
- **Body:** `files`: list of PDF binaries
- **Response:**
```json
{
  "uploaded": 1,
  "invoices": [
    {
      "id": "c1f7b789-9a2f-48d6-9bf3-7d72c1c1f4e1",
      "filename": "771e3d93-c40d-4340-a309-8b09e259b1dc.pdf",
      "original_filename": "normal_invoice.pdf",
      "status": "APPROVE",
      "invoice_number": "INV-2024-001",
      "grand_total": 1296.0,
      "confidence": 0.817
    }
  ]
}
```

### `POST /invoices/manual`
Creates a manual invoice entry and verifies it against the specified PO.
- **Body:**
```json
{
  "original_filename": "Manual_Bill.pdf",
  "invoice_number": "INV-MAN-01",
  "invoice_date": "2024-11-01",
  "due_date": "2024-12-01",
  "vendor_id": "v-acme-0001",
  "po_id": "po-acme-0001",
  "currency": "USD",
  "subtotal": 1200.0,
  "tax_amount": 96.0,
  "grand_total": 1296.0,
  "notes": "Emergency office supplies order"
}
```

### `GET /invoices/`
Paginated and filterable invoice listing.
- **Query Params:**
  - `status`: `APPROVE` | `REVIEW` | `REJECT` | `PROCESSING` | `PENDING`
  - `vendor_id`: string
  - `po_number`: string
  - `date_from`: `YYYY-MM-DD`
  - `date_to`: `YYYY-MM-DD`
  - `min_amount`: float
  - `max_amount`: float
  - `search`: string (matches invoice #, vendor, filename)
  - `page`: integer (default: 1)
  - `page_size`: integer (default: 20)

### `GET /invoices/{id}`
Returns full invoice entity:
- Extracted header and financial summary
- Parsed line items
- Matched vendor and approval state
- Matched PO and budget utilization
- Policy decision and human-readable explanation
- 11-point business rule validation breakdown
- 10-stage execution durations and findings
- Complete modification and audit log

### `GET /invoices/{id}/pdf`
Streams the original PDF document with `Content-Type: application/pdf`.

### `GET /invoices/export`
Exports filtered invoice records as a downloadable CSV.

### `DELETE /invoices/{id}`
Deletes the invoice record, stages, line items, and on-disk file.

---

## 3. Vendors

- `GET /vendors/`: List all vendors (supports `status` and `search` query parameters)
- `POST /vendors/`: Create a new vendor record
- `GET /vendors/{id}`: Get vendor detail with active POs
- `PUT /vendors/{id}`: Update vendor fields or approval status
- `POST /vendors/import-csv`: Upload and ingest master vendor CSV

---

## 4. Purchase Orders

- `GET /purchase-orders/`: List POs (supports `status`, `vendor_id`, and `search`)
- `POST /purchase-orders/`: Create PO with line items
- `GET /purchase-orders/{id}`: Retrieve PO with cumulative billing metrics
- `PUT /purchase-orders/{id}`: Update PO status or budget
- `POST /purchase-orders/import-csv`: Ingest master purchase orders CSV

---

## 5. Human Review Workflow

### `GET /review/queue`
Retrieves all invoices currently in `REVIEW` status requiring AP attention.

### `GET /review/{id}`
Retrieves complete review workspace:
- Extracted fields vs original PDF
- Current rule discrepancies
- List of available approved vendors and open POs for re-assignment

### `POST /review/{id}/submit`
Submits reviewer decision:
- **Body:**
```json
{
  "decision": "APPROVE",
  "reviewer_name": "Jane Doe (Senior AP Specialist)",
  "override_reason": "Verified tax ID against state register; price variance within approved limits",
  "reviewer_notes": "Procurement manager approved variance via email.",
  "field_corrections": {
    "invoice_number": "INV-2024-001",
    "grand_total": 1296.0
  },
  "new_vendor_id": "v-acme-0001",
  "new_po_id": "po-acme-0001",
  "rerun_validation": true
}
```
*Note: Manual approval strictly refuses hard policy violations (e.g. rejected vendors or confirmed duplicate files).*

---

## 6. Real-Time Processing Events (SSE)

### `GET /events/invoice/{id}`
Streams Server-Sent Events (SSE) as each processing stage runs.
```
data: {"invoice_id": "...", "stage_name": "pdf_parsing", "status": "COMPLETED", "duration_ms": 25, "findings": {"method": "PDF"}}
data: {"invoice_id": "...", "stage_name": "field_extraction", "status": "COMPLETED", "duration_ms": 12}
...
data: {"event": "done", "status": "APPROVE"}
```
