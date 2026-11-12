import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from ..database import Base


class DuplicateFingerprint(Base):
    __tablename__ = "duplicate_fingerprints"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String, ForeignKey("invoices.id"), unique=True, nullable=False)
    content_hash = Column(String, nullable=False, index=True)   # SHA-256 of raw PDF bytes
    normalized_hash = Column(String, nullable=False, index=True)  # SHA-256 of normalized key fields
    vendor_invoice_key = Column(String, nullable=False, index=True)  # normalized vendor+invoice_number
    amount_hash = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    invoice = relationship("Invoice", back_populates="duplicate_fingerprint")
