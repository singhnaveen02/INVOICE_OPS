"""Seed the database with realistic vendors, purchase orders, and line items.

Run via:  python init_db.py   (which calls seed_database)
"""

import csv
import os
import uuid
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from ..models.vendor import Vendor
from ..models.purchase_order import PurchaseOrder, POLineItem

# ---------------------------------------------------------------------------
# Static seed data
# ---------------------------------------------------------------------------

VENDORS = [
    {
        "id": "v-acme-0001",
        "name": "Acme Corporation",
        "gstin": "22AAAAA0000A1Z5",
        "tax_id": "EIN-12-3456789",
        "email": "billing@acmecorp.com",
        "phone": "+1-800-555-0101",
        "address": "1 Acme Plaza, Phoenix, AZ 85001, USA",
        "country": "US",
        "approval_status": "APPROVED",
        "approved_by": "admin@invoiceops.com",
        "notes": "Long-standing strategic partner. Priority vendor.",
    },
    {
        "id": "v-tech-0002",
        "name": "TechSupplies Ltd",
        "gstin": None,
        "tax_id": "EIN-98-7654321",
        "email": "accounts@techsupplies.co.uk",
        "phone": "+44-20-7946-0123",
        "address": "42 Silicon Road, London, EC1A 1BB, UK",
        "country": "GB",
        "approval_status": "APPROVED",
        "approved_by": "admin@invoiceops.com",
        "notes": "UK-based hardware supplier. Preferred for server components.",
    },
    {
        "id": "v-glob-0003",
        "name": "Global Logistics Inc",
        "gstin": None,
        "tax_id": "EIN-55-4433221",
        "email": "invoices@globallogistics.com",
        "phone": "+1-312-555-0200",
        "address": "2500 Freight Blvd, Chicago, IL 60601, USA",
        "country": "US",
        "approval_status": "APPROVED",
        "approved_by": "finance@invoiceops.com",
        "notes": "Primary freight and logistics vendor.",
    },
    {
        "id": "v-ofce-0004",
        "name": "Office Essentials Co",
        "gstin": None,
        "tax_id": "EIN-77-1122334",
        "email": "billing@officeessentials.com",
        "phone": "+1-415-555-0330",
        "address": "900 Market St, San Francisco, CA 94103, USA",
        "country": "US",
        "approval_status": "APPROVED",
        "approved_by": "admin@invoiceops.com",
        "notes": "Office supplies and stationery.",
    },
    {
        "id": "v-clou-0005",
        "name": "CloudServices Pro",
        "gstin": None,
        "tax_id": "EIN-33-9988776",
        "email": "billing@cloudservicespro.io",
        "phone": "+1-737-555-0411",
        "address": "500 Cloud Ave, Austin, TX 78701, USA",
        "country": "US",
        "approval_status": "APPROVED",
        "approved_by": "cto@invoiceops.com",
        "notes": "Cloud infrastructure and SaaS tools.",
    },
    {
        "id": "v-mega-0006",
        "name": "MegaSupplier Corp",
        "gstin": "27BBBBB1111B2Z6",
        "tax_id": None,
        "email": "ar@megasupplier.in",
        "phone": "+91-22-5555-6666",
        "address": "Plot 7, MIDC, Andheri East, Mumbai, MH 400093, India",
        "country": "IN",
        "approval_status": "PENDING",
        "approved_by": None,
        "notes": "New vendor — awaiting compliance review.",
    },
    {
        "id": "v-qkpt-0007",
        "name": "QuickParts Inc",
        "gstin": None,
        "tax_id": "EIN-66-5544332",
        "email": "invoices@quickparts.com",
        "phone": "+1-313-555-0510",
        "address": "8800 Industrial Dr, Detroit, MI 48201, USA",
        "country": "US",
        "approval_status": "APPROVED",
        "approved_by": "ops@invoiceops.com",
        "notes": "Manufacturing components and spare parts.",
    },
    {
        "id": "v-data-0008",
        "name": "DataSystems LLC",
        "gstin": None,
        "tax_id": "EIN-44-3322110",
        "email": "finance@datasystems.net",
        "phone": "+1-206-555-0620",
        "address": "1200 Data Center Dr, Seattle, WA 98101, USA",
        "country": "US",
        "approval_status": "APPROVED",
        "approved_by": "cto@invoiceops.com",
        "notes": "Data integration and analytics services.",
    },
    {
        "id": "v-medi-0009",
        "name": "MediaCreations",
        "gstin": None,
        "tax_id": "EIN-11-2233445",
        "email": "billing@mediacreations.co",
        "phone": "+1-310-555-0730",
        "address": "7777 Sunset Blvd, Los Angeles, CA 90046, USA",
        "country": "US",
        "approval_status": "REJECTED",
        "approved_by": None,
        "notes": "Rejected: policy violation — unauthorized use of copyrighted materials.",
    },
    {
        "id": "v-secu-0010",
        "name": "SecureTech Solutions",
        "gstin": None,
        "tax_id": "EIN-22-1100998",
        "email": "accounts@securetech.com",
        "phone": "+1-571-555-0840",
        "address": "3000 Cyber Lane, Reston, VA 20191, USA",
        "country": "US",
        "approval_status": "SUSPENDED",
        "approved_by": "compliance@invoiceops.com",
        "notes": "Suspended pending investigation into overbilling incidents (Q1 2024).",
    },
]

