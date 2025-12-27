#!/usr/bin/env python3
print("Testing imports...")

try:
    from app.models import PetitionModel, PetitionModelSection

    print("✓ Models imported successfully")
except Exception as e:
    print(f"✗ Error importing models: {e}")
    exit(1)

try:
    from app.admin import bp

    print("✓ Admin blueprint imported successfully")
except Exception as e:
    print(f"✗ Error importing admin blueprint: {e}")
    exit(1)

try:
    from app.admin.routes import petition_models_list

    print("✓ petition_models_list function imported successfully")
except Exception as e:
    print(f"✗ Error importing petition_models_list: {e}")
    exit(1)

print("All imports successful!")
