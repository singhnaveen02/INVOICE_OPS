#!/usr/bin/env python3
"""Initialize the InvoiceOps database with tables and seed data."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app import models  # noqa: F401 — registers all models with Base
from app.utils.seed import seed_database


def init():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()
    try:
        seed_database(db)
        print("Database initialized successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    init()