# POs reference only APPROVED vendors
POS = [
    {
        "id": "po-2024-001",
        "po_number": "PO-2024-001",
        "vendor_id": "v-acme-0001",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 25000.00,
        "utilized_amount": 7500.00,
        "issue_date": date(2024, 1, 10),
        "expiry_date": date(2024, 12, 31),
        "payment_terms": "Net 30",
        "description": "Annual office furniture and fixtures supply",
    },
    {
        "id": "po-2024-002",
        "po_number": "PO-2024-002",
        "vendor_id": "v-tech-0002",
        "status": "PARTIAL",
        "currency": "USD",
        "total_amount": 48000.00,
        "utilized_amount": 32000.00,
        "issue_date": date(2024, 1, 15),
        "expiry_date": date(2024, 12, 31),
        "payment_terms": "Net 60",
        "description": "Server hardware refresh — Phase 1",
    },
    {
        "id": "po-2024-003",
        "po_number": "PO-2024-003",
        "vendor_id": "v-glob-0003",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 15000.00,
        "utilized_amount": 0.00,
        "issue_date": date(2024, 2, 1),
        "expiry_date": date(2024, 12, 31),
        "payment_terms": "Net 30",
        "description": "Q1-Q2 domestic freight services",
    },
    {
        "id": "po-2024-004",
        "po_number": "PO-2024-004",
        "vendor_id": "v-ofce-0004",
        "status": "CLOSED",
        "currency": "USD",
        "total_amount": 3500.00,
        "utilized_amount": 3500.00,
        "issue_date": date(2024, 1, 20),
        "expiry_date": date(2024, 3, 20),
        "payment_terms": "Net 15",
        "description": "Q1 office stationery and consumables",
    },
    {
        "id": "po-2024-005",
        "po_number": "PO-2024-005",
        "vendor_id": "v-clou-0005",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 36000.00,
        "utilized_amount": 9000.00,
        "issue_date": date(2024, 1, 1),
        "expiry_date": date(2024, 12, 31),
        "payment_terms": "Net 30",
        "description": "Annual cloud infrastructure subscription",
    },
    {
        "id": "po-2024-006",
        "po_number": "PO-2024-006",
        "vendor_id": "v-acme-0001",
        "status": "PARTIAL",
        "currency": "USD",
        "total_amount": 12000.00,
        "utilized_amount": 4800.00,
        "issue_date": date(2024, 2, 15),
        "expiry_date": date(2024, 8, 15),
        "payment_terms": "Net 30",
        "description": "Laboratory equipment and safety gear",
    },
    {
        "id": "po-2024-007",
        "po_number": "PO-2024-007",
        "vendor_id": "v-qkpt-0007",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 8500.00,
        "utilized_amount": 0.00,
        "issue_date": date(2024, 3, 1),
        "expiry_date": date(2024, 9, 1),
        "payment_terms": "Net 30",
        "description": "Assembly line spare parts — batch order",
    },
    {
        "id": "po-2024-008",
        "po_number": "PO-2024-008",
        "vendor_id": "v-data-0008",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 22000.00,
        "utilized_amount": 11000.00,
        "issue_date": date(2024, 2, 20),
        "expiry_date": date(2024, 8, 20),
        "payment_terms": "Net 60",
        "description": "Data migration and ETL services — Phase 2",
    },
    {
        "id": "po-2024-009",
        "po_number": "PO-2024-009",
        "vendor_id": "v-tech-0002",
        "status": "CLOSED",
        "currency": "USD",
        "total_amount": 6200.00,
        "utilized_amount": 6200.00,
        "issue_date": date(2024, 1, 25),
        "expiry_date": date(2024, 2, 28),
        "payment_terms": "Net 15",
        "description": "Networking switches and cabling",
    },
    {
        "id": "po-2024-010",
        "po_number": "PO-2024-010",
        "vendor_id": "v-glob-0003",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 9800.00,
        "utilized_amount": 2450.00,
        "issue_date": date(2024, 3, 10),
        "expiry_date": date(2024, 9, 10),
        "payment_terms": "Net 30",
        "description": "International shipping — Asia-Pacific routes",
    },
    {
        "id": "po-2024-011",
        "po_number": "PO-2024-011",
        "vendor_id": "v-clou-0005",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 14400.00,
        "utilized_amount": 3600.00,
        "issue_date": date(2024, 3, 1),
        "expiry_date": date(2024, 12, 31),
        "payment_terms": "Net 30",
        "description": "DevOps tooling and monitoring platform",
    },
    {
        "id": "po-2024-012",
        "po_number": "PO-2024-012",
        "vendor_id": "v-ofce-0004",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 2100.00,
        "utilized_amount": 700.00,
        "issue_date": date(2024, 3, 15),
        "expiry_date": date(2024, 6, 15),
        "payment_terms": "Net 15",
        "description": "Q2 breakroom supplies and coffee station",
    },
    {
        "id": "po-2024-013",
        "po_number": "PO-2024-013",
        "vendor_id": "v-qkpt-0007",
        "status": "PARTIAL",
        "currency": "USD",
        "total_amount": 18750.00,
        "utilized_amount": 6250.00,
        "issue_date": date(2024, 2, 10),
        "expiry_date": date(2024, 8, 10),
        "payment_terms": "Net 30",
        "description": "CNC machine parts and tooling inserts",
    },
    {
        "id": "po-2024-014",
        "po_number": "PO-2024-014",
        "vendor_id": "v-data-0008",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 50000.00,
        "utilized_amount": 10000.00,
        "issue_date": date(2024, 1, 5),
        "expiry_date": date(2025, 1, 5),
        "payment_terms": "Net 60",
        "description": "Enterprise data warehouse build-out — 12-month engagement",
    },
    {
        "id": "po-2024-015",
        "po_number": "PO-2024-015",
        "vendor_id": "v-acme-0001",
        "status": "OPEN",
        "currency": "USD",
        "total_amount": 5500.00,
        "utilized_amount": 1100.00,
        "issue_date": date(2024, 3, 20),
        "expiry_date": date(2024, 9, 20),
        "payment_terms": "Net 30",
        "description": "Safety equipment and PPE for factory floor",
    },
]

