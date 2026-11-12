"""
Decision engine — maps validation results to APPROVED / REVIEW / REJECTED.
Status values use past tense to match Invoice.status column conventions.
"""
from __future__ import annotations

from typing import List

from .validation import RuleResult


class DecisionEngine:
    """
    Deterministic decision logic based on validation rule results and
    extraction confidence.
    """

    def decide(
        self,
        validation_results: List[RuleResult],
        extraction_confidence: float,
    ) -> dict:
        """
        Returns a dict with:
          decision         — "APPROVED" | "REVIEW" | "REJECTED"
          confidence_score — 0–1
          primary_reason   — single sentence
          explanation      — ordered list of human-readable lines
          discrepancies    — list of {rule, severity, message, details}
        """
        critical_failures = [r for r in validation_results if not r.passed and r.severity == "CRITICAL"]
        errors = [r for r in validation_results if not r.passed and r.severity == "ERROR"]
        warnings = [r for r in validation_results if not r.passed and r.severity == "WARNING"]

        explanation: List[str] = []
        discrepancies: List[dict] = []

        for rule in critical_failures:
            explanation.append(f"❌ CRITICAL: {rule.message}")
            discrepancies.append(
                {"rule": rule.rule_name, "severity": "CRITICAL",
                 "message": rule.message, "details": rule.details}
            )

        for rule in errors:
            explanation.append(f"⚠️ ERROR: {rule.message}")
            discrepancies.append(
                {"rule": rule.rule_name, "severity": "ERROR",
                 "message": rule.message, "details": rule.details}
            )

        for rule in warnings:
            explanation.append(f"ℹ️ WARNING: {rule.message}")
            discrepancies.append(
                {"rule": rule.rule_name, "severity": "WARNING",
                 "message": rule.message, "details": rule.details}
            )

        for rule in [r for r in validation_results if r.passed]:
            explanation.append(f"✅ {rule.message}")

        # --- Hard REJECT ---
        if critical_failures:
            reject_rules = {r.rule_name for r in critical_failures}
            if "duplicate_detection" in reject_rules:
                primary = "Duplicate invoice submission rejected"
            elif "vendor_approval" in reject_rules:
                primary = "Vendor not approved for payment processing"
            elif "po_status" in reject_rules:
                primary = "Purchase order is closed or cancelled"
            elif "po_utilization" in reject_rules:
                primary = "Invoice would exceed approved PO budget"
            else:
                primary = critical_failures[0].message

            return {
                "decision": "REJECTED",
                "confidence_score": 0.95,
                "primary_reason": primary,
                "explanation": explanation,
                "discrepancies": discrepancies,
            }

        # --- REVIEW conditions ---
        review_triggers: List[str] = []

        if extraction_confidence < 0.5:
            review_triggers.append("Low extraction confidence — manual verification required")

        mandatory = next(
            (r for r in validation_results if r.rule_name == "mandatory_fields"), None
        )
        if mandatory and not mandatory.passed and mandatory.severity in ("ERROR", "WARNING"):
            review_triggers.append("Missing critical invoice fields")

        vendor_po = next(
            (r for r in validation_results if r.rule_name == "vendor_po_match"), None
        )
        if vendor_po and not vendor_po.passed:
            review_triggers.append("Vendor or PO could not be reliably matched")

        if errors:
            rule_names = ", ".join(r.rule_name for r in errors)
            review_triggers.append(f"Validation errors require review: {rule_names}")

        if warnings:
            rule_names = ", ".join(r.rule_name for r in warnings)
            review_triggers.append(f"Warnings flagged: {rule_names}")

        if review_triggers:
            return {
                "decision": "REVIEW",
                "confidence_score": 0.6,
                "primary_reason": review_triggers[0],
                "explanation": explanation,
                "discrepancies": discrepancies,
            }

        # --- APPROVE ---
        passed_count = sum(1 for r in validation_results if r.passed)
        total_count = len(validation_results)

        return {
            "decision": "APPROVED",
            "confidence_score": min(0.95, extraction_confidence * 1.1),
            "primary_reason": f"All {passed_count}/{total_count} validation checks passed",
            "explanation": explanation,
            "discrepancies": discrepancies,
        }
