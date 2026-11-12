from .invoices import router as invoices_router
from .vendors import router as vendors_router
from .purchase_orders import router as purchase_orders_router
from .dashboard import router as dashboard_router
from .review import router as review_router
from .events import router as events_router

__all__ = [
    "invoices_router",
    "vendors_router",
    "purchase_orders_router",
    "dashboard_router",
    "review_router",
    "events_router",
]
