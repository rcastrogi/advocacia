#!/usr/bin/env python3
"""
Teste das rotas com SQLite temporário
"""

import os
import tempfile

from app import create_app, db


def test_routes_sqlite():
    # Criar banco SQLite temporário
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()

    # Configurar DATABASE_URL temporariamente
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_db.name}"

    try:
        app = create_app()

        # Criar tabelas
        with app.app_context():
            db.create_all()

        # Testar rotas
        with app.test_client() as client:
            print("Testing home route...")
            response = client.get("/")
            print(f"Home - Status: {response.status_code}")

            print("Testing plans route...")
            response = client.get("/payments/plans")
            print(f"Plans - Status: {response.status_code}")
            if response.status_code == 302:
                print(f"Redirected to: {response.headers.get('Location', 'Unknown')}")

    finally:
        # Limpar arquivo temporário
        try:
            os.unlink(temp_db.name)
        except:
            pass


if __name__ == "__main__":
    test_routes_sqlite()
