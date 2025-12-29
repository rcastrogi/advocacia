#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste completo do sistema de processos
"""

import os
import sys
import tempfile

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar ambiente de teste
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TESTING"] = "True"
os.environ["WTF_CSRF_ENABLED"] = "False"


def test_processes_system():
    """Testa o sistema completo de processos"""
    from app import create_app, db
    from app.models import Process, ProcessNotification, User
    from flask import g
    from flask_login import login_user
    from werkzeug.test import Client

    print("=== TESTE COMPLETO DO SISTEMA DE PROCESSOS ===\n")

    # 1. Criar app de teste
    print("1. Criando aplicacao de teste...")
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        # 2. Criar tabelas
        print("2. Criando tabelas do banco...")
        db.create_all()

        # 3. Criar usuário de teste
        print("3. Criando usuario de teste...")
        test_user = User(
            username="testuser",
            email="test@example.com",
            name="Test User",
            is_active=True,
        )
        test_user.set_password("testpass")
        db.session.add(test_user)
        db.session.commit()
        print("   Usuario criado: testuser/testpass")

        # 4. Testar autenticação
        print("\n4. Testando autenticacao...")
        client = app.test_client()

        # Testar acesso sem login (deve redirecionar)
        response = client.get("/processes/")
        if response.status_code == 302 and "auth/login" in response.headers.get(
            "Location", ""
        ):
            print(
                "   SUCCESS: Rota /processes/ redireciona para login quando nao autenticado"
            )
        else:
            print(
                f"   ERROR: Rota nao redirecionou corretamente. Status: {response.status_code}"
            )

        # 5. Fazer login
        print("5. Fazendo login...")
        with client:
            # Simular login
            response = client.post(
                "/auth/login",
                data={"username": "testuser", "password": "testpass"},
                follow_redirects=True,
            )

            if response.status_code == 200:
                print("   SUCCESS: Login realizado com sucesso")
            else:
                print(f"   ERROR: Falha no login. Status: {response.status_code}")

            # 6. Testar acesso autenticado ao dashboard
            print("6. Testando acesso ao dashboard...")
            response = client.get("/processes/")
            if response.status_code == 200:
                print("   SUCCESS: Dashboard acessivel apos login")
                if b"dashboard" in response.data.lower():
                    print("   SUCCESS: Template dashboard renderizado")
                else:
                    print("   WARNING: Palavra 'dashboard' nao encontrada no HTML")
            else:
                print(
                    f"   ERROR: Dashboard nao acessivel. Status: {response.status_code}"
                )

            # 7. Testar outras rotas web
            routes_to_test = [
                ("/processes/list", "Lista de processos"),
                ("/processes/reports", "Relatorios"),
                ("/processes/pending-petitions", "Peticoes pendentes"),
            ]

            print("\n7. Testando outras rotas web...")
            for route, description in routes_to_test:
                response = client.get(route)
                if response.status_code == 200:
                    print(f"   SUCCESS: {description} acessivel ({route})")
                else:
                    print(
                        f"   ERROR: {description} nao acessivel ({route}). Status: {response.status_code}"
                    )

            # 8. Testar endpoints da API
            print("\n8. Testando endpoints da API...")

            # API de processos
            response = client.get("/processes/api/processes")
            if response.status_code == 200:
                print("   SUCCESS: API /processes/api/processes acessivel")
            else:
                print(
                    f"   ERROR: API processos nao acessivel. Status: {response.status_code}"
                )

            # API de notificações
            response = client.get("/processes/api/notifications")
            if response.status_code == 200:
                print("   SUCCESS: API /processes/api/notifications acessivel")
            else:
                print(
                    f"   ERROR: API notificacoes nao acessivel. Status: {response.status_code}"
                )

            # API de estatísticas
            response = client.get("/processes/api/processes/stats")
            if response.status_code == 200:
                print("   SUCCESS: API /processes/api/processes/stats acessivel")
            else:
                print(
                    f"   ERROR: API stats nao acessivel. Status: {response.status_code}"
                )

    print("\n=== TESTE CONCLUIDO ===")
    return True


if __name__ == "__main__":
    try:
        test_processes_system()
    except Exception as e:
        print(f"ERRO GERAL: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
