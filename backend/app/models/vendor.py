import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    gstin = Column(String(15), nullable=True)
    tax_id = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    country = Column(String, default="US")
    approval_status = Column(String, default="PENDING")  # APPROVED, PENDING, REJECTED, SUSPENDED
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    invoices = relationship("Invoice", back_populates="vendor", foreign_keys="Invoice.vendor_id")
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")
