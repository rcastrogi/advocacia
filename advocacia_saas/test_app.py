#!/usr/bin/env python3
import sys

sys.path.append(".")

try:
    from app import create_app

    print("✓ Import create_app successful")
except Exception as e:
    print(f"✗ Error importing create_app: {e}")
    sys.exit(1)

try:
    app = create_app()
    print("✓ App creation successful")
except Exception as e:
    print(f"✗ Error creating app: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

try:
    with app.app_context():
        from app.models import PetitionModel

        count = PetitionModel.query.count()
        print(f"✓ Database connection works. Found {count} petition models")
except Exception as e:
    print(f"✗ Error with database: {e}")
    sys.exit(1)

print("All tests passed!")
