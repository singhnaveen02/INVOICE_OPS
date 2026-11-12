import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base, SessionLocal
from . import models  # noqa: F401 - registers models
from .models.vendor import Vendor
from .utils.seed import seed_database
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

# Auto-seed initial demo vendors & POs on fresh cloud deployments (e.g. Render)
_db = SessionLocal()
try:
    if _db.query(Vendor).count() == 0:
        seed_database(_db)
except Exception:
    _db.rollback()
finally:
    _db.close()

app = FastAPI(
    title="InvoiceOps API",
    description="Enterprise Accounts Payable Automation & Intelligent Invoice Processing System",
    version="1.0.0",
)

# CORS middleware (supports Vercel frontend + local dev)
cors_env = os.environ.get("CORS_ORIGINS", "*").strip()
allow_origins = ["*"] if cors_env == "*" else [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False if allow_origins == ["*"] else True,
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
