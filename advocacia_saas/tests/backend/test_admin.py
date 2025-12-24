"""
Testes críticos para sistema administrativo
Prioridade: Alta - Administração é crítica para gestão da plataforma
"""

import pytest
from app.models import User


class TestAdminSystem:
    """Testes para funcionalidades críticas de administração"""

    def test_admin_access_denied_for_regular_user(self, client, db_session):
        """Testa que usuários comuns não acessam admin"""
        # Criar usuário comum
        user = User(
            username="regularuser",
            full_name="Regular User",
            email="regular@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Login como usuário comum
        client.post(
            "/auth/login",
            data={
                "email": "regular@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Tentar acessar rota admin
        response = client.get("/admin/usuarios")
        assert response.status_code == 403  # Forbidden

    def test_admin_access_denied_for_unauthenticated(self, client):
        """Testa que usuários não autenticados não acessam admin"""
        response = client.get("/admin/usuarios")
        assert response.status_code == 302  # Redirect to login

    def test_admin_access_granted_for_master_user(self, client, db_session):
        """Testa que usuários master acessam admin"""
        # Criar usuário master
        admin_user = User(
            username="admin",
            full_name="Admin Master",
            email="admin@example.com",
            oab_number="999999",
            user_type="master",
        )
        admin_user.set_password("Admin123!")
        db_session.add(admin_user)
        db_session.commit()

        # Login como admin
        client.post(
            "/auth/login",
            data={
                "email": "admin@example.com",
                "password": "Admin123!",
                "submit": "Entrar",
            },
        )

        # Acessar rota admin
        response = client.get("/admin/usuarios")
        assert response.status_code == 200
        assert b"Admin" in response.data or b"admin" in response.data

    def test_users_list_functionality(self, client, db_session):
        """Testa listagem de usuários - funcionalidade crítica"""
        # Criar usuário master
        admin_user = User(
            username="admin",
            full_name="Admin Master",
            email="admin@example.com",
            oab_number="999999",
            user_type="master",
        )
        admin_user.set_password("Admin123!")
        db_session.add(admin_user)

        # Criar alguns usuários para listar
        for i in range(3):
            user = User(
                username=f"user{i}",
                full_name=f"User {i}",
                email=f"user{i}@example.com",
                oab_number=f"11111{i}",
                user_type="advogado",
            )
            user.set_password("Test123!")
            db_session.add(user)

        db_session.commit()

        # Login como admin
        client.post(
            "/auth/login",
            data={
                "email": "admin@example.com",
                "password": "Admin123!",
                "submit": "Entrar",
            },
        )

        # Acessar listagem de usuários
        response = client.get("/admin/usuarios")
        assert response.status_code == 200
        assert b"User 0" in response.data
        assert b"User 1" in response.data
        assert b"User 2" in response.data

    def test_users_search_functionality(self, client, db_session):
        """Testa busca de usuários - funcionalidade crítica"""
        # Criar usuário master
        admin_user = User(
            username="admin",
            full_name="Admin Master",
            email="admin@example.com",
            oab_number="999999",
            user_type="master",
        )
        admin_user.set_password("Admin123!")
        db_session.add(admin_user)

        # Criar usuários com nomes específicos
        users_data = [
            ("joao_silva", "João Silva", "joao@example.com"),
            ("maria_santos", "Maria Santos", "maria@example.com"),
            ("carlos_souza", "Carlos Souza", "carlos@example.com"),
        ]

        for username, full_name, email in users_data:
            user = User(
                username=username,
                full_name=full_name,
                email=email,
                oab_number="123456",
                user_type="advogado",
            )
            user.set_password("Test123!")
            db_session.add(user)

        db_session.commit()

        # Login como admin
        client.post(
            "/auth/login",
            data={
                "email": "admin@example.com",
                "password": "Admin123!",
                "submit": "Entrar",
            },
        )

        # Buscar por "João"
        response = client.get("/admin/usuarios?search=João")
        assert response.status_code == 200
        assert "João Silva".encode("utf-8") in response.data
        assert b"Maria Santos" not in response.data

    def test_users_filter_by_status(self, client, db_session):
        """Testa filtro de usuários por status"""
        # Criar usuário master
        admin_user = User(
            username="admin",
            full_name="Admin Master",
            email="admin@example.com",
            oab_number="999999",
            user_type="master",
        )
        admin_user.set_password("Admin123!")
        db_session.add(admin_user)

        # Criar usuários com diferentes status
        active_user = User(
            username="active_user",
            full_name="Active User",
            email="active@example.com",
            oab_number="111111",
            user_type="advogado",
            is_active=True,
        )
        active_user.set_password("Test123!")
        db_session.add(active_user)

        inactive_user = User(
            username="inactive_user",
            full_name="Inactive User",
            email="inactive@example.com",
            oab_number="222222",
            user_type="advogado",
            is_active=False,
        )
        inactive_user.set_password("Test123!")
        db_session.add(inactive_user)

        db_session.commit()

        # Login como admin
        client.post(
            "/auth/login",
            data={
                "email": "admin@example.com",
                "password": "Admin123!",
                "submit": "Entrar",
            },
        )

        # Filtrar apenas ativos
        response = client.get("/admin/usuarios?status=active")
        assert response.status_code == 200
        assert b"Active User" in response.data
        assert b"Inactive User" not in response.data

    def test_dashboard_access(self, client, db_session):
        """Testa acesso ao dashboard administrativo"""
        # Criar usuário master
        admin_user = User(
            username="admin",
            full_name="Admin Master",
            email="admin@example.com",
            oab_number="999999",
            user_type="master",
        )
        admin_user.set_password("Admin123!")
        db_session.add(admin_user)
        db_session.commit()

        # Login como admin
        client.post(
            "/auth/login",
            data={
                "email": "admin@example.com",
                "password": "Admin123!",
                "submit": "Entrar",
            },
        )

        # Acessar dashboard
        response = client.get("/admin/dashboard")
        assert response.status_code == 200
        assert b"Dashboard" in response.data or b"Admin" in response.data

    def test_financial_dashboard_access(self, client, db_session):
        """Testa acesso ao dashboard financeiro"""
        # Criar usuário master
        admin_user = User(
            username="admin",
            full_name="Admin Master",
            email="admin@example.com",
            oab_number="999999",
            user_type="master",
        )
        admin_user.set_password("Admin123!")
        db_session.add(admin_user)
        db_session.commit()

        # Login como admin
        client.post(
            "/auth/login",
            data={
                "email": "admin@example.com",
                "password": "Admin123!",
                "submit": "Entrar",
            },
        )

        # Acessar dashboard financeiro
        response = client.get("/admin/dashboard-financeiro")
        assert response.status_code == 200
        assert b"Financeiro" in response.data or b"Receita" in response.data

    def test_user_management_actions_blocked_for_regular_users(
        self, client, db_session
    ):
        """Testa que ações de gerenciamento são bloqueadas para usuários comuns"""
        # Criar usuário comum
        user = User(
            username="regularuser",
            full_name="Regular User",
            email="regular@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Login como usuário comum
        client.post(
            "/auth/login",
            data={
                "email": "regular@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Tentar ações administrativas
        routes_to_test = [
            "/admin/usuarios",
            "/admin/dashboard",
            "/admin/dashboard-financeiro",
        ]

        for route in routes_to_test:
            response = client.get(route)
            assert response.status_code in [302, 403]  # Redirect or Forbidden