PO_LINE_ITEMS = {
    "po-2024-001": [
        {"line_number": 1, "description": "Executive Desk (L-shape, walnut finish)", "sku": "DESK-EXC-WN-001", "quantity": 5, "unit_price": 1200.00, "unit_of_measure": "EA"},
        {"line_number": 2, "description": "Ergonomic Office Chair (mesh, adjustable)", "sku": "CHAIR-ERG-MSH-002", "quantity": 10, "unit_price": 450.00, "unit_of_measure": "EA"},
        {"line_number": 3, "description": "4-Drawer Filing Cabinet (letter size)", "sku": "CAB-FILE-4D-003", "quantity": 8, "unit_price": 320.00, "unit_of_measure": "EA"},
        {"line_number": 4, "description": "Whiteboard (6ft x 4ft, magnetic)", "sku": "WB-MAG-6X4-004", "quantity": 4, "unit_price": 180.00, "unit_of_measure": "EA"},
    ],
    "po-2024-002": [
        {"line_number": 1, "description": "Dell PowerEdge R750 Server", "sku": "SRV-DELL-R750-001", "quantity": 4, "unit_price": 6500.00, "unit_of_measure": "EA"},
        {"line_number": 2, "description": "32GB DDR4 ECC RAM Module", "sku": "RAM-DDR4-32G-002", "quantity": 32, "unit_price": 180.00, "unit_of_measure": "EA"},
        {"line_number": 3, "description": "2TB NVMe SSD (data center grade)", "sku": "SSD-NVM-2T-003", "quantity": 16, "unit_price": 320.00, "unit_of_measure": "EA"},
        {"line_number": 4, "description": "10GbE Network Interface Card", "sku": "NIC-10G-PCIe-004", "quantity": 8, "unit_price": 150.00, "unit_of_measure": "EA"},
        {"line_number": 5, "description": "Server Rack Installation Labor", "sku": "SVC-RACK-INST-005", "quantity": 1, "unit_price": 2000.00, "unit_of_measure": "HR"},
    ],
    "po-2024-003": [
        {"line_number": 1, "description": "LTL Freight — Midwest Region (per pallet)", "sku": "FRGT-LTL-MW-001", "quantity": 50, "unit_price": 180.00, "unit_of_measure": "PLT"},
        {"line_number": 2, "description": "Expedited Ground Shipping — Priority", "sku": "SHIP-EXP-GND-002", "quantity": 20, "unit_price": 75.00, "unit_of_measure": "SHP"},
        {"line_number": 3, "description": "Warehousing and Storage (monthly)", "sku": "WHSE-STG-MO-003", "quantity": 3, "unit_price": 2000.00, "unit_of_measure": "MO"},
    ],
    "po-2024-004": [
        {"line_number": 1, "description": "A4 Copy Paper (500 sheets/ream)", "sku": "PPR-A4-500-001", "quantity": 100, "unit_price": 8.50, "unit_of_measure": "RM"},
        {"line_number": 2, "description": "Ballpoint Pens (box of 50, blue)", "sku": "PEN-BP-BX50-002", "quantity": 20, "unit_price": 12.00, "unit_of_measure": "BX"},
        {"line_number": 3, "description": "Stapler (heavy duty, 60-sheet)", "sku": "STG-HD-60-003", "quantity": 10, "unit_price": 25.00, "unit_of_measure": "EA"},
        {"line_number": 4, "description": "Sticky Notes (3x3, 12-pack)", "sku": "STK-3X3-12P-004", "quantity": 30, "unit_price": 9.00, "unit_of_measure": "PK"},
        {"line_number": 5, "description": "Whiteboard Markers (assorted, 8-pack)", "sku": "MRK-WB-8PK-005", "quantity": 15, "unit_price": 14.00, "unit_of_measure": "PK"},
    ],
    "po-2024-005": [
        {"line_number": 1, "description": "Cloud Compute — 32 vCPU Reserved Instance (annual)", "sku": "CLD-CPU-32-ANN-001", "quantity": 1, "unit_price": 18000.00, "unit_of_measure": "LIC"},
        {"line_number": 2, "description": "Managed Kubernetes (10-node cluster, annual)", "sku": "CLD-K8S-10N-ANN-002", "quantity": 1, "unit_price": 12000.00, "unit_of_measure": "LIC"},
        {"line_number": 3, "description": "Object Storage — 50TB (annual)", "sku": "CLD-OBJ-50T-ANN-003", "quantity": 1, "unit_price": 6000.00, "unit_of_measure": "LIC"},
    ],
    "po-2024-006": [
        {"line_number": 1, "description": "Safety Goggles (ANSI Z87.1 rated)", "sku": "SFTY-GOG-Z87-001", "quantity": 50, "unit_price": 18.00, "unit_of_measure": "EA"},
        {"line_number": 2, "description": "Lab Coat (medium, autoclave-safe)", "sku": "COAT-LAB-MED-002", "quantity": 30, "unit_price": 45.00, "unit_of_measure": "EA"},
        {"line_number": 3, "description": "Digital Caliper (0–150mm, ±0.02mm)", "sku": "TOOL-CAL-150-003", "quantity": 10, "unit_price": 85.00, "unit_of_measure": "EA"},
        {"line_number": 4, "description": "Fume Hood (benchtop, 36-inch)", "sku": "EQUIP-FUME-36-004", "quantity": 2, "unit_price": 2250.00, "unit_of_measure": "EA"},
    ],
    "po-2024-007": [
        {"line_number": 1, "description": "M6 x 20mm Hex Bolts (grade 8.8, pack of 500)", "sku": "BOLT-M6X20-G8-001", "quantity": 10, "unit_price": 32.00, "unit_of_measure": "PK"},
        {"line_number": 2, "description": "Bearing — Deep Groove 6205-2RS", "sku": "BEAR-6205-2RS-002", "quantity": 50, "unit_price": 12.50, "unit_of_measure": "EA"},
        {"line_number": 3, "description": "Timing Belt (HTD 5M, 500mm)", "sku": "BELT-HTD5M-500-003", "quantity": 20, "unit_price": 22.00, "unit_of_measure": "EA"},
        {"line_number": 4, "description": "V-Belt (A-Section, A56)", "sku": "BELT-VA56-004", "quantity": 15, "unit_price": 18.00, "unit_of_measure": "EA"},
    ],
    "po-2024-008": [
        {"line_number": 1, "description": "Data Assessment and Schema Analysis", "sku": "SVC-DATA-ASSESS-001", "quantity": 40, "unit_price": 150.00, "unit_of_measure": "HR"},
        {"line_number": 2, "description": "ETL Pipeline Development", "sku": "SVC-ETL-DEV-002", "quantity": 80, "unit_price": 175.00, "unit_of_measure": "HR"},
        {"line_number": 3, "description": "Data Quality & Validation Framework", "sku": "SVC-DQ-FRMWK-003", "quantity": 30, "unit_price": 160.00, "unit_of_measure": "HR"},
    ],
    "po-2024-009": [
        {"line_number": 1, "description": "Cisco Catalyst 2960-X 48-Port Switch", "sku": "NET-CSC-2960X-001", "quantity": 4, "unit_price": 1050.00, "unit_of_measure": "EA"},
        {"line_number": 2, "description": "Cat6A Ethernet Cable (1000ft spool)", "sku": "CBL-CAT6A-1KFT-002", "quantity": 2, "unit_price": 320.00, "unit_of_measure": "SPL"},
        {"line_number": 3, "description": "19-inch Patch Panel (24-port, Cat6A)", "sku": "NET-PATCH-24-003", "quantity": 4, "unit_price": 95.00, "unit_of_measure": "EA"},
    ],
    "po-2024-010": [
        {"line_number": 1, "description": "Air Freight — Asia-Pacific (per kg rate)", "sku": "FRGT-AIR-APAC-001", "quantity": 500, "unit_price": 8.50, "unit_of_measure": "KG"},
        {"line_number": 2, "description": "Customs Brokerage Fee (per shipment)", "sku": "SVC-CUST-BRK-002", "quantity": 10, "unit_price": 230.00, "unit_of_measure": "SHP"},
    ],
    "po-2024-011": [
        {"line_number": 1, "description": "CI/CD Platform — Jenkins Enterprise (annual)", "sku": "SFT-CICD-JNK-ANN-001", "quantity": 1, "unit_price": 5400.00, "unit_of_measure": "LIC"},
        {"line_number": 2, "description": "Observability Stack — Datadog (annual, 20 hosts)", "sku": "SFT-OBS-DD-20H-002", "quantity": 1, "unit_price": 7200.00, "unit_of_measure": "LIC"},
        {"line_number": 3, "description": "Incident Management — PagerDuty Business (annual)", "sku": "SFT-INC-PD-BIZ-003", "quantity": 1, "unit_price": 1800.00, "unit_of_measure": "LIC"},
    ],
    "po-2024-012": [
        {"line_number": 1, "description": "Ground Coffee Beans — Colombian (5lb bag)", "sku": "CAFE-COLO-5LB-001", "quantity": 10, "unit_price": 55.00, "unit_of_measure": "BG"},
        {"line_number": 2, "description": "Paper Cups (12oz, case of 1000)", "sku": "CUP-12OZ-1K-002", "quantity": 5, "unit_price": 48.00, "unit_of_measure": "CS"},
        {"line_number": 3, "description": "Dish Soap and Cleaning Supplies Kit", "sku": "CLN-DISH-KIT-003", "quantity": 6, "unit_price": 32.00, "unit_of_measure": "KT"},
    ],
    "po-2024-013": [
        {"line_number": 1, "description": "CNC Turning Insert CNMG 120408 (box of 10)", "sku": "CNC-INS-CNMG-001", "quantity": 20, "unit_price": 185.00, "unit_of_measure": "BX"},
        {"line_number": 2, "description": "End Mill — 10mm 4-Flute Carbide", "sku": "CNC-EM-10MM-4F-002", "quantity": 30, "unit_price": 48.00, "unit_of_measure": "EA"},
        {"line_number": 3, "description": "Collet Chuck ER32 (C40, 100L)", "sku": "CNC-COL-ER32-003", "quantity": 5, "unit_price": 220.00, "unit_of_measure": "EA"},
        {"line_number": 4, "description": "CNC Machine Coolant (20L drum)", "sku": "CNC-CLT-20L-004", "quantity": 10, "unit_price": 95.00, "unit_of_measure": "DR"},
    ],
    "po-2024-014": [
        {"line_number": 1, "description": "Data Warehouse Architecture Design", "sku": "SVC-DWH-ARCH-001", "quantity": 60, "unit_price": 220.00, "unit_of_measure": "HR"},
        {"line_number": 2, "description": "BigQuery Setup and Optimization", "sku": "SVC-BQ-SETUP-002", "quantity": 80, "unit_price": 195.00, "unit_of_measure": "HR"},
        {"line_number": 3, "description": "dbt Model Development (100+ models)", "sku": "SVC-DBT-DEV-003", "quantity": 120, "unit_price": 185.00, "unit_of_measure": "HR"},
        {"line_number": 4, "description": "Looker Dashboard Development (10 dashboards)", "sku": "SVC-LKR-DASH-004", "quantity": 40, "unit_price": 175.00, "unit_of_measure": "HR"},
        {"line_number": 5, "description": "Training and Knowledge Transfer", "sku": "SVC-KT-TRAIN-005", "quantity": 20, "unit_price": 150.00, "unit_of_measure": "HR"},
    ],
    "po-2024-015": [
        {"line_number": 1, "description": "Hard Hat (ABS, Class E, yellow)", "sku": "PPE-HAT-CLE-001", "quantity": 25, "unit_price": 32.00, "unit_of_measure": "EA"},
        {"line_number": 2, "description": "Safety Vest (class 2, hi-vis orange)", "sku": "PPE-VEST-C2-002", "quantity": 25, "unit_price": 18.00, "unit_of_measure": "EA"},
        {"line_number": 3, "description": "Steel-Toe Work Boots (size 9–13 assorted)", "sku": "PPE-BOOT-ST-003", "quantity": 20, "unit_price": 95.00, "unit_of_measure": "PR"},
        {"line_number": 4, "description": "Cut-Resistant Gloves (level D, medium)", "sku": "PPE-GLOVE-CRD-004", "quantity": 50, "unit_price": 14.00, "unit_of_measure": "PR"},
    ],
}


