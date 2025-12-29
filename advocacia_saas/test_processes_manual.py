#!/usr/bin/env python3
"""
Script simples para testar a rota /processes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import User


def test_processes_route():
    """Testa a rota /processes"""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        # Criar tabelas
        db.create_all()

        # Criar usuário de teste
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            user_type="advogado",
            is_active=True,
        )
        user.set_password("password123", skip_history_check=True)
        db.session.add(user)
        db.session.commit()

        # Testar com cliente não autenticado
        with app.test_client() as client:
            print("Testing unauthenticated access...")
            response = client.get("/processes")
            print(f"Status: {response.status_code}")
            print(f"Location: {response.headers.get('Location', 'None')}")

            if response.status_code == 302 and "login" in response.headers.get(
                "Location", ""
            ):
                print("✓ Correctly redirects to login")
            else:
                print("✗ Does not redirect properly")

            # Testar com usuário autenticado
            print("\nTesting authenticated access...")
            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
                sess["_fresh"] = True

            response = client.get("/processes")
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                content = response.get_data(as_text=True)
                if "Processos" in content and "Dashboard" in content:
                    print("✓ Dashboard loads successfully")
                else:
                    print("✗ Dashboard content not found")
                    print(f"Content preview: {content[:200]}...")
            else:
                print(f"✗ Dashboard failed to load: {response.status_code}")
                print(f"Response: {response.get_data(as_text=True)[:200]}...")


if __name__ == "__main__":
    test_processes_route()
