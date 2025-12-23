#!/usr/bin/env python3
"""
Teste da rota de planos
"""

from app import create_app


def test_route():
    app = create_app()
    with app.test_client() as client:
        response = client.get("/payments/plans")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Rota funcionando corretamente!")
        else:
            print("Erro na rota")


if __name__ == "__main__":
    test_route()
