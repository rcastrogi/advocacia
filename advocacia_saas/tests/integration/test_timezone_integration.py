"""
Testes de integração para funcionalidades de timezone do Petitio.
"""

import pytest
from app import create_app, db
from app.models import User


class TestTimezoneIntegration:
    """Testes de integração para o sistema de timezone"""

    def test_timezone_update_route_integration(self, authenticated_client, db_session):
        """Testa a rota completa de atualização de timezone com autenticação"""
        # O authenticated_client já está logado com sample_user

        # Atualizar timezone usando o cliente autenticado
        response = authenticated_client.post(
            "/auth/update_timezone",
            data={"timezone": "Asia/Tokyo"},
            follow_redirects=True,
        )

        assert response.status_code == 200

        # Verificar se o timezone foi atualizado no banco
        # O authenticated_client usa sample_user, então vamos buscar esse usuário
        sample_user = db_session.query(User).filter_by(username="testuser").first()
        assert sample_user is not None
        assert sample_user.timezone == "Asia/Tokyo"

    def test_timezone_validation_integration(self, authenticated_client, db_session):
        """Testa validação de timezone inválido"""
        # O authenticated_client já está logado com sample_user

        # Tentar atualizar com timezone inválido
        response = authenticated_client.post(
            "/auth/update_timezone",
            data={"timezone": "Invalid/Timezone"},
            follow_redirects=True,
        )

        # Deve redirecionar ou mostrar erro
        assert response.status_code in [200, 302]

        # Verificar que o timezone não foi alterado
        sample_user = db_session.query(User).filter_by(username="testuser").first()
        assert sample_user is not None
        assert sample_user.timezone == "America/Sao_Paulo"  # valor padrão
