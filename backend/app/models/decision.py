import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from ..database import Base


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.id"), unique=True, nullable=False)
    decision = Column(String, nullable=False)  # APPROVE, REVIEW, REJECT
    confidence_score = Column(Float, nullable=False)
    primary_reason = Column(String, nullable=False)
    explanation = Column(JSON, nullable=False, default=list)
    discrepancies = Column(JSON, nullable=False, default=list)
    validation_summary = Column(JSON, nullable=False, default=dict)
    decided_at = Column(DateTime, server_default=func.now())
    decided_by = Column(String, default="system")
    is_manual_override = Column(Boolean, default=False)
    override_reason = Column(String, nullable=True)
    reviewer_notes = Column(String, nullable=True)
    reviewer_name = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="decision")
    validation_results = relationship("ValidationResult", back_populates="decision", cascade="all, delete-orphan")


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id = Column(String, ForeignKey("decisions.id"), nullable=False)
    rule_name = Column(String, nullable=False)
    passed = Column(Boolean, nullable=False)
    severity = Column(String, nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    message = Column(String, nullable=False)
    details = Column(JSON, nullable=True)

    # Relationships
    decision = relationship("Decision", back_populates="validation_results")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    action = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    notes = Column(String, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="audit_logs")
