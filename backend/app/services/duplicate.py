"""
Duplicate detection service using multiple fingerprinting strategies.
"""
import hashlib
import re
import uuid
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from ..models.duplicate import DuplicateFingerprint


class DuplicateDetector:
    def compute_fingerprints(
        self,
        file_bytes: bytes,
        vendor_name: Optional[str],
        invoice_number: Optional[str],
        grand_total: Optional[float],
    ) -> dict:
        """Compute all fingerprints for a given invoice."""
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        # Normalized key: lowercase, no spaces/special chars
        key_parts = []
        if vendor_name:
            key_parts.append(re.sub(r"[^a-z0-9]", "", vendor_name.lower()))
        if invoice_number:
            key_parts.append(re.sub(r"[^a-z0-9]", "", invoice_number.lower()))
        normalized_key = "|".join(key_parts)
        normalized_hash = (
            hashlib.sha256(normalized_key.encode()).hexdigest() if key_parts else None
        )

        vendor_invoice_key = normalized_key

        amount_hash = None
        if grand_total is not None and invoice_number:
            amount_str = f"{invoice_number}|{grand_total:.2f}"
            amount_hash = hashlib.sha256(amount_str.encode()).hexdigest()

        return {
            "content_hash": content_hash,
            "normalized_hash": normalized_hash,
            "vendor_invoice_key": vendor_invoice_key,
            "amount_hash": amount_hash,
        }

    def check_duplicate(
        self,
        db: Session,
        fingerprints: dict,
        exclude_invoice_id: str = None,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Returns (is_duplicate, duplicate_of_id, reason).
        Checks content hash first (exact duplicate), then normalized vendor+invoice key.
        """
        query = db.query(DuplicateFingerprint)
        if exclude_invoice_id:
            query = query.filter(DuplicateFingerprint.invoice_id != exclude_invoice_id)

        # Check content hash first (exact binary duplicate)
        if fingerprints.get("content_hash"):
            existing = query.filter(
                DuplicateFingerprint.content_hash == fingerprints["content_hash"]
            ).first()
            if existing:
                return True, existing.invoice_id, "Exact PDF content match"

        # Check normalized vendor+invoice key (same invoice resubmitted with tweaks)
        if fingerprints.get("normalized_hash") and fingerprints.get("vendor_invoice_key"):
            existing = query.filter(
                DuplicateFingerprint.normalized_hash == fingerprints["normalized_hash"],
                DuplicateFingerprint.vendor_invoice_key != "",
            ).first()
            if existing:
                return (
                    True,
                    existing.invoice_id,
                    "Same vendor + invoice number combination",
                )

        return False, None, ""

    def save_fingerprint(self, db: Session, invoice_id: str, fingerprints: dict) -> DuplicateFingerprint:
        """Persist the fingerprint record for future duplicate checks."""
        fp = DuplicateFingerprint(
            id=str(uuid.uuid4()),
            invoice_id=invoice_id,
            content_hash=fingerprints.get("content_hash", ""),
            normalized_hash=fingerprints.get("normalized_hash", ""),
            vendor_invoice_key=fingerprints.get("vendor_invoice_key", ""),
            amount_hash=fingerprints.get("amount_hash"),
        )
        db.add(fp)
        db.commit()
        return fp
