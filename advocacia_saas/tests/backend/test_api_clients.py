"""
Testes para rotas da API
"""

import json

import pytest
from app.models import Client, User


class TestAPIClientRoutes:
    """Testes para rotas de clientes da API"""

    def test_get_clients_unauthorized(self, client):
        """Testa acesso não autorizado à lista de clientes"""
        response = client.get("/api/clients", follow_redirects=False)
        assert response.status_code == 401

    def test_get_clients_authorized(self, client, db_session):
        """Testa acesso autorizado à lista de clientes"""
        # Criar usuário e logar
        user = User(
            username="api_test",
            full_name="API Test User",
            email="api@example.com",
            oab_number="123456",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()  # Commit user first to get ID

        # Criar alguns clientes
        client1 = Client(
            full_name="Cliente 1",
            email="cliente1@example.com",
            lawyer_id=user.id,
            cpf_cnpj="12345678901",
            mobile_phone="11999999999",
        )
        client2 = Client(
            full_name="Cliente 2",
            email="cliente2@example.com",
            lawyer_id=user.id,
            cpf_cnpj="12345678902",
            mobile_phone="11999999998",
        )
        db_session.add_all([client1, client2])
        db_session.commit()

        # Fazer login
        client.post(
            "/auth/login",
            data={
                "email": "api@example.com",
                "password": "password123",
                "submit": "Entrar",
            },
        )

        # Acessar API
        response = client.get("/api/clients")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]["full_name"] == "Cliente 1"
        assert data[1]["full_name"] == "Cliente 2"

    def test_create_client(self, client, db_session):
        """Testa criação de cliente via API"""
        # Criar e logar usuário
        user = User(
            username="create_test",
            full_name="Create Test User",
            email="create@example.com",
            oab_number="123456",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()
        db_session.commit()

        client.post(
            "/auth/login",
            data={
                "email": "create@example.com",
                "password": "password123",
                "submit": "Entrar",
            },
        )

        # Criar cliente
        response = client.post(
            "/api/clients",
            json={
                "full_name": "Novo Cliente",
                "email": "novo@cliente.com",
                "mobile_phone": "11999999999",
                "cpf_cnpj": "12345678901",
            },
        )

        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["full_name"] == "Novo Cliente"
        assert data["email"] == "novo@cliente.com"

        # Verificar no banco
        created_client = Client.query.filter_by(email="novo@cliente.com").first()
        assert created_client is not None
        assert created_client.lawyer_id == user.id

    def test_get_client_by_id(self, client, db_session):
        """Testa busca de cliente por ID"""
        # Criar usuário e cliente
        user = User(
            username="get_test",
            full_name="Get Test",
            email="get@example.com",
            oab_number="123",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()

        client_obj = Client(
            full_name="Cliente Específico",
            email="especifico@example.com",
            lawyer_id=user.id,
            cpf_cnpj="12345678901",
            mobile_phone="11999999999",
        )
        db_session.add(client_obj)
        db_session.commit()

        # Logar
        client.post(
            "/auth/login",
            data={
                "email": "get@example.com",
                "password": "password123",
                "submit": "Entrar",
            },
        )

        # Buscar cliente
        response = client.get(f"/api/clients/{client_obj.id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["full_name"] == "Cliente Específico"
        assert data["email"] == "especifico@example.com"

    def test_update_client(self, client, db_session):
        """Testa atualização de cliente"""
        # Criar usuário e cliente
        user = User(
            username="update_test",
            full_name="Update Test",
            email="update@example.com",
            oab_number="123",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()

        client_obj = Client(
            full_name="Cliente Original",
            email="original@example.com",
            lawyer_id=user.id,
            cpf_cnpj="12345678901",
            mobile_phone="11999999999",
        )
        db_session.add(client_obj)
        db_session.commit()

        # Logar
        client.post(
            "/auth/login",
            data={
                "email": "update@example.com",
                "password": "password123",
                "submit": "Entrar",
            },
        )

        # Atualizar cliente
        response = client.put(
            f"/api/clients/{client_obj.id}",
            json={
                "full_name": "Cliente Atualizado",
                "email": "atualizado@example.com",
                "mobile_phone": "11888888888",
            },
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["full_name"] == "Cliente Atualizado"
        assert data["email"] == "atualizado@example.com"

        # Verificar no banco
        updated_client = Client.query.get(client_obj.id)
        assert updated_client.full_name == "Cliente Atualizado"

    def test_delete_client(self, client, db_session):
        """Testa exclusão de cliente"""
        # Criar usuário e cliente
        user = User(
            username="delete_test",
            full_name="Delete Test",
            email="delete@example.com",
            oab_number="123",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()

        client_obj = Client(
            full_name="Cliente Para Deletar",
            email="deletar@example.com",
            lawyer_id=user.id,
            cpf_cnpj="12345678901",
            mobile_phone="11999999999",
        )
        db_session.add(client_obj)
        db_session.commit()

        client_id = client_obj.id

        # Logar
        client.post(
            "/auth/login",
            data={
                "email": "delete@example.com",
                "password": "password123",
                "submit": "Entrar",
            },
        )

        # Deletar cliente
        response = client.delete(f"/api/clients/{client_id}")
        assert response.status_code == 200

        # Verificar que foi deletado
        deleted_client = Client.query.get(client_id)
        assert deleted_client is None