def _make_vendor(data: dict) -> Vendor:
    v = Vendor()
    v.id = data["id"]
    v.name = data["name"]
    v.gstin = data.get("gstin")
    v.tax_id = data.get("tax_id")
    v.email = data.get("email")
    v.phone = data.get("phone")
    v.address = data.get("address")
    v.country = data.get("country", "US")
    v.approval_status = data["approval_status"]
    v.approved_by = data.get("approved_by")
    v.notes = data.get("notes")
    return v


def _make_po(data: dict) -> PurchaseOrder:
    po = PurchaseOrder()
    po.id = data["id"]
    po.po_number = data["po_number"]
    po.vendor_id = data["vendor_id"]
    po.status = data["status"]
    po.currency = data.get("currency", "USD")
    po.total_amount = data["total_amount"]
    po.utilized_amount = data.get("utilized_amount", 0.0)
    po.remaining_amount = round(data["total_amount"] - data.get("utilized_amount", 0.0), 2)
    po.issue_date = data["issue_date"]
    po.expiry_date = data.get("expiry_date")
    po.payment_terms = data.get("payment_terms")
    po.description = data.get("description")
    return po


def _make_line_item(po_id: str, item: dict) -> POLineItem:
    li = POLineItem()
    li.id = str(uuid.uuid4())
    li.po_id = po_id
    li.line_number = item["line_number"]
    li.description = item["description"]
    li.sku = item.get("sku")
    li.quantity = float(item["quantity"])
    li.unit_price = float(item["unit_price"])
    li.total_price = round(li.quantity * li.unit_price, 2)
    li.unit_of_measure = item.get("unit_of_measure", "EA")
    return li


