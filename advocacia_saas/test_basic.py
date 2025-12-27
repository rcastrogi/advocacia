#!/usr/bin/env python3
print("Testing basic imports...")

try:
    import sys

    sys.path.append(".")
    print("✓ sys.path updated")
except Exception as e:
    print(f"✗ Error with sys: {e}")

try:
    import flask

    print("✓ Flask imported")
except Exception as e:
    print(f"✗ Error importing Flask: {e}")

try:
    from flask import Flask

    print("✓ Flask components imported")
except Exception as e:
    print(f"✗ Error importing Flask components: {e}")

print("Basic imports test completed")
