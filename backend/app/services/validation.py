"""
Business-rule validation engine — evaluates 11 rules and returns RuleResult list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models.invoice import Invoice
from ..models.purchase_order import PurchaseOrder
from ..models.vendor import Vendor
from .matching import MatchResult


@dataclass
class RuleResult:
    rule_name: str
    passed: bool
    severity: str  # INFO | WARNING | ERROR | CRITICAL
    message: str
    details: dict = field(default_factory=dict)


class ValidationEngine:
    """
    Runs all 11 business rules against an extraction + match result pair.
    """

    def validate(
        self,
        extraction,
        match_result: MatchResult,
        db: Session,
        is_duplicate: bool = False,
        duplicate_of_id: Optional[str] = None,
    ) -> List[RuleResult]:
        results: List[RuleResult] = []

        results.append(self._check_vendor_approval(match_result.matched_vendor))
        results.append(self._check_mandatory_fields(extraction))
        results.append(self._check_duplicate(is_duplicate, duplicate_of_id))
        results.append(self._check_vendor_po_match(match_result))
        results.append(self._check_po_status(match_result.matched_po))
        results.append(self._check_amount_vs_po(extraction, match_result.matched_po))
        results.append(self._check_line_items(extraction, match_result.matched_po))
        results.append(self._check_tax_reconciliation(extraction))
        results.append(self._check_currency(extraction, match_result.matched_po))
        results.append(self._check_po_utilization(extraction, match_result.matched_po, db))
        results.append(self._check_date_consistency(extraction, match_result.matched_po))

        return results

    # ------------------------------------------------------------------
    # Individual rules
    # ------------------------------------------------------------------

    def _check_vendor_approval(self, vendor: Optional[Vendor]) -> RuleResult:
        if vendor is None:
            return RuleResult(
                "vendor_approval", False, "ERROR",
                "No matching vendor found in approved vendor list",
            )
        status = vendor.approval_status
        if status == "APPROVED":
            return RuleResult("vendor_approval", True, "INFO",
                              f"Vendor '{vendor.name}' is approved")
        elif status == "PENDING":
            return RuleResult("vendor_approval", False, "ERROR",
                              f"Vendor '{vendor.name}' is pending approval",
                              {"vendor_status": "PENDING"})
        elif status == "REJECTED":
            return RuleResult("vendor_approval", False, "CRITICAL",
                              f"Vendor '{vendor.name}' has been rejected — invoices cannot be processed",
                              {"vendor_status": "REJECTED"})
        elif status == "SUSPENDED":
            return RuleResult("vendor_approval", False, "CRITICAL",
                              f"Vendor '{vendor.name}' is suspended",
                              {"vendor_status": "SUSPENDED"})
        return RuleResult("vendor_approval", False, "ERROR",
                          f"Unknown vendor status: {status}")

    def _check_mandatory_fields(self, extraction) -> RuleResult:
        missing = []
        if not extraction.invoice_number:
            missing.append("invoice_number")
        if not extraction.invoice_date:
            missing.append("invoice_date")
        if not extraction.grand_total:
            missing.append("grand_total")
        if not extraction.vendor_name:
            missing.append("vendor_name")

        if not missing:
            return RuleResult("mandatory_fields", True, "INFO",
                              "All mandatory fields present")
        # invoice_date and vendor_name are important but non-fatal alone
        if set(missing) <= {"invoice_date", "vendor_name"}:
            return RuleResult("mandatory_fields", False, "WARNING",
                              f"Optional critical fields missing: {', '.join(missing)}",
                              {"missing_fields": missing})
        return RuleResult("mandatory_fields", False, "ERROR",
                          f"Required fields missing: {', '.join(missing)}",
                          {"missing_fields": missing})

    def _check_duplicate(self, is_duplicate: bool, duplicate_of_id: Optional[str]) -> RuleResult:
        if is_duplicate:
            return RuleResult("duplicate_detection", False, "CRITICAL",
                              "Duplicate invoice detected",
                              {"duplicate_of": duplicate_of_id})
        return RuleResult("duplicate_detection", True, "INFO", "No duplicate detected")

    def _check_vendor_po_match(self, match_result: MatchResult) -> RuleResult:
        if match_result.is_ambiguous:
            return RuleResult("vendor_po_match", False, "WARNING",
                              "Ambiguous vendor or PO match — requires human review",
                              {"match_method": match_result.match_method})
        if match_result.matched_po and match_result.matched_vendor:
            return RuleResult("vendor_po_match", True, "INFO",
                              f"Matched PO: {match_result.matched_po.po_number}",
                              {"po_confidence": match_result.po_confidence,
                               "vendor_confidence": match_result.vendor_confidence})
        if not match_result.matched_po:
            return RuleResult("vendor_po_match", False, "WARNING",
                              "No purchase order matched",
                              {"vendor_found": match_result.matched_vendor is not None})
        return RuleResult("vendor_po_match", False, "ERROR", "Match failed")

    def _check_po_status(self, po: Optional[PurchaseOrder]) -> RuleResult:
        if po is None:
            return RuleResult("po_status", False, "WARNING",
                              "No PO to validate status")
        if po.status in ("OPEN", "PARTIAL"):
            return RuleResult("po_status", True, "INFO",
                              f"PO {po.po_number} status: {po.status}")
        elif po.status == "CLOSED":
            return RuleResult("po_status", False, "CRITICAL",
                              f"PO {po.po_number} is CLOSED — no further invoices allowed")
        elif po.status == "CANCELLED":
            return RuleResult("po_status", False, "CRITICAL",
                              f"PO {po.po_number} has been CANCELLED")
        return RuleResult("po_status", False, "ERROR",
                          f"Unknown PO status: {po.status}")

    def _check_amount_vs_po(self, extraction, po: Optional[PurchaseOrder]) -> RuleResult:
        if po is None or extraction.grand_total is None:
            return RuleResult("amount_vs_po", False, "WARNING",
                              "Cannot validate amount — PO or invoice total missing")
        tolerance = settings.PRICE_TOLERANCE_PERCENT / 100
        diff = abs(extraction.grand_total - po.total_amount)
        diff_pct = diff / max(po.total_amount, 0.01)

        if extraction.grand_total <= po.total_amount * (1 + tolerance):
            return RuleResult("amount_vs_po", True, "INFO",
                              f"Invoice total ${extraction.grand_total:.2f} within PO amount ${po.total_amount:.2f}",
                              {"difference": diff, "difference_pct": round(diff_pct * 100, 2)})
        return RuleResult("amount_vs_po", False, "ERROR",
                          f"Invoice total ${extraction.grand_total:.2f} exceeds PO amount ${po.total_amount:.2f} "
                          f"by {diff_pct * 100:.1f}%",
                          {"difference": diff,
                           "difference_pct": round(diff_pct * 100, 2),
                           "tolerance_pct": settings.PRICE_TOLERANCE_PERCENT})

    def _check_line_items(self, extraction, po: Optional[PurchaseOrder]) -> RuleResult:
        line_items = getattr(extraction, "line_items", [])
        if not line_items:
            return RuleResult("line_item_check", True, "INFO",
                              "No line items to validate")
        item_sum = sum(getattr(item, "total_price", None) or 0 for item in line_items)
        if extraction.subtotal and item_sum > 0:
            diff = abs(item_sum - extraction.subtotal) / max(extraction.subtotal, 0.01)
            if diff > 0.05:
                return RuleResult("line_item_check", False, "WARNING",
                                  f"Line item sum ${item_sum:.2f} differs from subtotal ${extraction.subtotal:.2f}",
                                  {"item_sum": item_sum,
                                   "subtotal": extraction.subtotal,
                                   "diff_pct": round(diff * 100, 2)})
        return RuleResult("line_item_check", True, "INFO",
                          f"Line items check passed ({len(line_items)} items)")

    def _check_tax_reconciliation(self, extraction) -> RuleResult:
        if not extraction.grand_total:
            return RuleResult("tax_reconciliation", False, "WARNING",
                              "Cannot reconcile — grand total missing")
        if extraction.subtotal is None:
            return RuleResult("tax_reconciliation", False, "WARNING",
                              "Subtotal missing for reconciliation")

        computed = (
            (extraction.subtotal or 0)
            + (extraction.tax_amount or 0)
            - (extraction.discount_amount or 0)
            + (extraction.shipping_amount or 0)
        )
        diff = abs(computed - extraction.grand_total)

        if diff < 1.0:
            return RuleResult("tax_reconciliation", True, "INFO",
                              f"Totals reconcile: ${computed:.2f} = ${extraction.grand_total:.2f}")
        elif diff < extraction.grand_total * 0.02:
            return RuleResult("tax_reconciliation", False, "WARNING",
                              f"Minor reconciliation discrepancy: computed ${computed:.2f} vs stated ${extraction.grand_total:.2f}",
                              {"computed": computed, "stated": extraction.grand_total, "diff": diff})
        return RuleResult("tax_reconciliation", False, "ERROR",
                          f"Significant reconciliation error: computed ${computed:.2f} vs stated ${extraction.grand_total:.2f}",
                          {"computed": computed, "stated": extraction.grand_total, "diff": diff})

    def _check_currency(self, extraction, po: Optional[PurchaseOrder]) -> RuleResult:
        if po is None:
            return RuleResult("currency_check", True, "INFO",
                              "No PO currency to compare")
        inv_currency = getattr(extraction, "currency", "USD") or "USD"
        if inv_currency == po.currency:
            return RuleResult("currency_check", True, "INFO",
                              f"Currency matches: {inv_currency}")
        return RuleResult("currency_check", False, "ERROR",
                          f"Currency mismatch: invoice {inv_currency} vs PO {po.currency}")

    def _check_po_utilization(
        self, extraction, po: Optional[PurchaseOrder], db: Session
    ) -> RuleResult:
        if po is None or extraction.grand_total is None:
            return RuleResult("po_utilization", False, "WARNING",
                              "Cannot check PO utilization")
        new_total = po.utilized_amount + extraction.grand_total
        if new_total > po.total_amount:
            remaining = po.total_amount - po.utilized_amount
            return RuleResult("po_utilization", False, "CRITICAL",
                              f"Invoice would exceed PO budget. PO remaining: ${remaining:.2f}, invoice: ${extraction.grand_total:.2f}",
                              {"po_total": po.total_amount,
                               "utilized": po.utilized_amount,
                               "remaining": remaining,
                               "invoice_amount": extraction.grand_total})
        utilization_pct = new_total / po.total_amount * 100
        return RuleResult("po_utilization", True, "INFO",
                          f"PO utilization: {utilization_pct:.1f}% after this invoice",
                          {"po_total": po.total_amount,
                           "new_utilized": new_total,
                           "utilization_pct": round(utilization_pct, 2)})

    def _check_date_consistency(self, extraction, po: Optional[PurchaseOrder]) -> RuleResult:
        if not extraction.invoice_date:
            return RuleResult("date_consistency", False, "WARNING",
                              "Invoice date missing")

        if po and (po.expiry_date or po.issue_date):
            inv_date_str = extraction.invoice_date
            inv_date = None
            for fmt in [
                "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y",
                "%m/%d/%y", "%d/%m/%y",
                "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%d %B %Y",
            ]:
                try:
                    inv_date = datetime.strptime(inv_date_str, fmt).date()
                    break
                except ValueError:
                    continue

            if inv_date is None:
                return RuleResult("date_consistency", True, "INFO",
                                  "Date format unrecognized but proceeding")

            if po.expiry_date and inv_date > po.expiry_date:
                return RuleResult("date_consistency", False, "ERROR",
                                  f"Invoice date {inv_date} is after PO expiry {po.expiry_date}")
            if po.issue_date and inv_date < po.issue_date:
                return RuleResult("date_consistency", False, "WARNING",
                                  f"Invoice date {inv_date} is before PO issue date {po.issue_date}")

        return RuleResult("date_consistency", True, "INFO",
                          "Date consistency check passed")
