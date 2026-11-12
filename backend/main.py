"""
FastAPI Cloud entrypoint alias.
Re-exports the application instance from app.main.
"""
from app.main import app

__all__ = ["app"]
