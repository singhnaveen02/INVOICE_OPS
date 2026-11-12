"""
Multi-stage PO and vendor matching engine using exact and fuzzy strategies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from ..models.purchase_order import PurchaseOrder
from ..models.vendor import Vendor
from ..config import settings


@dataclass
class MatchResult:
    matched_vendor: Optional[Vendor] = None
    matched_po: Optional[PurchaseOrder] = None
    vendor_confidence: float = 0.0
    po_confidence: float = 0.0
    match_method: str = "none"
    is_ambiguous: bool = False
    candidate_vendors: list = field(default_factory=list)
    candidate_pos: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def normalize_company_name(name: str) -> str:
    """Normalizes company suffixes for better fuzzy matching."""
    s = name.lower()
    s = re.sub(r"\bcorp\.?\b", "corporation", s)
    s = re.sub(r"\binc\.?\b", "incorporated", s)
    s = re.sub(r"\bltd\.?\b", "limited", s)
    s = re.sub(r"\bco\.?\b", "company", s)
    s = re.sub(r"[^\w\s]", "", s)
    return " ".join(s.split())


class POMatchingEngine:
    """
    Three-stage matching:
    1. Exact PO number lookup
    2. Vendor matching (GSTIN/tax_id exact -> fuzzy name)
    3. PO matching within vendor (fuzzy PO# -> amount+date heuristic)
    """

    def match(self, db: Session, extraction) -> MatchResult:
        result = MatchResult()

        # --- Stage 1: Exact PO number ---
        if extraction.po_number:
            po = (
                db.query(PurchaseOrder)
                .filter(PurchaseOrder.po_number == extraction.po_number)
                .first()
            )
            if po:
                result.matched_po = po
                result.po_confidence = 1.0
                result.match_method = "exact_po"
                # Carry the vendor from the PO
                result.matched_vendor = po.vendor
                result.vendor_confidence = 0.95
                return result

        # --- Stage 2: Vendor matching ---
        vendors = db.query(Vendor).all()
        vendor_match = self._match_vendor(extraction, vendors)
        if vendor_match:
            result.matched_vendor, result.vendor_confidence = vendor_match

        # --- Stage 3: PO matching within matched vendor ---
        if result.matched_vendor:
            pos = (
                db.query(PurchaseOrder)
                .filter(PurchaseOrder.vendor_id == result.matched_vendor.id)
                .all()
            )
            po_match = self._match_po(extraction, pos)
            if po_match:
                result.matched_po, result.po_confidence, result.match_method = po_match

        # Flag ambiguous / unmatched cases
        if not result.matched_vendor or result.vendor_confidence < 0.8:
            result.is_ambiguous = True
        if not result.matched_po or result.po_confidence < 0.8:
            result.is_ambiguous = True

        # Reject low-confidence PO matches outright
        if result.matched_po and result.po_confidence < 0.5:
            result.matched_po = None
            result.po_confidence = 0.0
            result.warnings.append("PO match confidence too low - routing to review")

        return result

    def _match_vendor(
        self, extraction, vendors: List[Vendor]
    ) -> Optional[Tuple[Vendor, float]]:
        if not vendors:
            return None
        if (
            not extraction.vendor_name
            and not extraction.vendor_gstin
            and not extraction.vendor_tax_id
        ):
            return None

        # Exact GSTIN match
        if extraction.vendor_gstin:
            for v in vendors:
                if v.gstin and v.gstin.strip().lower() == extraction.vendor_gstin.strip().lower():
                    return (v, 1.0)

        # Exact tax_id match
        if extraction.vendor_tax_id:
            for v in vendors:
                if v.tax_id and v.tax_id.strip().lower() == extraction.vendor_tax_id.strip().lower():
                    return (v, 1.0)

        # Fuzzy name match with token_set_ratio & normalization
        if extraction.vendor_name:
            query_norm = normalize_company_name(extraction.vendor_name)
            vendor_map = {normalize_company_name(v.name): v for v in vendors}

            matches = process.extract(
                query_norm,
                list(vendor_map.keys()),
                scorer=fuzz.token_set_ratio,
                limit=3,
            )

            if matches and matches[0][1] >= 75:  # threshold
                best_name, best_score, _ = matches[0]
                confidence = best_score / 100.0

                # Flag ambiguity when second candidate is very close
                if (
                    len(matches) > 1
                    and matches[1][1] >= 75
                    and abs(matches[0][1] - matches[1][1]) < 8
                ):
                    confidence = confidence * 0.7  # reduce confidence for close candidates

                return (vendor_map[best_name], confidence)

        return None

    def _match_po(
        self, extraction, pos: List[PurchaseOrder]
    ) -> Optional[Tuple[PurchaseOrder, float, str]]:
        if not pos:
            return None

        # Fuzzy PO number match
        if extraction.po_number:
            po_numbers = {po.po_number: po for po in pos}
            matches = process.extract(
                extraction.po_number,
                list(po_numbers.keys()),
                scorer=fuzz.ratio,
                limit=3,
            )
            if matches and matches[0][1] >= 85:
                matched_po = po_numbers[matches[0][0]]
                return (matched_po, matches[0][1] / 100.0, "fuzzy_po")

        # Amount heuristic (only if exactly 1 open PO for this vendor and amount matches closely)
        if extraction.grand_total and len(pos) == 1:
            po = pos[0]
            if po.total_amount > 0:
                diff_pct = abs(po.total_amount - extraction.grand_total) / po.total_amount
                if diff_pct < 0.05:  # within 5%
                    return (po, 0.65, "amount_single_po")

        return None
