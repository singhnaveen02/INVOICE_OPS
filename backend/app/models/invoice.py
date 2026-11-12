import uuid
from sqlalchemy import Column, String, Float, Integer, Date, DateTime, Boolean, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from ..database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    invoice_number = Column(String, nullable=True, index=True)
    invoice_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True)
    po_id = Column(String, ForeignKey("purchase_orders.id"), nullable=True)
    vendor_name_extracted = Column(String, nullable=True)
    gstin_extracted = Column(String, nullable=True)
    tax_id_extracted = Column(String, nullable=True)
    po_number_extracted = Column(String, nullable=True)
    currency = Column(String, default="USD")
    subtotal = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    discount_amount = Column(Float, nullable=True)
    shipping_amount = Column(Float, nullable=True)
    grand_total = Column(Float, nullable=True)
    payment_terms = Column(String, nullable=True)
    extraction_confidence = Column(Float, default=0.0)
    extraction_method = Column(String, default="PDF")  # PDF, OCR, MANUAL, LLM
    status = Column(String, default="PENDING")  # PENDING, PROCESSING, APPROVED, REVIEW, REJECTED
    notes = Column(String, nullable=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(String, ForeignKey("invoices.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="invoices", foreign_keys=[vendor_id])
    po = relationship("PurchaseOrder", back_populates="invoices", foreign_keys=[po_id])
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    processing_stages = relationship("ProcessingStage", back_populates="invoice", cascade="all, delete-orphan")
    decision = relationship("Decision", back_populates="invoice", uselist=False, cascade="all, delete-orphan")
    duplicate_fingerprint = relationship("DuplicateFingerprint", back_populates="invoice", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="invoice", cascade="all, delete-orphan")
    duplicate_of = relationship("Invoice", remote_side="Invoice.id", foreign_keys=[duplicate_of_id])


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)
    tax_rate = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0)

    # Relationships
    invoice = relationship("Invoice", back_populates="line_items")


class ProcessingStage(Base):
    __tablename__ = "processing_stages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    stage_name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    findings = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="processing_stages")
