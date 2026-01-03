#!/usr/bin/env python
"""Test to reproduce dashboard error with enhanced logging"""

import logging
import sys

# Configure logging to see all messages
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from app import create_app, db
from app.models import User

app = create_app()

# Set debug mode
app.config["DEBUG"] = True
app.logger.setLevel(logging.DEBUG)

print("=" * 70)
print("DASHBOARD ERROR REPRODUCTION TEST")
print("=" * 70)

with app.app_context():
    with app.test_client() as client:
        # Get admin user
        admin_user = User.query.filter_by(user_type="master").first()

        if not admin_user:
            print("[ERROR] No master user found")
            sys.exit(1)

        print(f"\n[INFO] Admin user: {admin_user.email}")

        # Test 1: Direct request to dashboard
        print(f"\n[TEST 1] GET /admin/dashboard (unauthenticated)")
        response = client.get("/admin/dashboard")
        print(f"  Status: {response.status_code}")
        print(f"  Location: {response.headers.get('Location', 'N/A')}")

        # Test 2: Try to access admin users list
        print(f"\n[TEST 2] GET /admin/usuarios (unauthenticated)")
        response = client.get("/admin/usuarios")
        print(f"  Status: {response.status_code}")

        # Test 3: Check if there are any JavaScript errors by checking a page
        print(f"\n[TEST 3] GET / (homepage)")
        response = client.get("/")
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            html = response.get_data(as_text=True)
            # Check for common errors
            if "<script>" in html:
                print("  [INFO] Page contains JavaScript")
            if "error-handling.js" in html:
                print("  [INFO] error-handling.js is loaded")

print("\n" + "=" * 70)
print("TEST COMPLETE - Check Flask logs above for any errors")
print("=" * 70)