def seed_database(db: Session) -> None:
    """Idempotently seed vendors, POs, and PO line items."""
    # --- Vendors ---
    existing_vendors = {v.id for v in db.query(Vendor.id).all()}  # type: ignore[arg-type]
    new_vendors = []
    for vdata in VENDORS:
        if vdata["id"] not in existing_vendors:
            new_vendors.append(_make_vendor(vdata))
    if new_vendors:
        db.add_all(new_vendors)
        db.commit()
        print(f"  Seeded {len(new_vendors)} vendor(s).")
    else:
        print("  Vendors already seeded.")

    # --- Purchase Orders ---
    existing_pos = {p.id for p in db.query(PurchaseOrder.id).all()}  # type: ignore[arg-type]
    new_pos = []
    for pdata in POS:
        if pdata["id"] not in existing_pos:
            new_pos.append(_make_po(pdata))
    if new_pos:
        db.add_all(new_pos)
        db.commit()
        print(f"  Seeded {len(new_pos)} purchase order(s).")
    else:
        print("  Purchase orders already seeded.")

    # --- PO Line Items ---
    from ..models.purchase_order import POLineItem as PLI  # local import to avoid circulars
    existing_li_po_ids = {r[0] for r in db.query(PLI.po_id).all()}
    new_items = []
    for po_id, items in PO_LINE_ITEMS.items():
        if po_id not in existing_li_po_ids:
            for item in items:
                new_items.append(_make_line_item(po_id, item))
    if new_items:
        db.add_all(new_items)
        db.commit()
        print(f"  Seeded {len(new_items)} PO line item(s).")
    else:
        print("  PO line items already seeded.")

    # --- Generate CSV files ---
    _write_csvs()


