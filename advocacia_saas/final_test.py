#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test /admin/usuarios like a real browser"""

from app import create_app

app = create_app()

print("=" * 60)
print("TEST: /admin/usuarios endpoint")
print("=" * 60)

with app.test_client() as client:
    # Test 1: Access without cookies
    print("\n[1] GET /admin/usuarios (sem autenticacao)")
    resp = client.get("/admin/usuarios")
    print(f"    Status: {resp.status_code}")
    if resp.status_code == 302:
        print(f"    Redirect to: {resp.location}")
        print("    [OK] Expected behavior - redirect to login")
    elif resp.status_code == 500:
        print("    [ERROR] Server error!")
        # Print first error found
        data = resp.get_data(as_text=True)
        lines = data.split("\n")
        for line in lines:
            if "Error" in line or "TypeError" in line:
                print(f"    {line[:100]}")
                break
    else:
        print(f"    [INFO] Unexpected status: {resp.status_code}")

print("\n" + "=" * 60)
