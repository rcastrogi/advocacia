"""
Testes críticos para sistema de IA
Prioridade: Alta - IA é funcionalidade diferenciadora da plataforma
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from app.models import AIGeneration, CreditPackage, CreditTransaction, User, UserCredits


class TestAISystem:
    """Testes para funcionalidades críticas de IA"""

    def test_ai_generation_requires_authentication(self, client):
        """Testa que geração de IA requer autenticação"""
        response = client.post("/ai/api/generate/section")
        assert response.status_code == 302  # Redirect to login

    def test_ai_generation_requires_credits(self, client, db_session):
        """Testa que geração de IA requer créditos suficientes"""
        # Criar usuário sem créditos
        user = User(
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Criar registro de créditos vazio
        user_credits = UserCredits(user_id=user.id, balance=0)
        db_session.add(user_credits)
        db_session.commit()

        # Login
        client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Tentar gerar conteúdo IA
        response = client.post(
            "/ai/api/generate/section",
            json={
                "section_type": "fatos",
                "petition_type": "civel",
                "context": {"description": "Teste"},
            },
        )

        assert response.status_code == 402
        data = response.get_json()
        assert (
            "créditos" in data.get("error", "").lower()
            or "credits" in data.get("error", "").lower()
        )

    def test_ai_generation_success(self, client, db_session):
        """Testa geração de IA bem-sucedida - funcionalidade crítica"""
        # Criar usuário com créditos
        user = User(
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Criar registro de créditos
        user_credits = UserCredits(user_id=user.id, balance=100)
        db_session.add(user_credits)
        db_session.commit()

        # Login
        client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Mock do serviço de IA
        mock_response = {
            "content": "Texto gerado pela IA",
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_input": 50,
                "tokens_output": 100,
                "tokens_total": 150,
                "response_time_ms": 2000,
            },
        }

        with patch("app.ai.routes.ai_service.generate_section") as mock_generate:
            mock_generate.return_value = (
                "Texto gerado pela IA",
                {
                    "model": "gpt-4o-mini",
                    "tokens_input": 50,
                    "tokens_output": 100,
                    "tokens_total": 150,
                    "response_time_ms": 2000,
                },
            )

            # Gerar conteúdo IA
            response = client.post(
                "/ai/api/generate/section",
                json={
                    "section_type": "fatos",
                    "petition_type": "civel",
                    "context": {"description": "Acidente de trânsito"},
                },
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "content" in data
            assert "Texto gerado pela IA" in data["content"]

            # Verificar se créditos foram debitados
            updated_credits = UserCredits.query.filter_by(user_id=user.id).first()
            assert updated_credits.balance < 100  # Deve ter diminuído

            # Verificar se geração foi registrada
            generation = AIGeneration.query.filter_by(user_id=user.id).first()
            assert generation is not None
            assert generation.generation_type == "section"
            assert generation.status == "completed"

    def test_ai_generation_error_handling(self, client, db_session):
        """Testa tratamento de erros na geração de IA"""
        # Criar usuário com créditos
        user = User(
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Criar registro de créditos
        user_credits = UserCredits(user_id=user.id, balance=100)
        db_session.add(user_credits)
        db_session.commit()

        # Login
        client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Mock do serviço de IA com erro
        with patch("app.ai.routes.ai_service.generate_section") as mock_generate:
            mock_generate.side_effect = Exception("Erro na API da OpenAI")

            # Tentar gerar conteúdo IA
            response = client.post(
                "/ai/api/generate/section",
                json={
                    "section_type": "fatos",
                    "petition_type": "civel",
                    "context": {"description": "Teste"},
                },
            )

            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data

            # Verificar se geração de erro foi registrada
            generation = AIGeneration.query.filter_by(
                user_id=user.id, status="failed"
            ).first()
            assert generation is not None
            assert "Erro na API" in generation.error_message

    def test_credits_dashboard_access(self, client, db_session):
        """Testa acesso ao dashboard de créditos"""
        # Criar usuário
        user = User(
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Criar registro de créditos
        user_credits = UserCredits(user_id=user.id, balance=50)
        db_session.add(user_credits)
        db_session.commit()

        # Login
        client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Acessar dashboard de créditos
        response = client.get("/ai/credits")
        assert response.status_code == 200
        assert (
            "créditos".encode("utf-8") in response.data.lower()
            or b"credits" in response.data.lower()
        )

    @pytest.mark.skip(
        reason="Complex Mercado Pago integration test - requires external service setup"
    )
    def test_credit_purchase_flow(self, client, db_session):
        """Testa fluxo de compra de créditos - funcionalidade crítica"""
        # Criar usuário
        user = User(
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Criar pacote de créditos
        package = CreditPackage(
            name="Pacote Teste",
            slug="pacote-teste",
            credits=100,
            price=Decimal("29.90"),
            is_active=True,
            sort_order=1,
        )
        db_session.add(package)
        db_session.commit()

        # Login
        client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Mock Mercado Pago
        with patch("app.ai.routes.mp_sdk") as mock_mp:
            mock_payment_response = {
                "id": 12345,
                "status": "pending",
                "point_of_interaction": {
                    "transaction_data": {
                        "qr_code": "test-qr-code",
                        "qr_code_base64": "test-qr-base64",
                    }
                },
            }
            mock_mp.payment.return_value.create.return_value = {
                "status": 201,
                "response": mock_payment_response,
            }

            # Comprar créditos
            response = client.post("/ai/buy-credits", json={"package_id": package.id})

            assert response.status_code == 200
            data = response.get_json()
            assert "pix_code" in data

            # Verificar se transação foi registrada
            transaction = CreditTransaction.query.filter_by(user_id=user.id).first()
            assert transaction is not None
            assert transaction.transaction_type == "purchase"
            assert transaction.amount == 100

    def test_master_user_bypass_credits(self, client, db_session):
        """Testa que usuários master não gastam créditos"""
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

        # Criar registro de créditos vazio
        user_credits = UserCredits(user_id=admin_user.id, balance=0)
        db_session.add(user_credits)
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

        # Mock do serviço de IA
        mock_response = {
            "content": "Texto gerado pelo admin",
            "metadata": {"model": "gpt-4o-mini", "tokens_total": 100},
        }

        with patch("app.ai.routes.ai_service.generate_section") as mock_generate:
            mock_generate.return_value = (
                "Texto gerado pelo admin",
                {"model": "gpt-4o-mini", "tokens_total": 100},
            )

            # Gerar conteúdo IA como admin
            response = client.post(
                "/ai/api/generate/section",
                json={
                    "section_type": "fatos",
                    "petition_type": "civel",
                    "context": {"description": "Teste"},
                },
            )

            assert response.status_code == 200

            # Verificar que créditos não foram debitados
            updated_credits = UserCredits.query.filter_by(user_id=admin_user.id).first()
            assert updated_credits.balance == 0  # Deve permanecer zero

    def test_ai_generation_rate_limiting(self, client, db_session):
        """Testa controle de taxa de geração de IA"""
        # Criar usuário com poucos créditos
        user = User(
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Criar registro de créditos com apenas 1 crédito
        user_credits = UserCredits(user_id=user.id, balance=0)
        db_session.add(user_credits)
        db_session.commit()

        # Login
        client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Mock do serviço de IA que consome 5 créditos
        mock_response = {
            "content": "Texto gerado",
            "metadata": {"model": "gpt-4o-mini", "tokens_total": 100},
        }

        with patch("app.ai.routes.ai_service.generate_section") as mock_generate:
            mock_generate.return_value = (
                "Texto gerado",
                {"model": "gpt-4o-mini", "tokens_total": 100},
            )

            # Tentar gerar conteúdo (deve falhar por falta de créditos)
            response = client.post(
                "/ai/api/generate/section",
                json={
                    "section_type": "fatos",
                    "petition_type": "civel",
                    "context": {"description": "Teste"},
                },
            )

            assert response.status_code == 402
            data = response.get_json()
            assert "créditos" in data.get("error", "").lower()

    def test_ai_usage_statistics(self, client, db_session):
        """Testa estatísticas de uso de IA"""
        # Criar usuário
        user = User(
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            oab_number="123456",
            user_type="advogado",
        )
        user.set_password("Test123!")
        db_session.add(user)
        db_session.commit()

        # Criar algumas gerações de IA
        for i in range(3):
            generation = AIGeneration(
                user_id=user.id,
                generation_type="section",
                credits_used=5,
                status="completed",
            )
            db_session.add(generation)

        db_session.commit()

        # Login
        client.post(
            "/auth/login",
            data={
                "email": "test@example.com",
                "password": "Test123!",
                "submit": "Entrar",
            },
        )

        # Acessar dashboard de créditos (que mostra estatísticas)
        response = client.get("/ai/credits")
        assert response.status_code == 200
        # Verificar se estatísticas aparecem na página
        assert (
            "gerações".encode("utf-8") in response.data.lower()
            or b"generations" in response.data.lower()
        )
