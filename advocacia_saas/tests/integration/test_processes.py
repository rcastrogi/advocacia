"""
Testes de integração para o módulo de processos.
"""

import pytest


class TestProcessesRoutes:
    """Testes para rotas de processos"""

    def test_processes_dashboard_requires_auth(self, client):
        """Testa se dashboard de processos requer autenticação"""
        response = client.get("/processes")
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("Location", "")

    def test_processes_dashboard_authenticated(self, authenticated_client):
        """Testa se dashboard de processos funciona com usuário autenticado"""
        response = authenticated_client.get("/processes")
        assert response.status_code == 200
        assert b"Processos" in response.data
        assert b"Dashboard" in response.data

    def test_processes_api_endpoints(self, authenticated_client):
        """Testa endpoints da API de processos"""
        # Testar endpoint de stats
        response = authenticated_client.get("/processes/api/processes/stats")
        assert response.status_code == 200

        # Testar endpoint de notificações
        response = authenticated_client.get("/processes/api/notifications")
        assert response.status_code == 200
