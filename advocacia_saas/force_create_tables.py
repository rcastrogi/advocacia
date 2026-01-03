#!/usr/bin/env python
"""
Force create all tables
"""

from app import create_app, db
from app.models import *

app = create_app()

with app.app_context():
    print("Creating all tables...")
    db.create_all()
    print("[OK] All tables created")

    # Verify
    from sqlalchemy import inspect

    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    print(f"\nTotal tables: {len(tables)}")
    print("Tables:")
    for table in sorted(tables):
        print(f"  - {table}")

    # Check specific tables
    print("\nKey tables check:")
    key_tables = ["user", "billing_plan", "payment", "petition_type", "petition_model"]
    for table in key_tables:
        if table in tables:
            print(f"  [OK] {table}")
        else:
            print(f"  [MISSING] {table}")
