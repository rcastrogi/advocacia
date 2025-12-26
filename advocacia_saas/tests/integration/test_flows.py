"""
Testes de integração para fluxos principais do Petitio.
"""

import pytest
from flask import url_for


class TestAuthFlow:
    """Testes de fluxo de autenticação"""

    def test_login_page_loads(self, client):
        """Testa se página de login carrega"""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"Email" in response.data
        assert b"Senha" in response.data

    def test_valid_login(self, client, sample_user, app):
        """Testa login com credenciais válidas"""
        with app.app_context():
            response = client.post(
                "/auth/login",
                data={
                    "email": "test@example.com",
                    "password": "StrongPass123!",
                    "remember_me": False,
                },
                follow_redirects=True,
            )

            assert response.status_code == 200
            # Deve redirecionar para dashboard
            assert (
                b"Dashboard" in response.data or b"dashboard" in response.data.lower()
            )

    def test_invalid_login(self, client):
        """Testa login com credenciais inválidas"""
        response = client.post(
            "/auth/login",
            data={"email": "wrong@example.com", "password": "wrongpassword"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Deve mostrar erro
        assert b"inv" in response.data.lower() or b"erro" in response.data.lower()

    def test_logout(self, authenticated_client):
        """Testa logout"""
        response = authenticated_client.get("/auth/logout", follow_redirects=True)

        assert response.status_code == 200
        # Deve voltar para login
        assert b"login" in response.data.lower()

    def test_master_user_always_can_login(self, client, db_session):
        """Testa que usuários master sempre podem fazer login, mesmo desativados"""
        from app.models import User

        # Criar usuário master desativado
        master_user = User(
            username="master_test",
            email="master@test.com",
            full_name="Master Test",
            user_type="master",
            is_active=False,  # Master desativado
        )
        master_user.set_password("MasterPass123!")
        db_session.add(master_user)
        db_session.commit()

        # Tentar fazer login com usuário master desativado
        response = client.post(
            "/auth/login",
            data={
                "email": "master@test.com",
                "password": "MasterPass123!",
                "remember_me": False,
            },
            follow_redirects=True,
        )

        # Deve permitir login mesmo com usuário desativado
        assert response.status_code == 200
        assert (
            b"master" in response.data.lower() or b"dashboard" in response.data.lower()
        )


class TestPasswordSecurity:
    """Testes de segurança de senha"""

    def test_weak_password_rejected(self, client, db_session):
        """Testa rejeição de senha fraca no registro"""
        response = client.post(
            "/auth/register",
            data={
                "username": "newuser",
                "email": "newuser@example.com",
                "full_name": "New User",
                "password": "weak",  # Senha fraca
                "password2": "weak",
                "user_type": "advogado",
            },
        )

        # Deve falhar validação
        assert b"senha" in response.data.lower() or b"password" in response.data.lower()

    def test_advogado_requires_specialties(self, client, db_session):
        """Testa que advogado deve selecionar pelo menos uma especialidade"""
        response = client.post(
            "/auth/register",
            data={
                "username": "advuser",
                "email": "advuser@example.com",
                "full_name": "Advogado User",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
                "user_type": "advogado",
                "consent_personal_data": True,
                "consent_terms": True,
                # specialties não incluído - deve falhar
            },
        )

        # Deve falhar validação
        assert (
            b"especialidade" in response.data.lower()
            or b"atua" in response.data.lower()
        )

    def test_escritorio_requires_specialties(self, client, db_session):
        """Testa que escritório também deve selecionar pelo menos uma especialidade"""
        response = client.post(
            "/auth/register",
            data={
                "username": "escuser",
                "email": "escuser@example.com",
                "full_name": "Escritório User",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
                "user_type": "escritorio",
                "consent_personal_data": True,
                "consent_terms": True,
                # specialties não incluído - deve falhar
            },
        )

        # Deve falhar validação
        assert (
            b"especialidade" in response.data.lower()
            or b"atua" in response.data.lower()
        )

    def test_password_change_flow(self, authenticated_client, sample_user, app):
        """Testa fluxo de mudança de senha"""
        with app.app_context():
            response = authenticated_client.post(
                "/auth/change-password",
                data={
                    "current_password": "StrongPass123!",
                    "new_password": "NewStrongPass456!@",
                    "confirm_password": "NewStrongPass456!@",
                },
                follow_redirects=True,
            )

            assert response.status_code == 200


class TestRateLimiting:
    """Testes de rate limiting"""

    def test_login_rate_limit(self, client):
        """Testa limite de tentativas de login"""
        # Fazer 11 tentativas (limite é 10/minuto)
        for i in range(11):
            response = client.post(
                "/auth/login",
                data={"email": "test@example.com", "password": "wrongpassword"},
            )

            # 11ª tentativa deve ser bloqueada
            if i == 10:
                assert response.status_code == 429  # Too Many Requests


class TestAdminAccess:
    """Testes de acesso admin"""

    def test_admin_dashboard_requires_auth(self, client):
        """Testa que dashboard admin requer autenticação"""
        response = client.get("/usuarios")
        # Deve redirecionar para login
        assert response.status_code == 302

    def test_admin_dashboard_requires_master(self, authenticated_client):
        """Testa que dashboard admin requer privilégios master"""
        response = authenticated_client.get("/usuarios")
        # Usuário normal não tem acesso
        assert response.status_code == 403

    def test_admin_dashboard_access(self, admin_client):
        """Testa acesso ao dashboard admin"""
        response = admin_client.get("/usuarios")
        assert response.status_code == 200
        assert b"usu" in response.data.lower()  # Deve ter "usuários"


class TestNotifications:
    """Testes de sistema de notificações"""

    def test_create_notification(self, authenticated_client, sample_user, app):
        """Testa criação de notificação"""
        from app.models import Notification

        with app.app_context():
            Notification.create_notification(
                user_id=sample_user.id,
                notification_type="test",
                title="Teste",
                message="Mensagem de teste",
            )

            count = Notification.get_unread_count(sample_user.id)
            assert count == 1


class TestCaching:
    """Testes de cache"""

    def test_cache_initialization(self, app):
        """Testa se cache foi inicializado"""
        from app import cache

        with app.app_context():
            # Testar set/get
            cache.set("test_key", "test_value")
            value = cache.get("test_key")
            assert value == "test_value"

            # Limpar
            cache.delete("test_key")
            assert cache.get("test_key") is None


class TestProfileValidation:
    """Testes de validação do perfil do usuário"""

    def test_lawyer_must_have_specialties(self, authenticated_client, app):
        """Testa que advogado deve ter pelo menos uma especialidade no perfil"""
        with app.app_context():
            # Simular um usuário advogado
            from app.models import User

            user = User.query.filter_by(user_type="advogado").first()
            if not user:
                # Criar um usuário advogado para teste
                user = User(
                    username="test_lawyer",
                    email="lawyer@test.com",
                    full_name="Test Lawyer",
                    user_type="advogado",
                )
                user.set_password("testpass123")
                from app import db

                db.session.add(user)
                db.session.commit()

            # Fazer login como advogado
            response = authenticated_client.post(
                "/auth/login",
                data={"email": user.email, "password": "testpass123"},
                follow_redirects=True,
            )

            # Tentar atualizar perfil sem especialidades
            response = authenticated_client.post(
                "/auth/profile",
                data={
                    "full_name": "Test Lawyer",
                    "email": user.email,
                    "uf": "SP",
                    "quick_actions": ["create_petition"],
                    # specialties não incluído - deve falhar
                },
            )

            # Deve falhar validação
            assert (
                b"especialidade" in response.data.lower()
                or b"atua" in response.data.lower()
            )

    def test_law_firm_does_not_require_specialties(self, authenticated_client, app):
        """Testa que escritório não precisa de especialidades no perfil"""
        with app.app_context():
            # Simular um usuário escritório
            from app.models import User

            user = User.query.filter_by(user_type="escritorio").first()
            if not user:
                # Criar um usuário escritório para teste
                user = User(
                    username="test_firm",
                    email="firm@test.com",
                    full_name="Test Law Firm",
                    user_type="escritorio",
                )
                user.set_password("testpass123")
                from app import db

                db.session.add(user)
                db.session.commit()

            # Fazer login como escritório
            response = authenticated_client.post(
                "/auth/login",
                data={"email": user.email, "password": "testpass123"},
                follow_redirects=True,
            )

            # Tentar atualizar perfil sem especialidades
            response = authenticated_client.post(
                "/auth/profile",
                data={
                    "full_name": "Test Law Firm",
                    "email": user.email,
                    "uf": "SP",
                    "quick_actions": ["create_petition"],
                    # specialties não incluído - deve passar
                },
                follow_redirects=True,
            )

            # Deve redirecionar com sucesso
            assert response.status_code == 200
