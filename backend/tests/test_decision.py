import pytest
from app.services.decision import DecisionEngine
from app.services.validation import RuleResult


@pytest.fixture
def engine():
    return DecisionEngine()


def test_decision_approve_all_pass(engine):
    rules = [
        RuleResult("vendor_approval", True, "INFO", "Vendor is approved"),
        RuleResult("mandatory_fields", True, "INFO", "All mandatory fields present"),
        RuleResult("duplicate_detection", True, "INFO", "No duplicate"),
        RuleResult("vendor_po_match", True, "INFO", "PO matched"),
        RuleResult("po_status", True, "INFO", "PO is open"),
        RuleResult("amount_vs_po", True, "INFO", "Amount within PO"),
        RuleResult("line_item_check", True, "INFO", "Line items valid"),
        RuleResult("tax_reconciliation", True, "INFO", "Totals reconcile"),
        RuleResult("currency_check", True, "INFO", "Currency matches"),
        RuleResult("po_utilization", True, "INFO", "PO within budget"),
        RuleResult("date_consistency", True, "INFO", "Dates consistent"),
    ]
    dec = engine.decide(rules, extraction_confidence=0.92)
    assert dec["decision"] == "APPROVED"
    assert dec["confidence_score"] > 0.8
    assert "All 11/11 validation checks passed" in dec["primary_reason"]
    assert len(dec["discrepancies"]) == 0


def test_decision_reject_on_critical_duplicate(engine):
    rules = [
        RuleResult("duplicate_detection", False, "CRITICAL", "Duplicate invoice detected"),
        RuleResult("vendor_approval", True, "INFO", "Vendor is approved"),
    ]
    dec = engine.decide(rules, extraction_confidence=0.9)
    assert dec["decision"] == "REJECTED"
    assert "Duplicate invoice" in dec["primary_reason"]
    assert any(d["severity"] == "CRITICAL" for d in dec["discrepancies"])


def test_decision_reject_on_rejected_vendor(engine):
    rules = [
        RuleResult("vendor_approval", False, "CRITICAL", "Vendor has been rejected"),
    ]
    dec = engine.decide(rules, extraction_confidence=0.9)
    assert dec["decision"] == "REJECTED"
    assert "Vendor not approved" in dec["primary_reason"]


def test_decision_review_on_low_confidence(engine):
    # Requirement: "Never automatically approve uncertain invoices."
    rules = [
        RuleResult("vendor_approval", True, "INFO", "Vendor is approved"),
        RuleResult("mandatory_fields", True, "INFO", "All mandatory fields present"),
    ]
    # Extraction confidence is only 0.35 (uncertain)
    dec = engine.decide(rules, extraction_confidence=0.35)
    assert dec["decision"] == "REVIEW"
    assert "Low extraction confidence" in dec["primary_reason"]


def test_decision_review_on_missing_fields(engine):
    rules = [
        RuleResult("mandatory_fields", False, "ERROR", "Required fields missing: invoice_number"),
    ]
    dec = engine.decide(rules, extraction_confidence=0.85)
    assert dec["decision"] == "REVIEW"
    assert "Missing critical invoice fields" in dec["primary_reason"]


def test_decision_review_on_ambiguous_match(engine):
    rules = [
        RuleResult("vendor_po_match", False, "WARNING", "Ambiguous vendor or PO match"),
    ]
    dec = engine.decide(rules, extraction_confidence=0.85)
    assert dec["decision"] == "REVIEW"
    assert "Vendor or PO could not be reliably matched" in dec["primary_reason"]
