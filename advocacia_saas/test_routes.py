#!/usr/bin/env python3
"""
Teste completo das rotas
"""

from app import create_app


def test_routes():
    app = create_app()
    with app.test_client() as client:
        # Testar rota home
        print("Testing home route...")
        response = client.get("/")
        print(f"Home - Status: {response.status_code}")

        # Testar rota de planos (requer login)
        print("Testing plans route...")
        response = client.get("/payments/plans")
        print(f"Plans - Status: {response.status_code}")
        if response.status_code == 302:
            print(f"Redirected to: {response.headers.get('Location', 'Unknown')}")

        # Testar rota de login
        print("Testing login route...")
        response = client.get("/auth/login")
        print(f"Login - Status: {response.status_code}")


if __name__ == "__main__":
    test_routes()
