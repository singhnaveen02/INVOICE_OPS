import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine, Base
from . import models  # noqa: F401 - registers models
from .routers import (
    invoices_router,
    vendors_router,
    purchase_orders_router,
    dashboard_router,
    review_router,
    events_router,
)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InvoiceOps API",
    description="Enterprise Accounts Payable Automation & Intelligent Invoice Processing System",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])
app.include_router(vendors_router, prefix="/vendors", tags=["Vendors"])
app.include_router(purchase_orders_router, prefix="/purchase-orders", tags=["Purchase Orders"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(review_router, prefix="/review", tags=["Human Review"])
app.include_router(events_router, prefix="/events", tags=["Real-time Events"])


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "InvoiceOps API",
        "version": "1.0.0",
        "database": "connected",
    }
