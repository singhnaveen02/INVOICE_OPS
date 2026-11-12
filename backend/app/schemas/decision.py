from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ValidationResultResponse(BaseModel):
    id: str
    decision_id: str
    rule_name: str
    passed: bool
    severity: str
    message: str
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class DecisionResponse(BaseModel):
    id: str
    invoice_id: str
    decision: str
    confidence_score: float
    primary_reason: str
    explanation: List[str]
    discrepancies: List[Dict[str, Any]]
    validation_summary: Dict[str, Any]
    decided_at: Optional[datetime] = None
    decided_by: str
    is_manual_override: bool
    override_reason: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    validation_results: List[ValidationResultResponse] = []

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: str
    invoice_id: str
    action: str
    actor: str
    timestamp: Optional[datetime] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewSubmit(BaseModel):
    decision: str  # APPROVE, REVIEW, REJECT
    reviewer_name: str
    reviewer_notes: Optional[str] = None
    override_reason: Optional[str] = None
