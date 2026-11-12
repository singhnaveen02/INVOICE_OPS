import uuid
from sqlalchemy import Column, String, Float, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from ..database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    po_number = Column(String, unique=True, nullable=False, index=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=False)
    status = Column(String, default="OPEN")  # OPEN, PARTIAL, CLOSED, CANCELLED
    currency = Column(String, default="USD")
    total_amount = Column(Float, nullable=False)
    utilized_amount = Column(Float, default=0.0)
    remaining_amount = Column(Float, nullable=True, default=0.0)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    payment_terms = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    vendor = relationship("Vendor", back_populates="purchase_orders")
    line_items = relationship("POLineItem", back_populates="purchase_order", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="po", foreign_keys="Invoice.po_id")


class POLineItem(Base):
    __tablename__ = "po_line_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    po_id = Column(String, ForeignKey("purchase_orders.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    sku = Column(String, nullable=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    unit_of_measure = Column(String, default="EA")

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="line_items")