def _write_csvs() -> None:
    """Write sample CSV files to backend/sample_data/."""
    base = Path(__file__).resolve().parents[3] / "sample_data"
    base.mkdir(parents=True, exist_ok=True)

    # vendors.csv
    vendor_path = base / "vendors.csv"
    with open(vendor_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "name", "gstin", "tax_id", "email", "phone", "address", "country", "approval_status"],
        )
        writer.writeheader()
        for v in VENDORS:
            writer.writerow(
                {
                    "id": v["id"],
                    "name": v["name"],
                    "gstin": v.get("gstin", ""),
                    "tax_id": v.get("tax_id", ""),
                    "email": v.get("email", ""),
                    "phone": v.get("phone", ""),
                    "address": v.get("address", ""),
                    "country": v.get("country", "US"),
                    "approval_status": v["approval_status"],
                }
            )

    # purchase_orders.csv
    po_path = base / "purchase_orders.csv"
    vendor_lookup = {v["id"]: v["name"] for v in VENDORS}
    with open(po_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id", "po_number", "vendor_id", "vendor_name", "status", "currency",
                "total_amount", "utilized_amount", "issue_date", "expiry_date", "payment_terms", "description",
            ],
        )
        writer.writeheader()
        for p in POS:
            writer.writerow(
                {
                    "id": p["id"],
                    "po_number": p["po_number"],
                    "vendor_id": p["vendor_id"],
                    "vendor_name": vendor_lookup.get(p["vendor_id"], ""),
                    "status": p["status"],
                    "currency": p.get("currency", "USD"),
                    "total_amount": p["total_amount"],
                    "utilized_amount": p.get("utilized_amount", 0.0),
                    "issue_date": p["issue_date"].isoformat(),
                    "expiry_date": p["expiry_date"].isoformat() if p.get("expiry_date") else "",
                    "payment_terms": p.get("payment_terms", ""),
                    "description": p.get("description", ""),
                }
            )

    # po_line_items.csv
    li_path = base / "po_line_items.csv"
    po_lookup = {p["id"]: p["po_number"] for p in POS}
    with open(li_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id", "po_id", "po_number", "line_number", "description",
                "sku", "quantity", "unit_price", "total_price", "unit_of_measure",
            ],
        )
        writer.writeheader()
        for po_id, items in PO_LINE_ITEMS.items():
            for item in items:
                total = round(float(item["quantity"]) * float(item["unit_price"]), 2)
                writer.writerow(
                    {
                        "id": str(uuid.uuid4()),
                        "po_id": po_id,
                        "po_number": po_lookup.get(po_id, ""),
                        "line_number": item["line_number"],
                        "description": item["description"],
                        "sku": item.get("sku", ""),
                        "quantity": item["quantity"],
                        "unit_price": item["unit_price"],
                        "total_price": total,
                        "unit_of_measure": item.get("unit_of_measure", "EA"),
                    }
                )

    print(f"  CSV files written to: {base}")
