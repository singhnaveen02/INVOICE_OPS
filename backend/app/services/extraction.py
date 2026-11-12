import fitz  # PyMuPDF
import pdfplumber
import pytesseract
import cv2
import numpy as np
from PIL import Image
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from pathlib import Path
import hashlib
import io


@dataclass
class ExtractedLineItem:
    line_number: int
    description: Optional[str] = None
    sku: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total_price: Optional[float] = None
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    # Vendor info
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    # Invoice header
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: str = "USD"
    # Financials
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    shipping_amount: Optional[float] = None
    grand_total: Optional[float] = None
    # Line items
    line_items: List[ExtractedLineItem] = field(default_factory=list)
    # Metadata
    extraction_method: str = "PDF"
    overall_confidence: float = 0.0
    field_confidence: Dict[str, float] = field(default_factory=dict)
    raw_text: str = ""
    file_hash: str = ""


class InvoiceExtractor:
    def __init__(self):
        self._setup_patterns()

    def _setup_patterns(self):
        self.patterns = {
            "invoice_number": [
                r"\bInvoice\s*(?:Number|No\.?|#)\s*[:#\-\s]?\s*([A-Za-z0-9\-]+)",
                r"\bINV\s*[:#\-]\s*([A-Za-z0-9\-]+)",
                r"\bINV[\-_]([A-Za-z0-9\-]+)",
                r"\bBill\s*(?:Number|No\.?|#)\s*[:#\-\s]?\s*([A-Za-z0-9\-]+)",
                r"\bInvoice\s*:\s*([A-Za-z0-9\-]+)",
            ],
            "po_number": [
                r"\bPurchase\s*Order\s*(?:Number|No\.?|#)?\s*[:#\-\s]?\s*([A-Za-z0-9\-]+)",
                r"\bP\.?O\.?\s*(?:Number|No\.?|#)?\s*[:#\-\s]?\s*([A-Za-z0-9\-]+)",
                r"\bPO[\-_]([A-Za-z0-9\-]+)",
                r"\bOrder\s*No\.?\s*:?\s*([A-Za-z0-9\-]+)",
            ],
            "date": [
                r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
                r"(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
                r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})",
                r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})",
            ],
            "amount": [
                r"\$\s*([\d,]+\.?\d*)",
                r"USD\s*([\d,]+\.?\d*)",
                r"([\d,]+\.\d{2})\s*USD",
                r"€\s*([\d,]+\.?\d*)",
                r"£\s*([\d,]+\.?\d*)",
            ],
            "gstin": [
                r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b",
            ],
            "currency": [
                r"\b(USD|EUR|GBP|INR|CAD|AUD)\b",
                r"Currency:\s*([A-Z]{3})",
            ],
        }

    def extract(self, file_path: str, file_bytes: bytes = None) -> ExtractionResult:
        result = ExtractionResult()

        # Compute file hash
        if file_bytes:
            result.file_hash = hashlib.sha256(file_bytes).hexdigest()
        else:
            with open(file_path, "rb") as f:
                result.file_hash = hashlib.sha256(f.read()).hexdigest()

        # Try text extraction first
        text = self._extract_text_pymupdf(file_path)

        if len(text.strip()) < 50:
            # Likely scanned - try pdfplumber
            text = self._extract_text_pdfplumber(file_path)

        if len(text.strip()) < 50:
            # Still poor - use OCR
            text = self._extract_text_ocr(file_path)
            result.extraction_method = "OCR"
        else:
            result.extraction_method = "PDF"

        result.raw_text = text

        # Parse fields from text
        self._parse_fields(text, result)

        # Calculate overall confidence
        result.overall_confidence = self._calculate_confidence(result)

        return result

    def _extract_text_pymupdf(self, file_path: str) -> str:
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception:
            return ""

    def _extract_text_pdfplumber(self, file_path: str) -> str:
        try:
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    # Also try table extraction
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row:
                                text += " | ".join([str(c) if c else "" for c in row]) + "\n"
            return text
        except Exception:
            return ""

    def _extract_text_ocr(self, file_path: str) -> str:
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(file_path, dpi=300)
            text = ""
            for image in images:
                # Preprocess with OpenCV
                img_array = np.array(image)
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                # Denoise
                denoised = cv2.fastNlMeansDenoising(gray, h=10)
                # Threshold (Otsu)
                _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                # OCR
                pil_img = Image.fromarray(thresh)
                page_text = pytesseract.image_to_string(pil_img, config="--psm 6")
                text += page_text + "\n"
            return text
        except Exception:
            return ""

    def _parse_fields(self, text: str, result: ExtractionResult):
        # Invoice number
        for pattern in self.patterns["invoice_number"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result.invoice_number = match.group(1).strip()
                result.field_confidence["invoice_number"] = 0.9
                break

        # PO number
        for pattern in self.patterns["po_number"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result.po_number = match.group(1).strip()
                result.field_confidence["po_number"] = 0.9
                break

        # GSTIN
        for pattern in self.patterns["gstin"]:
            match = re.search(pattern, text)
            if match:
                result.vendor_gstin = match.group(1)
                result.field_confidence["vendor_gstin"] = 0.95
                break

        # Currency
        for pattern in self.patterns["currency"]:
            match = re.search(pattern, text)
            if match:
                result.currency = match.group(1)
                break

        # Dates - find invoice date and due date
        date_matches = []
        for pattern in self.patterns["date"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_matches.append(match.group(1))

        if date_matches:
            result.invoice_date = date_matches[0]
            result.field_confidence["invoice_date"] = 0.7
            if len(date_matches) > 1:
                result.due_date = date_matches[1]
                result.field_confidence["due_date"] = 0.6

        # Amounts - look for labeled amounts
        amount_patterns = [
            (r"\b(?:Sub[\s\-]?total)\b\s*:?\s*\$?\s*([\d,]+\.?\d*)", "subtotal"),
            (r"\b(?:Tax|GST|VAT|HST)\b\s*(?:\(\d+%\))?\s*:?\s*\$?\s*([\d,]+\.?\d*)", "tax_amount"),
            (r"\b(?:Discount)\b\s*:?\s*\$?\s*([\d,]+\.?\d*)", "discount_amount"),
            (r"\b(?:Shipping|Freight|Delivery)\b\s*:?\s*\$?\s*([\d,]+\.?\d*)", "shipping_amount"),
            (r"\b(?:Grand\s*Total|Invoice\s*Total|Amount\s*Due|Balance\s*Due|Total\s*Due|TOTAL\s*DUE)\b\s*:?\s*\$?\s*([\d,]+\.?\d*)", "grand_total"),
            (r"(?<!Sub)\bTotal\b\s*:?\s*\$?\s*([\d,]+\.?\d*)", "grand_total"),
        ]

        for pattern, field_name in amount_patterns:
            # If grand_total or other field already set by a more specific pattern, don't overwrite
            if getattr(result, field_name) is not None and field_name == "grand_total":
                continue
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1).replace(",", ""))
                    setattr(result, field_name, value)
                    result.field_confidence[field_name] = 0.85
                except ValueError:
                    pass

        # Vendor name - try to get from "From:", "Vendor:", or first line
        vendor_patterns = [
            r"(?:From|Vendor|Supplier|Bill\s*From)\s*:?\s*\n?\s*([A-Z][A-Za-z\s&,\.]+(?:Inc|Ltd|LLC|Corp|Co|GmbH)?\.?)",
            r"^([A-Z][A-Za-z\s&,\.]+(?:Inc|Ltd|LLC|Corp|Co|GmbH)?\.?)\s*$",
        ]
        for pattern in vendor_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                if len(name) > 3:
                    result.vendor_name = name
                    result.field_confidence["vendor_name"] = 0.7
                    break

        # Payment terms
        payment_patterns = [
            r"Payment\s*Terms?\s*:?\s*(Net\s*\d+|Due\s*on\s*receipt|Immediate)",
            r"Terms?\s*:?\s*(Net\s*\d+)",
        ]
        for pattern in payment_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result.payment_terms = match.group(1).strip()
                break

        # Line items - basic table parsing
        result.line_items = self._extract_line_items(text)

    def _extract_line_items(self, text: str) -> List[ExtractedLineItem]:
        items = []
        # Look for table-like structures with quantities and prices
        # Pattern: item description | qty | unit price | total
        line_pattern = re.compile(
            r"([A-Za-z][A-Za-z0-9\s\-/]+?)\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)",
            re.IGNORECASE,
        )

        line_num = 1
        for match in line_pattern.finditer(text):
            desc = match.group(1).strip()
            if len(desc) < 3:
                continue
            try:
                qty = float(match.group(2))
                unit_price = float(match.group(3).replace(",", ""))
                total = float(match.group(4).replace(",", ""))

                # Basic sanity check: qty * unit_price ≈ total (within 10%)
                if total > 0 and abs(qty * unit_price - total) / total < 0.1:
                    items.append(
                        ExtractedLineItem(
                            line_number=line_num,
                            description=desc,
                            quantity=qty,
                            unit_price=unit_price,
                            total_price=total,
                            confidence=0.8,
                        )
                    )
                    line_num += 1
            except (ValueError, ZeroDivisionError):
                pass

        return items

    def _calculate_confidence(self, result: ExtractionResult) -> float:
        critical_fields = ["invoice_number", "grand_total", "vendor_name"]
        important_fields = ["invoice_date", "subtotal", "po_number"]

        weighted_sum = 0.0
        total_weight = 0.0

        for f in critical_fields:
            val = getattr(result, f, None)
            total_weight += 1.0
            if val is not None:
                weighted_sum += result.field_confidence.get(f, 0.5) * 1.0

        for f in important_fields:
            val = getattr(result, f, None)
            total_weight += 0.5
            if val is not None:
                weighted_sum += result.field_confidence.get(f, 0.5) * 0.5

        return round(weighted_sum / total_weight, 3) if total_weight > 0 else 0.0
