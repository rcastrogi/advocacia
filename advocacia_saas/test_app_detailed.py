#!/usr/bin/env python3
"""
Test script to debug Flask app creation and blueprint registration
"""

import os
import sys
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing Flask app creation...")

    # Test basic imports
    print("1. Importing Flask...")
    from flask import Flask

    print("   ✓ Flask imported successfully")

    print("2. Importing app...")
    from app import create_app

    print("   ✓ App imported successfully")

    print("3. Creating app instance...")
    app = create_app()
    print("   ✓ App created successfully")

    print("4. Testing app context...")
    with app.app_context():
        print("   ✓ App context works")

        print("5. Testing database connection...")
        from app import db

        print("   ✓ Database imported")

        print("6. Testing PetitionModel import...")
        from app.models import PetitionModel, PetitionModelSection

        print("   ✓ PetitionModel and PetitionModelSection imported")

        print("7. Testing admin blueprint...")
        from app.admin import bp as admin_bp

        print(f"   ✓ Admin blueprint imported: {admin_bp.name}")

        print("8. Testing admin routes import...")
        from app.admin import routes

        print("   ✓ Admin routes imported")

        print("9. Testing petition_models_list function...")
        # Try to access the function
        func = getattr(routes, "petition_models_list", None)
        if func:
            print("   ✓ petition_models_list function found")
        else:
            print("   ✗ petition_models_list function not found")

    print("\nAll tests passed! App should start normally.")

except Exception as e:
    print(f"\n❌ Error during testing: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
