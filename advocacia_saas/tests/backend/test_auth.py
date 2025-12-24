"""
Testes para autenticação de usuários
"""

import pytest
from app.models import User
from flask import url_for


class TestAuthentication:
    """Testes para funcionalidades de autenticação"""

    def test_user_registration(self, client, db_session):
        """Testa registro de novo usuário"""
        response = client.post(
            "/auth/register",
            data={
                "username": "joao_silva",
                "full_name": "João Silva",
                "email": "joao@example.com",
                "oab_number": "123456",
                "password": "Abc123!@#",
                "password2": "Abc123!@#",
                "user_type": "advogado",
                "uf": "SP",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verificar se usuário foi criado
        user = User.query.filter_by(email="joao@example.com").first()
        assert user is not None
        assert user.full_name == "João Silva"
        assert user.oab_number == "123456"

    def test_user_login_success(self, client, db_session):
        """Testa login bem-sucedido"""
        # Criar usuário primeiro
        user = User(
            username="maria_santos",
            full_name="Maria Santos",
            email="maria@example.com",
            oab_number="654321",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()

        # Tentar login
        response = client.post(
            "/auth/login",
            data={"email": "maria@example.com", "password": "password123", "submit": "Entrar"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verificar se sessão foi criada
        with client.session_transaction() as sess:
            assert "_user_id" in sess

    def test_user_login_invalid_credentials(self, client):
        """Testa login com credenciais inválidas"""
        response = client.post(
            "/auth/login",
            data={"email": "invalid@example.com", "password": "wrongpassword", "submit": "Entrar"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Verificar se não há sessão de usuário
        with client.session_transaction() as sess:
            assert "_user_id" not in sess

    def test_password_validation(self, client):
        """Testa validação de senha"""
        # Senha muito curta
        response = client.post(
            "/auth/register",
            data={
                "username": "testuser",
                "full_name": "Test User",
                "email": "test@example.com",
                "oab_number": "123456",
                "password": "123",  # Senha muito curta
                "password2": "123",
                "user_type": "advogado",
                "uf": "SP",
            },
        )

        assert b"A senha deve ter no m" in response.data

    def test_email_uniqueness(self, client, db_session):
        """Testa que emails devem ser únicos"""
        # Criar primeiro usuário
        user1 = User(
            username="user1",
            full_name="User One",
            email="duplicate@example.com",
            oab_number="111111",
        )
        user1.set_password("password123")
        db_session.add(user1)
        db_session.commit()

        # Tentar criar segundo usuário com mesmo email
        response = client.post(
            "/auth/register",
            data={
                "username": "user2",
                "full_name": "User Two",
                "email": "duplicate@example.com",
                "oab_number": "222222",
                "password": "password123",
                "confirm_password": "password123",
            },
        )

        assert b"Email j\xc3\xa1 cadastrado" in response.data

    def test_logout(self, client, db_session):
        """Testa funcionalidade de logout"""
        # Criar e logar usuário
        user = User(
            username="logout_test",
            full_name="Logout Test",
            email="logout@example.com",
            oab_number="999999",
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()

        # Login
        client.post(
            "/auth/login",
            data={"email": "logout@example.com", "password": "password123", "submit": "Entrar"},
        )

        # Verificar login
        with client.session_transaction() as sess:
            assert "_user_id" in sess

        # Logout
        response = client.get("/auth/logout", follow_redirects=True)
        assert response.status_code == 200

        # Verificar logout
        with client.session_transaction() as sess:
            assert "_user_id" not in sess
